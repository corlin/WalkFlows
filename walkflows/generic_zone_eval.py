"""Conditional comparison of camera-local zone flows with reference trajectories."""
import math
from collections import Counter, defaultdict


def validate_zones(zones):
    if not isinstance(zones,list) or not zones:
        raise ValueError("invalid zones")
    names=set()
    for zone in zones:
        if not isinstance(zone,dict):
            raise ValueError("invalid zone")
        name,points=zone.get("name"),zone.get("points")
        if not isinstance(name,str) or not name.strip() or name in names or not isinstance(points,list) or len(points)<3:
            raise ValueError("invalid zone")
        names.add(name)
        for point in points:
            if (not isinstance(point,list) or len(point)!=2 or any(
                    isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in point)):
                raise ValueError("invalid zone coordinates")
        area=abs(sum(points[i][0]*points[(i+1)%len(points)][1]-
                     points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points))))/2
        if area<1e-9:raise ValueError("degenerate zone")


def in_polygon(point, polygon):
    x,y=point;inside=False
    for i,(xi,yi) in enumerate(polygon):
        xj,yj=polygon[i-1]
        cross=(x-xi)*(yj-yi)-(y-yi)*(xj-xi)
        if (abs(cross)<1e-9 and min(xi,xj)-1e-9<=x<=max(xi,xj)+1e-9
                and min(yi,yj)-1e-9<=y<=max(yi,yj)+1e-9):
            return True
        if (yi>y)!=(yj>y) and x<(xj-xi)*(y-yi)/(yj-yi)+xi:
            inside=not inside
    return inside


def flows_for_camera(rows,zones,camera,fps,offset,max_duration):
    if not math.isfinite(fps) or fps<=0 or not math.isfinite(max_duration) or max_duration<=0:
        raise ValueError("invalid temporal parameters")
    grouped=defaultdict(list)
    for row in rows:
        if row.get("id") is None or row.get("id")=="" or type(row.get("frame")) is not int or row["frame"]<0:
            continue
        grouped[str(row["id"])].append(row)
    flows=[]
    for ident,points in grouped.items():
        counts=Counter(p["frame"] for p in points)
        valid={}
        for point in points:
            x,y=point.get("x"),point.get("y")
            if (counts[point["frame"]]!=1 or not isinstance(x,(int,float)) or not isinstance(y,(int,float))
                    or not math.isfinite(x) or not math.isfinite(y)):
                continue
            valid[point["frame"]]=(x,y)
        events=[]
        for frame in sorted(valid):
            if frame-1 not in valid:continue
            for index,zone in enumerate(zones):
                before=in_polygon(valid[frame-1],zone["points"])
                after=in_polygon(valid[frame],zone["points"])
                if before!=after:
                    events.append({"frame":frame,"type":"enter" if after else "exit",
                                   "index":index,"zone":zone["name"]})
        events.sort(key=lambda e:(e["frame"],e["index"]))
        for i in range(len(events)-1):
            a,b=events[i],events[i+1]
            if (a["type"]!="exit" or b["type"]!="enter" or a["index"]==b["index"]
                    or b["frame"]<=a["frame"] or (b["frame"]-a["frame"])/fps>max_duration
                    or (i>0 and events[i-1]["frame"]==a["frame"])
                    or (i+2<len(events) and events[i+2]["frame"]==b["frame"])):
                continue
            if any(frame not in valid for frame in range(a["frame"],b["frame"]+1)):
                continue
            flows.append({"camera":camera,"id":ident,"from":a["zone"],"to":b["zone"],
                          "exit_frame":a["frame"],"arrival_frame":b["frame"],
                          "exit_time":offset+a["frame"]/fps,"arrival_time":offset+b["frame"]/fps})
    return sorted(flows,key=lambda x:(x["arrival_time"],x["camera"],x["id"]))


def nearby_flows(prediction,references,tolerance):
    if not math.isfinite(tolerance) or tolerance<0:
        raise ValueError("invalid time tolerance")
    return [r for r in references if prediction["from"]==r["from"] and prediction["to"]==r["to"]
            and abs(prediction["exit_time"]-r["exit_time"])<=tolerance
            and abs(prediction["arrival_time"]-r["arrival_time"])<=tolerance]
