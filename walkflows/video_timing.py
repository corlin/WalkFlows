"""Measure decoded frame presentation times and compare a playback copy."""
import math
import re
import subprocess
from collections import deque
from pathlib import Path

from walkflows.multicamera_processing import file_sha256
from walkflows.multicamera_preview import ffmpeg_executable
from walkflows.multicamera_project import _video

_TIMEBASE=re.compile(r"config in time_base:\s*(\d+)/(\d+)")
_FRAME=re.compile(r"\bn:\s*(\d+)\s+pts:\s*(-?\d+|NOPTS)\s+pts_time:")


def compare_timing(source, fps, preview=None):
    if not isinstance(fps,(int,float)) or isinstance(fps,bool) or not math.isfinite(fps) or fps<=0:
        raise ValueError("invalid nominal frame rate")
    def normalize(values):
        if not values or any(not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(x) for x in values):
            raise ValueError("missing or invalid presentation timestamps")
        if any(b<=a for a,b in zip(values,values[1:])):
            raise ValueError("presentation timestamps are not strictly increasing")
        return [x-values[0] for x in values]
    source_relative=normalize(source)
    nominal=[abs(t-i/fps) for i,t in enumerate(source_relative)]
    result={"frames":len(source),"nominal_fps":fps,"first_presentation_time_seconds":source[0],
            "last_relative_presentation_time_seconds":source_relative[-1],
            "max_nominal_deviation_seconds":max(nominal),
            "max_nominal_deviation_frames":max(nominal)*fps}
    if preview is not None:
        normalized=normalize(preview)
        if len(normalized)!=len(source_relative):
            raise ValueError("preview frame count differs from source")
        deviations=[abs(a-b) for a,b in zip(source_relative,normalized)]
        result["preview_first_presentation_time_seconds"]=preview[0]
        result["max_preview_deviation_seconds"]=max(deviations)
        result["max_preview_deviation_frames"]=max(deviations)*fps
    return result


def read_presentation_times(video, executable):
    cmd=[str(executable),"-nostdin","-hide_banner","-loglevel","info","-xerror","-i",str(video),
         "-map","0:v:0","-vf","showinfo","-an","-sn","-dn","-fps_mode","passthrough","-f","null","-"]
    times=[]; timebase=None; tail=deque(maxlen=12)
    with subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,errors="replace") as proc:
        try:
            for line in proc.stderr:
                tail.append(line.strip())
                if "showinfo" not in line:continue
                config=_TIMEBASE.search(line)
                if config:
                    numerator,denominator=map(int,config.groups())
                    if numerator<=0 or denominator<=0:raise ValueError("invalid FFmpeg time base")
                    if timebase is not None:raise ValueError("video timing changed during decoding")
                    timebase=numerator/denominator
                frame=_FRAME.search(line)
                if frame:
                    index=int(frame.group(1));pts=frame.group(2)
                    if timebase is None or pts=="NOPTS" or index!=len(times):
                        raise ValueError("missing or discontinuous FFmpeg presentation timestamps")
                    times.append(int(pts)*timebase)
        except Exception:
            proc.kill();proc.wait();raise
        status=proc.wait()
    if status:raise ValueError("FFmpeg timing decode failed: "+" ".join(tail)[-1000:])
    if not times:raise ValueError("no presentation timestamps decoded")
    return times


def audit_video_timing(video, preview=None):
    video=Path(video).expanduser().resolve(strict=True)
    preview=Path(preview).expanduser().resolve(strict=True) if preview is not None else None
    metadata=_video(video);source_hash=metadata["sha256"]
    preview_hash=file_sha256(preview) if preview is not None else None
    ffmpeg=ffmpeg_executable();ffmpeg_hash=file_sha256(ffmpeg)
    source_times=read_presentation_times(video,ffmpeg)
    preview_times=read_presentation_times(preview,ffmpeg) if preview else None
    result=compare_timing(source_times,metadata["fps"],preview_times)
    if file_sha256(video)!=source_hash or (preview and file_sha256(preview)!=preview_hash) or file_sha256(ffmpeg)!=ffmpeg_hash:
        raise ValueError("input or FFmpeg changed during timing check")
    result.update(source_sha256=source_hash,preview_sha256=preview_hash,ffmpeg_sha256=ffmpeg_hash,
                  scope="FFmpeg decoded presentation timestamps relative to first frame; not proof of camera synchronization or browser frame accuracy.")
    return result
