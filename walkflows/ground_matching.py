"""Suggest, but never automatically accept, cross-view ground correspondences."""
import cv2
import numpy as np

from walkflows.plane_calibration import validate_coverage_polygon


def _ground_mask(image, polygon):
    height,width=image.shape[:2]
    bounds=[[0,0],[width-1,0],[width-1,height-1],[0,height-1]]
    points=validate_coverage_polygon(polygon,bounds,width,height)
    mask=np.zeros((height,width),np.uint8)
    cv2.fillPoly(mask,[np.rint(points).astype(np.int32)],255)
    return mask



def _region_features(image, mask, limit=4000, max_dimension=1800, padding=64):
    """Detect inside a padded polygon crop before limiting features."""
    x,y,w,h=cv2.boundingRect(mask)
    x0=max(0,x-padding);y0=max(0,y-padding)
    x1=min(image.shape[1],x+w+padding);y1=min(image.shape[0],y+h+padding)
    roi=image[y0:y1,x0:x1];region_mask=mask[y0:y1,x0:x1]
    ratio=min(1.0,max_dimension/max(roi.shape[:2]))
    if ratio<1.0:
        size=(max(1,round(roi.shape[1]*ratio)),max(1,round(roi.shape[0]*ratio)))
        roi=cv2.resize(roi,size,interpolation=cv2.INTER_AREA)
        region_mask=cv2.resize(region_mask,size,interpolation=cv2.INTER_NEAREST)
    sx=(x1-x0)/roi.shape[1];sy=(y1-y0)/roi.shape[0]
    detector=cv2.SIFT_create(nfeatures=0,contrastThreshold=.02)
    keypoints,descriptors=detector.detectAndCompute(roi,region_mask)
    if descriptors is None:return [],None
    order=sorted(range(len(keypoints)),key=lambda i:keypoints[i].response,reverse=True)[:limit]
    result=[]
    for i in order:
        point=keypoints[i]
        point.pt=(point.pt[0]*sx+x0,point.pt[1]*sy+y0)
        result.append(point)
    return result,descriptors[order]


def _suggest_sift(reference, target, reference_polygon, target_polygon, max_matches=40):
    if reference.ndim not in (2,3) or target.ndim not in (2,3) or not 4<=max_matches<=100:
        raise ValueError("invalid images or match limit")
    refmask=_ground_mask(reference,reference_polygon)
    tgtmask=_ground_mask(target,target_polygon)
    ref=cv2.cvtColor(reference,cv2.COLOR_BGR2GRAY) if reference.ndim==3 else reference
    tgt=cv2.cvtColor(target,cv2.COLOR_BGR2GRAY) if target.ndim==3 else target
    rk,rd=_region_features(ref,refmask)
    tk,td=_region_features(tgt,tgtmask)
    result={"status":"insufficient_features","reference_features":len(rk),
            "target_features":len(tk),"matches":[],"inliers":0,
            "scope":"Unverified candidate correspondences; do not assume points lie on ground or share metric coordinates."}
    if rd is None or td is None or len(rk)<4 or len(tk)<4:return result
    matcher=cv2.BFMatcher(cv2.NORM_L2)
    candidates=matcher.knnMatch(rd,td,k=2)
    good=[a for pair in candidates if len(pair)==2 for a,b in [pair] if a.distance<.72*b.distance]
    result["tentative_matches"]=len(good)
    if len(good)<8:
        result["status"]="insufficient_matches";return result
    a=np.float32([rk[m.queryIdx].pt for m in good])
    b=np.float32([tk[m.trainIdx].pt for m in good])
    matrix,mask=cv2.findHomography(a,b,cv2.RANSAC,4.0)
    if matrix is None or mask is None or not np.isfinite(matrix).all():
        result["status"]="estimation_failed";return result
    inliers=mask.ravel().astype(bool)
    result["inliers"]=int(inliers.sum())
    if result["inliers"]<8:
        result["status"]="insufficient_inliers";return result
    projected=cv2.perspectiveTransform(a[inliers,None,:],matrix)[:,0,:]
    errors=np.linalg.norm(projected-b[inliers],axis=1)
    result["inlier_rmse_pixels"]=float(np.sqrt(np.mean(errors**2)))
    if not np.isfinite(result["inlier_rmse_pixels"]) or result["inlier_rmse_pixels"] > 4.0:
        result["status"]="unreliable_fit";return result
    ref_hull=cv2.convexHull(a[inliers]);target_hull=cv2.convexHull(b[inliers])
    result["reference_hull_area_pixels"]=float(cv2.contourArea(ref_hull))
    result["target_hull_area_pixels"]=float(cv2.contourArea(target_hull))
    # A spatially distributed subset is more useful to review than clustered keypoints.
    choices=np.flatnonzero(inliers)
    choices=sorted(choices,key=lambda i:good[i].distance)
    selected=[]; min_spacing=12.0
    for i in choices:
        if all(np.linalg.norm(a[i]-a[j])>=min_spacing and np.linalg.norm(b[i]-b[j])>=min_spacing for j in selected):
            selected.append(i)
        if len(selected)>=max_matches:break
    if len(selected)<4:
        result["status"]="insufficient_distribution";return result
    result["matches"]=[{"reference":a[i].astype(float).tolist(),"target":b[i].astype(float).tolist()} for i in selected]
    result["status"]="candidates"
    return result



_XFEAT_MODEL = None
_XFEAT_SHA256 = "0f5187fd7bedd26c7fe6acc9685444493a165a35ecc087b33c2db3627f3ea10b"


def _xfeat_model():
    global _XFEAT_MODEL
    if _XFEAT_MODEL is not None:
        return _XFEAT_MODEL
    import hashlib
    from pathlib import Path
    weights=Path(__file__).resolve().parents[1]/"data"/"models"/"xfeat.pt"
    if not weights.is_file() or hashlib.sha256(weights.read_bytes()).hexdigest()!=_XFEAT_SHA256:
        return None
    from walkflows.vendor.xfeat.xfeat import XFeat
    _XFEAT_MODEL=XFeat(weights=str(weights),top_k=8192)
    return _XFEAT_MODEL


def _xfeat_region(model,image,mask):
    import torch
    x,y,w,h=cv2.boundingRect(mask);pad=64
    x0=max(0,x-pad);y0=max(0,y-pad)
    x1=min(image.shape[1],x+w+pad);y1=min(image.shape[0],y+h+pad)
    roi=image[y0:y1,x0:x1]
    if min(roi.shape[:2])<32:return np.empty((0,2)),None
    ratio=min(1.0,1280/max(roi.shape[:2]))
    if ratio<1:
        size=(max(32,round(roi.shape[1]*ratio)),max(32,round(roi.shape[0]*ratio)))
        roi=cv2.resize(roi,size,interpolation=cv2.INTER_AREA)
    sx=(x1-x0)/roi.shape[1];sy=(y1-y0)/roi.shape[0]
    features=model.detectAndCompute(model.parse_input(roi),top_k=8192)[0]
    points=features["keypoints"].cpu().numpy()
    points[:,0]=points[:,0]*sx+x0;points[:,1]=points[:,1]*sy+y0
    pixels=np.floor(points).astype(np.int64)
    pixels[:,0]=np.clip(pixels[:,0],0,mask.shape[1]-1)
    pixels[:,1]=np.clip(pixels[:,1],0,mask.shape[0]-1)
    keep=mask[pixels[:,1],pixels[:,0]]>0
    indexes=np.flatnonzero(keep)[:4096]
    return points[indexes],features["descriptors"][torch.as_tensor(indexes,device=model.dev)]


def _suggest_xfeat(reference,target,reference_polygon,target_polygon,max_matches):
    model=_xfeat_model()
    if model is None:return None
    a,ad=_xfeat_region(model,reference,_ground_mask(reference,reference_polygon))
    b,bd=_xfeat_region(model,target,_ground_mask(target,target_polygon))
    result={"status":"insufficient_features","reference_features":len(a),"target_features":len(b),
            "matches":[],"inliers":0,"algorithm":"xfeat",
            "scope":"Unverified candidate correspondences; do not assume points lie on ground or share metric coordinates."}
    if ad is None or bd is None or len(a)<4 or len(b)<4:return result
    ai,bi=model.match(ad,bd,min_cossim=.82)
    x=a[ai.cpu().numpy()].astype(np.float32);y=b[bi.cpu().numpy()].astype(np.float32)
    result["tentative_matches"]=len(x)
    if len(x)<8:
        result["status"]="insufficient_matches";return result
    matrix,mask=cv2.findHomography(x,y,cv2.RANSAC,4.0)
    if matrix is None or mask is None or not np.isfinite(matrix).all():
        result["status"]="estimation_failed";return result
    chosen=mask.ravel().astype(bool);result["inliers"]=int(chosen.sum())
    if result["inliers"]<8:
        result["status"]="insufficient_inliers";return result
    projected=cv2.perspectiveTransform(x[chosen,None,:],matrix)[:,0,:]
    errors=np.linalg.norm(projected-y[chosen],axis=1)
    result["inlier_rmse_pixels"]=float(np.sqrt(np.mean(errors**2)))
    if not np.isfinite(result["inlier_rmse_pixels"]) or result["inlier_rmse_pixels"]>4:
        result["status"]="unreliable_fit";return result
    selected=[]
    for i in np.flatnonzero(chosen):
        if all(np.linalg.norm(x[i]-x[j])>=12 and np.linalg.norm(y[i]-y[j])>=12 for j in selected):
            selected.append(i)
        if len(selected)>=max_matches:break
    if len(selected)<4:
        result["status"]="insufficient_distribution";return result
    result["reference_hull_area_pixels"]=float(cv2.contourArea(cv2.convexHull(x[chosen])))
    result["target_hull_area_pixels"]=float(cv2.contourArea(cv2.convexHull(y[chosen])))
    result["matches"]=[{"reference":x[i].astype(float).tolist(),"target":y[i].astype(float).tolist()} for i in selected]
    result["status"]="candidates"
    return result


def suggest_ground_matches(reference,target,reference_polygon,target_polygon,max_matches=40):
    primary=_suggest_sift(reference,target,reference_polygon,target_polygon,max_matches)
    primary["algorithm"]="sift"
    if primary["status"]=="candidates":return primary
    try:
        fallback=_suggest_xfeat(reference,target,reference_polygon,target_polygon,max_matches)
    except (ImportError, OSError, RuntimeError, ValueError, cv2.error) as exc:
        primary["fallback_status"]="unavailable"
        return primary
    if fallback is not None and fallback["status"]=="candidates":
        fallback["sift_status"]=primary["status"]
        return fallback
    primary["fallback_status"]=fallback["status"] if fallback is not None else "model_not_installed"
    return primary



def alignment_preview(matches, target_polygon, reference_shape):
    """Project the target outline into the reference image as an unverified preview."""
    try:
        if len(matches)<4:return {"status":"unavailable"}
        source=np.asarray([m["target"] for m in matches],np.float64)
        target=np.asarray([m["reference"] for m in matches],np.float64)
        polygon=np.asarray(target_polygon,np.float64)
        if (source.ndim!=2 or source.shape[1]!=2 or target.shape!=source.shape
                or polygon.ndim!=2 or polygon.shape[1]!=2 or len(polygon)<3
                or not np.isfinite(source).all() or not np.isfinite(target).all() or not np.isfinite(polygon).all()):
            return {"status":"unavailable"}
        matrix,inliers=cv2.findHomography(source,target,cv2.RANSAC,4.0)
        if matrix is None or inliers is None or int(inliers.sum())<4 or not np.isfinite(matrix).all():
            return {"status":"unavailable"}
        pts=np.column_stack((polygon,np.ones(len(polygon))))
        mapped=pts@matrix.T
        denominator=mapped[:,2]
        scales=np.linalg.norm(matrix[2])*np.linalg.norm(pts,axis=1)
        if np.any(np.abs(denominator)<=1e-10*scales) or np.any(np.sign(denominator)!=np.sign(denominator[0])):
            return {"status":"unavailable"}
        projected=mapped[:,:2]/denominator[:,None]
        bound=4*max(reference_shape[:2])
        if not np.isfinite(projected).all() or np.max(np.abs(projected))>bound:
            return {"status":"unavailable"}
        hull=cv2.convexHull(source[inliers.ravel().astype(bool)].astype(np.float32))
        outside=sum(cv2.pointPolygonTest(hull,tuple(map(float,p)),False)<0 for p in polygon)
        if outside > len(polygon)/2:
            return {"status":"excessive_extrapolation","inliers":int(inliers.sum()),
                    "outside_control_hull_vertices":int(outside),"polygon_vertices":len(polygon)}
        return {"status":"preview","target_in_reference":projected.tolist(),"inliers":int(inliers.sum()),
                "outside_control_hull_vertices":int(outside),"polygon_vertices":len(polygon),
                "scope":"Unverified projection of target coverage onto reference image; not a metric floor plan."}
    except (ValueError,TypeError,KeyError,cv2.error,np.linalg.LinAlgError):
        return {"status":"unavailable"}


def handle_match_request(handler, cameras):
    """Read-only matching for explicitly exposed cameras, bounded and same-origin."""
    import json
    from urllib.parse import urlsplit
    # A single server instance shares this class-level guard.
    guard=getattr(handler,"_ground_match_guard",None)
    if guard is None:
        # Avoid lazy-init races by installing the guard when the handler is built.
        handler.send_error(503,"Matching unavailable");return
    if urlsplit(handler.path).path!="/ground-match":
        handler.send_error(404);return
    origin=handler.headers.get("Origin","")
    host=handler.headers.get("Host","")
    if origin!="http://"+host:
        handler.send_error(403,"Same-origin request required");return
    try:
        length=int(handler.headers.get("Content-Length","0"))
    except ValueError:
        handler.send_error(400);return
    if length<=0 or length>65536:
        handler.send_error(413);return
    if not guard.acquire(blocking=False):
        handler.send_error(429,"Matching busy");return
    try:
        request=json.loads(handler.rfile.read(length))
        if not isinstance(request,dict):raise ValueError("invalid request")
        ref=request["reference"];target=request["target"]
        if ref==target or ref not in cameras or target not in cameras:
            raise ValueError("select two distinct project cameras")
        def frame_for(cid,index):
            if type(index) is not int or index<0 or index>100000000:
                raise ValueError("invalid frame number")
            cap=cv2.VideoCapture(str(cameras[cid]))
            try:
                if not cap.isOpened():raise ValueError("video unavailable")
                cap.set(cv2.CAP_PROP_POS_FRAMES,index)
                ok,frame=cap.read()
                if not ok:raise ValueError("cannot decode frame")
                return frame
            finally:cap.release()
        reference=frame_for(ref,request["reference_frame"])
        target_frame=frame_for(target,request["target_frame"])
        for key in ("reference_polygon","target_polygon"):
            if not isinstance(request.get(key),list) or len(request[key])>256:
                raise ValueError("invalid polygon")
        result=suggest_ground_matches(reference,target_frame,request["reference_polygon"],request["target_polygon"])
        result["alignment_preview"]=alignment_preview(result["matches"],request["target_polygon"],reference.shape)
        reference_points=request.get("reference_points",[])
        plane_points=request.get("plane_points",[])
        if reference_points or plane_points:
            from walkflows.plane_calibration import fit_homography
            mapping=fit_homography(reference_points,plane_points)["homography"]
            result["plane_mode"]="existing_reference"
            result["reference_seed"]=None
        else:
            polygon=np.asarray(request["reference_polygon"],dtype=np.float64)
            seeds=polygon.tolist()
            if len(seeds)==3:seeds.append(polygon.mean(axis=0).tolist())
            from walkflows.plane_calibration import fit_homography
            mapping=fit_homography(seeds,seeds)["homography"]
            result["plane_mode"]="reference_image"
            result["reference_seed"]={"image_points":seeds,"plane_points":seeds}
        if result["matches"]:
            points=np.asarray([item["reference"] for item in result["matches"]],np.float64)
            m=np.asarray(mapping,dtype=np.float64)
            raw=np.column_stack((points,np.ones(len(points))))@m.T
            scales=np.linalg.norm(m[2])*np.linalg.norm(np.column_stack((points,np.ones(len(points)))),axis=1)
            safe=(np.abs(raw[:,2])>1e-12*scales)
            if not safe.all():raise ValueError("reference mapping near projective horizon")
            world=raw[:,:2]/raw[:,2,None]
            if not np.isfinite(world).all():raise ValueError("invalid reference projection")
            for pair,xy in zip(result["matches"],world):pair["plane"]=xy.tolist()
        result.update(reference=ref,target=target,reference_frame=request["reference_frame"],target_frame=request["target_frame"])
        body=json.dumps(result,ensure_ascii=False,allow_nan=False).encode("utf-8")
        handler.send_response(200);handler.send_header("Content-Type","application/json; charset=utf-8")
        handler.send_header("Content-Length",str(len(body)));handler.end_headers();handler.wfile.write(body)
    except (ValueError,KeyError,TypeError,cv2.error,json.JSONDecodeError) as exc:
        handler.send_error(400,str(exc))
    finally:
        guard.release()
