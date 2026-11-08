"""Cross-check source quaternion product and ground intersection, not full upstream pipeline."""
from pathlib import Path
import csv,json,subprocess,hashlib
import numpy as np
r=Path(__file__).resolve().parents[1];a=r/"data/upstream-research";out=r/"data/processed/site02-native-quaternion";out.mkdir(parents=True,exist_ok=True)
header=(a/"quaternion.hpp").read_text();start=header.index("static void product");end=header.index("QuaternionT<T> operator*",start)
product=header[start:end].replace("QuaternionT<T>","Q")
source="#include <iostream>\n#include <iomanip>\n#include <cmath>\nstruct Q {double x,y,z,w;\n"+product+"};\n"
source+="""int main(){Q q;double u,v,cx,cy,cz;while(std::cin>>q.x>>q.y>>q.z>>q.w>>u>>v>>cx>>cy>>cz){double n=std::sqrt(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w);Q qi{-q.x/n,-q.y/n,-q.z/n,q.w/n};Q p{u,v,1,0},t,r;Q::product(q,p,t);Q::product(t,qi,r);double k=-cz/r.z;std::cout<<std::setprecision(17)<<cx+k*r.x<<' '<<cy+k*r.y<<' '<<cz+k*r.z<<std::endl;}}
"""
cpp=out/"native-product-probe.cpp";cpp.write_text(source);binary=out/"native-product-probe"
subprocess.run(["g++","-std=c++17","-O2",str(cpp),"-o",str(binary)],check=True)
scene=json.loads((a/"site02_scene01_v1.json").read_text());reports=[]
for camera,et in zip(scene["bcam-keys"],scene["bcam-transforms"]):
    sensor=json.loads((a/(camera+".json")).read_text())["sensor0"]
    with (r/"data/processed/site02-floor-probe"/(camera+"_experimental_floor.csv")).open() as f:rows=list(csv.DictReader(f))
    pix=np.array([[float(x["pixel_x"]),float(x["pixel_y"])] for x in rows]);conditioned=(pix*np.array(sensor["format"])/[896,672]-sensor["center"])*sensor["scale"]
    text=subprocess.check_output([str(r/"data/processed/site02-native-lift/lift-probe")],input="".join(f"{x:.17g} {y:.17g}\n" for x,y in conditioned),text=True)
    terms=np.array([[float(v) for v in line.split()] for line in text.splitlines()]);uv=terms@np.array(sensor["A"]).T
    inputs=[et["rotation"]+[float(u),float(v)]+et["translation"] for u,v in uv]
    native=subprocess.check_output([str(binary)],input="".join(" ".join(format(v,".17g") for v in row)+"\n" for row in inputs),text=True)
    actual=np.array([[float(v) for v in line.split()] for line in native.splitlines()]);expected=np.array([[float(row[k]) for k in ["experimental_x","experimental_y","experimental_z"]] for row in rows])
    np.testing.assert_allclose(actual,expected,atol=1e-11,rtol=1e-11)
    reports.append({"camera":camera,"rows":len(rows),"max_abs_difference":float(np.max(np.abs(actual-expected)))})
report={"status":"pass","source_header_sha256":hashlib.sha256((a/"quaternion.hpp").read_bytes()).hexdigest(),"comparisons":reports,"scope":"Exact upstream quaternion product in minimal wrapper, plus native lift. Does not build or validate full native camera construction, inverse distortion or physical accuracy."}
(out/"result.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
