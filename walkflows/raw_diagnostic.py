"""Reference-near raw detection diagnostics; no identity or recall claim."""
import math

from walkflows.multicamera_processing import _project
from walkflows.reference_eval import convert_reference


def summarize_raw(probe, reference_data, reference_id, max_distance, high_confidence):
    if (not math.isfinite(max_distance) or max_distance<=0 or
            not math.isfinite(high_confidence) or high_confidence<probe["confidence"] or high_confidence>1):
        raise ValueError("invalid diagnostic thresholds")
    reference=convert_reference(reference_data)
    if reference_data.get("start-frame")!=0:raise ValueError("unsupported reference alignment")
    cameras={c["id"]:c for c in probe["project"]["cameras"]}
    if len(cameras)!=len(probe["project"]["cameras"]):raise ValueError("duplicate camera")
    near=[];samples=set();covered=set()
    for row in probe["results"]:
        cid=row["camera"];camera=cameras[cid];frame=row["frame"];model=row["weight_sha256"]
        if (camera["offset_seconds"]!=0 or not math.isclose(1/camera["video"]["fps"],
                reference["frame_duration"],rel_tol=1e-5,abs_tol=1e-7)):
            raise ValueError("reference alignment assumption does not match metadata")
        if type(frame) is not int or frame not in reference["by_frame"]:
            raise ValueError("frame outside reference")
        key=(cid,frame,model)
        if key in samples:raise ValueError("duplicate sample")
        samples.add(key)
        targets=[p for p in reference["by_frame"][frame] if p["id"]==reference_id]
        if not targets:continue
        covered.add(key);target=targets[0]
        for detection in row["detections"]:
            box=detection["box"];score=detection["confidence"]
            if (len(box)!=4 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in box)
                    or not isinstance(score,(int,float)) or not math.isfinite(score)):continue
            x,y=_project(camera["homography"],(box[0]+box[2])/2,box[3],camera.get("calibration_polygon"))
            if x=="" or y=="":continue
            distance=math.hypot(x-target["x"],y-target["y"])
            if distance<=max_distance:
                near.append({"camera":cid,"frame":frame,"weight_sha256":model,
                             "confidence":score,"distance":distance})
    return {"sampled_camera_model_frames":len(samples),"samples_with_reference":len(covered),
            "frames_with_near_detection":len({(x["camera"],x["frame"],x["weight_sha256"]) for x in near}),
            "frames_with_high_near_detection":len({(x["camera"],x["frame"],x["weight_sha256"]) for x in near
                                                   if x["confidence"]>=high_confidence}),
            "near_detections":near}
