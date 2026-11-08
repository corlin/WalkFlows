"""Read-only verification of fixed site03 inputs, calibration and weights."""
from pathlib import Path
import os,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.local_cli import check_inputs
if os.geteuid()==0:raise SystemExit('Use the non-root WSL user')
raise SystemExit(check_inputs())
