"""Derive approximate planar maps from a retail dataset manifest and calibration."""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial.transform import Rotation

from scripts.derive_site03_plane_mapping import derive
from walkflows.multicamera_processing import file_sha256
from walkflows.scene_transforms import compose_camera, normalized_bounds, scene_global_transform


def compose_floor_camera(camera, global_transform):
    # Only ground-preserving rigid global transforms are supported.
    if camera.get("scale") != 1 or global_transform.get("scale") != 1:
        raise ValueError("unsupported floor transform scale")
    rotation = Rotation.from_quat(global_transform["rotation"])
    if (not np.allclose(rotation.apply([0, 0, 1]), [0, 0, 1], atol=1e-8)
            or abs(global_transform["translation"][2]) > 1e-8):
        raise ValueError("global transform does not preserve floor")
    return compose_camera(camera, global_transform)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--camera", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scenario = args.scenario.resolve(strict=True)
    calibration = args.calibration.resolve(strict=True)
    manifest_path = scenario / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scene_key = manifest["scene-key"]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", scene_key):
        raise ValueError("invalid scene key")
    scene_path = calibration / "scenes" / (scene_key + ".json")
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    videos = manifest["videos"]
    by_camera = {item["camera"]: item for item in videos}
    if len(by_camera) != len(videos) or len(args.camera) != len(set(args.camera)):
        raise ValueError("duplicate camera")
    if any(cid not in by_camera or cid not in scene["bcam-keys"] for cid in args.camera):
        raise ValueError("camera is missing from manifest or scene")
    epoch = datetime.fromisoformat(manifest["epoch"])
    bounds = normalized_bounds(scene["hist-aabb"])
    configs=[];reports=[]
    for cid in args.camera:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", cid):
            raise ValueError("invalid camera id")
        item=by_camera[cid]
        video=(scenario/item["file"]).resolve(strict=True)
        if not video.is_relative_to(scenario):
            raise ValueError("video escapes scenario")
        capture=cv2.VideoCapture(str(video))
        ok,frame=capture.read()
        fps=capture.get(cv2.CAP_PROP_FPS)
        capture.release()
        if not ok or frame.shape[:2] != (672,1792) or not np.isclose(fps,float(item["fps"]),rtol=1e-5):
            raise ValueError("requires original 1792x672 stereo video and matching fps")
        sensor_path=calibration/"binocular"/(cid+".json")
        sensor=json.loads(sensor_path.read_text(encoding="utf-8"))["sensor0"]
        transform=scene["bcam-transforms"][scene["bcam-keys"].index(cid)]
        composed=compose_floor_camera(transform,scene_global_transform(scene))
        matrix,polygon,stats=derive(sensor,composed,bounds)
        offset=(datetime.fromisoformat(item["timestamp"])-epoch).total_seconds()
        configs.append({"id":cid,"path":str(video),"offset_seconds":offset,
                        "homography":matrix,"calibration_polygon":polygon,
                        "analysis_roi":[0,0,896,672]})
        reports.append({"camera":cid,"video_sha256":file_sha256(video),
                        "sensor_sha256":file_sha256(sensor_path),**stats})
    args.output.mkdir(parents=True,exist_ok=False)
    report={"scope":"Approximation of supplied calibration, not ground-truth physical accuracy. "
                    "Only left stereo image and sampled domain; manifest times are not independent sync proof.",
            "scenario_manifest_sha256":file_sha256(manifest_path),"scene_sha256":file_sha256(scene_path),
            "implementation_sha256":file_sha256(__file__),"derivation_sha256":file_sha256(Path(__file__).with_name("derive_site03_plane_mapping.py")),
            "cameras":reports}
    (args.output/"config.json").write_text(json.dumps({"name":scenario.name,"cameras":configs},indent=2))
    (args.output/"calibration-report.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
