"""Create verified, optional browser-playback copies of completed video inputs."""
import json
import math
import re
import shutil
import subprocess
import time
from pathlib import Path

import cv2

from walkflows.multicamera_processing import file_sha256, _state
from walkflows.multicamera_project import build_project


def ffmpeg_executable():
    system = shutil.which("ffmpeg")
    if system:
        return Path(system).resolve(strict=True)
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise ValueError("FFmpeg unavailable; install the optional preview dependency or provide FFmpeg on PATH") from exc
    return Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve(strict=True)


def _verify_video(path, source, expected_frames=None):
    cap=cv2.VideoCapture(str(path))
    count=0
    try:
        fps=float(cap.get(cv2.CAP_PROP_FPS))
        if not cap.isOpened() or not math.isfinite(fps) or fps<=0:
            raise ValueError("preview cannot be decoded")
        while True:
            ok,frame=cap.read()
            if not ok:break
            if frame.shape[:2]!=(source["height"],source["width"]):
                raise ValueError("preview dimensions changed")
            count+=1
    finally:
        cap.release()
    if count<=0:
        raise ValueError("video has no decodable frames")
    if expected_frames is not None and count!=expected_frames:
        raise ValueError("preview frame count differs from source")
    if not math.isclose(fps,source["fps"],rel_tol=0.001,abs_tol=0.001):
        raise ValueError("preview frame rate differs from source")
    return {"decoded_frames":count,"fps":fps,"width":source["width"],"height":source["height"]}


def build_preview_bundle(run_dir, destination, camera_ids=None, *, ffmpeg=None):
    run_dir=Path(run_dir).expanduser().resolve(strict=True)
    run_path=run_dir/"run.json"
    run_hash=file_sha256(run_path)
    run=json.loads(run_path.read_text(encoding="utf-8"))
    if run.get("status")!="completed":raise ValueError("run must be completed")
    cameras=run["project"]["cameras"]
    results={c["id"]:c for c in run["cameras"]}
    if len(results)!=len(cameras) or set(results)!={c["id"] for c in cameras}:
        raise ValueError("invalid camera results")
    return _build_bundle(cameras,destination,camera_ids,ffmpeg,
                         {"kind":"run","run_sha256":run_hash},run_path,run_hash,results)


def build_project_preview_bundle(config_path, destination, camera_ids=None, *, ffmpeg=None):
    config_path=Path(config_path).expanduser().resolve(strict=True)
    config_hash=file_sha256(config_path)
    project=build_project(config_path,allow_no_overlap=True)
    return _build_bundle(project["cameras"],destination,camera_ids,ffmpeg,
                         {"kind":"project","config_sha256":config_hash},config_path,config_hash,None)


def _build_bundle(cameras,destination,camera_ids,ffmpeg,identity,source_manifest,source_manifest_hash,results):
    destination=Path(destination).expanduser().resolve()
    by_id={c["id"]:c for c in cameras}
    if len(by_id)!=len(cameras):raise ValueError("duplicate camera")
    requested=list(by_id) if camera_ids is None else list(camera_ids)
    if not requested or len(requested)!=len(set(requested)) or set(requested)-set(by_id):
        raise ValueError("invalid camera selection")
    if any(not isinstance(cid,str) or not re.fullmatch(r"[A-Za-z0-9_-]+",cid) for cid in requested):
        raise ValueError("invalid camera id")
    executable=Path(ffmpeg).resolve(strict=True) if ffmpeg is not None else ffmpeg_executable()
    try:
        version=subprocess.run([str(executable),"-version"],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    except (subprocess.SubprocessError, IndexError) as exc:
        raise ValueError("FFmpeg executable could not be inspected") from exc
    ffmpeg_hash=file_sha256(executable)
    destination.mkdir(parents=True,exist_ok=False)
    journal={"status":"running","started_unix_s":time.time(),"cameras":[]}
    _state(destination/"state.json",journal)
    entries=[]
    try:
        for cid in requested:
            camera=by_id[cid];source=camera["video"]
            if file_sha256(source["path"])!=source["sha256"]:
                raise ValueError("source hash mismatch: "+cid)
            if results is None:
                expected_frames=_verify_video(Path(source["path"]),source)["decoded_frames"]
            else:
                result=results[cid]
                if (result.get("status")!="completed" or type(result.get("decoded_frames")) is not int or
                        result["decoded_frames"]<=0):
                    raise ValueError("camera incomplete: "+cid)
                expected_frames=result["decoded_frames"]
            entry={"id":cid,"status":"running"};journal["cameras"].append(entry)
            _state(destination/"state.json",journal)
            target=destination/(cid+".mp4")
            cmd=[str(executable),"-nostdin","-hide_banner","-loglevel","error","-n","-i",source["path"],
                 "-map","0:v:0","-an","-sn","-dn","-c:v","libx264","-preset","veryfast",
                 "-crf","20","-pix_fmt","yuv420p","-fps_mode","passthrough","-movflags","+faststart",str(target)]
            proc=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
            if proc.returncode:
                raise RuntimeError("FFmpeg failed for "+cid+": "+proc.stderr[-1000:])
            metadata=_verify_video(target,source,expected_frames)
            if file_sha256(source["path"])!=source["sha256"]:
                raise ValueError("source changed during transcoding: "+cid)
            entries.append({"id":cid,"source_sha256":source["sha256"],
                            "preview_sha256":file_sha256(target),**metadata})
            entry.update(status="completed",decoded_frames=metadata["decoded_frames"])
            _state(destination/"state.json",journal)
        if file_sha256(source_manifest)!=source_manifest_hash or file_sha256(executable)!=ffmpeg_hash:
            raise ValueError("project, run or FFmpeg changed during transcoding")
        manifest={"schema_version":1,**identity,"ffmpeg_sha256":ffmpeg_hash,
                  "ffmpeg_version":version,"settings":{"video_codec":"libx264","crf":20,"preset":"veryfast",
                   "pixel_format":"yuv420p","timestamps":"passthrough","audio":"omitted"},
                  "scope":"Playback copies, not analysis inputs; frame count and nominal fps checked, "
                          "per-frame timestamps and variable-frame-rate alignment not independently verified.",
                  "cameras":entries}
        content=json.dumps(manifest,indent=2,allow_nan=False)+"\n"
        with (destination/"preview.json").open("x",encoding="utf-8") as file:file.write(content)
        journal["status"]="completed";journal["finished_unix_s"]=time.time()
        _state(destination/"state.json",journal)
        return manifest
    except Exception as exc:
        journal["status"]="failed";journal["error"]=str(exc);journal["finished_unix_s"]=time.time()
        _state(destination/"state.json",journal)
        raise
