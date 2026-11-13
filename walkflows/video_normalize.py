"""Create an explicitly resampled constant-frame-rate analysis input."""
import hashlib
import json
import math
import os
import subprocess
import time
from pathlib import Path

from walkflows.multicamera_processing import file_sha256, _state
from walkflows.multicamera_preview import ffmpeg_executable
from walkflows.multicamera_project import _video, build_project
from walkflows.video_timing import audit_video_timing


def normalize_video(video, fps, destination):
    if (isinstance(fps,bool) or not isinstance(fps,(int,float)) or
            not math.isfinite(fps) or not .1<=fps<=240):
        raise ValueError("target fps must be between 0.1 and 240")
    video=Path(video).expanduser().resolve(strict=True)
    destination=Path(destination).expanduser().resolve()
    executable=ffmpeg_executable()
    source_hash=file_sha256(video);ffmpeg_hash=file_sha256(executable)
    destination.mkdir(parents=True,exist_ok=False)
    journal={"status":"running","stage":"audit_source","started_unix_s":time.time()}
    _state(destination/"state.json",journal)
    try:
        source_metadata=_video(video)
        source=audit_video_timing(video)
        if source["source_sha256"]!=source_hash or source["ffmpeg_sha256"]!=ffmpeg_hash:
            raise ValueError("source or FFmpeg changed")
        journal["stage"]="transcode"
        _state(destination/"state.json",journal)
        target=destination/"normalized.mp4"
        rate=format(float(fps),".10g")
        cmd=[str(executable),"-nostdin","-hide_banner","-loglevel","error","-xerror","-n",
             "-i",str(video),"-map","0:v:0","-an","-sn","-dn","-vf",
             "setpts=PTS-STARTPTS,fps=fps="+rate+":round=near",
             "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",
             "-fps_mode","cfr","-movflags","+faststart",str(target)]
        result=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        if result.returncode:
            raise ValueError("FFmpeg normalization failed: "+result.stderr[-1000:])
        journal["stage"]="audit_output"
        _state(destination/"state.json",journal)
        output_metadata=_video(target)
        output=audit_video_timing(target)
        if (output_metadata["width"],output_metadata["height"])!=(source_metadata["width"],source_metadata["height"]):
            raise ValueError("normalized dimensions differ from source")
        if (output_metadata["sha256"]!=output["source_sha256"] or
                file_sha256(target)!=output["source_sha256"] or
                output["ffmpeg_sha256"]!=ffmpeg_hash or file_sha256(video)!=source_hash):
            raise ValueError("source or FFmpeg changed during normalization")
        if not math.isclose(output["nominal_fps"],float(fps),rel_tol=.00001,abs_tol=.00001):
            raise ValueError("normalized frame rate differs from requested rate")
        if output["max_nominal_deviation_seconds"]>.001:
            raise ValueError("normalized video timestamps are not sufficiently regular")
        report={"schema_version":1,"source":{"sha256":source_hash,**source},
                "output":{"sha256":output["source_sha256"],**output},
                "dimensions":{"width":source_metadata["width"],"height":source_metadata["height"]},
                "requested_fps":float(fps),"ffmpeg_sha256":ffmpeg_hash,
                "settings":{"filter":"setpts=PTS-STARTPTS,fps:round=near","codec":"libx264",
                            "preset":"veryfast","crf":20,"pixel_format":"yuv420p","audio":"omitted"},
                "scope":"Resampled analysis input; frames may be duplicated or dropped, start time reset. "
                        "Not proof of camera alignment or tracking accuracy."}
        content=json.dumps(report,indent=2,allow_nan=False)+chr(10)
        with (destination/"manifest.json").open("x",encoding="utf-8") as file:file.write(content)
        journal.update(status="completed",stage="completed",finished_unix_s=time.time())
        _state(destination/"state.json",journal)
        return report
    except Exception as exc:
        if journal["cameras"] and journal["cameras"][-1]["status"]=="running":
            journal["cameras"][-1].update(status="failed",error=str(exc))
        journal.update(status="failed",error=str(exc),finished_unix_s=time.time())
        _state(destination/"state.json",journal)
        raise


def normalize_project(config_path, fps, destination):
    """Normalize each camera sequentially and publish a validated new project."""
    if (isinstance(fps,bool) or not isinstance(fps,(int,float)) or
            not math.isfinite(fps) or not .1<=fps<=240):
        raise ValueError("target fps must be between 0.1 and 240")
    config_path=Path(config_path).expanduser().resolve(strict=True)
    destination=Path(destination).expanduser().resolve()
    config_bytes=config_path.read_bytes()
    config=json.loads(config_bytes)
    config_hash=file_sha256(config_path)
    if config_hash!=hashlib.sha256(config_bytes).hexdigest():
        raise ValueError("project changed during validation")
    project=build_project(config_path,allow_no_overlap=True)
    if any("normalization" in camera for camera in project["cameras"]):
        raise ValueError("project contains an already normalized camera")
    if file_sha256(config_path)!=config_hash:
        raise ValueError("project changed during validation")
    destination.mkdir(parents=True,exist_ok=False)
    journal={"status":"running","stage":"normalizing","started_unix_s":time.time(),
             "source_config_sha256":config_hash,"cameras":[]}
    _state(destination/"state.json",journal)
    try:
        by_id={item["id"]:item for item in config["cameras"]}
        for camera in project["cameras"]:
            cid=camera["id"]
            entry={"id":cid,"status":"running"};journal["cameras"].append(entry)
            _state(destination/"state.json",journal)
            bundle=destination/cid
            report=normalize_video(camera["video"]["path"],fps,bundle)
            if report["source"]["sha256"]!=camera["video"]["sha256"]:
                raise ValueError("source changed since project validation: "+cid)
            by_id[cid]["path"]=str((bundle/"normalized.mp4").resolve())
            by_id[cid]["normalization_manifest"]=str((bundle/"manifest.json").resolve())
            entry.update(status="completed",source_sha256=report["source"]["sha256"],
                         output_sha256=report["output"]["sha256"])
            _state(destination/"state.json",journal)
        if file_sha256(config_path)!=config_hash:
            raise ValueError("project changed during normalization")
        for camera in project["cameras"]:
            if file_sha256(camera["video"]["path"])!=camera["video"]["sha256"]:
                raise ValueError("source changed during normalization: "+camera["id"])
        journal["stage"]="validating_project";_state(destination/"state.json",journal)
        candidate=destination/"project.json.part"
        content=json.dumps(config,indent=2,ensure_ascii=False,allow_nan=False)+chr(10)
        with candidate.open("x",encoding="utf-8") as file:file.write(content)
        build_project(candidate,allow_no_overlap=True)
        os.link(candidate,destination/"project.json")
        candidate.unlink()
        journal.update(status="completed",stage="completed",finished_unix_s=time.time(),
                       project_sha256=file_sha256(destination/"project.json"),
                       scope="Offsets preserved as estimates; recheck after resampling.")
        _state(destination/"state.json",journal)
        return journal
    except Exception as exc:
        if journal["cameras"] and journal["cameras"][-1]["status"]=="running":
            journal["cameras"][-1].update(status="failed",error=str(exc))
        journal.update(status="failed",error=str(exc),finished_unix_s=time.time())
        _state(destination/"state.json",journal)
        raise
