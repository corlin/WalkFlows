"""Run local research evidence pipeline without network, model downloads or training."""
from pathlib import Path
import subprocess,json,sys,time
root=Path(__file__).resolve().parents[1]
out=root/"data/processed/site02-research-verification";out.mkdir(parents=True,exist_ok=True)
steps=["audit_site02_calibration.py","export_site02_reference.py","probe_native_lift.py","probe_site02_floor.py","probe_site02_reference_overlay.py","probe_native_quaternion.py","probe_site02_stereo.py","probe_site02_crossview_features.py","review_site02_roi.py","probe_site02_consistency.py","probe_retailvision_uncertainty.py","export_site02_quality.py","verify_site02_artifacts.py"]
report={"status":"running","steps":[],"scope":"Numerical/source contracts and artifact consistency; no independent physical accuracy, synchronization or identity validation."}
for name in steps:
    start=time.perf_counter();p=subprocess.run([sys.executable,str(root/"scripts"/name)],cwd=root,capture_output=True,text=True)
    (out/(name+".log")).write_text(p.stdout+p.stderr)
    report["steps"].append({"script":name,"exit_code":p.returncode,"elapsed_s":time.perf_counter()-start})
    (out/"report.json").write_text(json.dumps(report,indent=2))
    print(name,'PASS' if p.returncode==0 else 'FAIL',flush=True)
    if p.returncode:
        report["status"]="failed";(out/"report.json").write_text(json.dumps(report,indent=2));raise SystemExit(p.returncode)
p=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],cwd=root,capture_output=True,text=True)
(out/"unit-tests.log").write_text(p.stdout+p.stderr)
report["unit_tests_exit_code"]=p.returncode;report["status"]="pass" if p.returncode==0 else "failed"
(out/"report.json").write_text(json.dumps(report,indent=2));print('research suite',report["status"])
raise SystemExit(p.returncode)
