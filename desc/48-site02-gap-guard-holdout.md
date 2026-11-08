# Held-out site02 appearance-gap check

The 0.6 appearance-gap threshold and crop settings from document 47 were frozen before running the separate site02 scene. Both 218-frame cameras were processed with the same detector and relaxed ByteTrack association configuration as the earlier site03 experiment. The two source video hashes, model hash, tracker configuration hash and output CSV hashes are recorded in `data/processed/site02-byte095-holdout/run.json`; the analysis verifies them before using the results.

C0001001 produced 227 tracked observations and three within-track gaps; C0001011 produced 194 observations and six gaps. The appearance distances across these nine gaps ranged from 0.091 to 0.362, below the frozen 0.6 threshold; the guard made no splits. For C0001001 and the larger C0001011 ID 2, inspection of paired boxed frames is consistent with the same dark-clothed person either side of the relevant gaps. The far-away C0001011 ID 15 box is too small to establish identity confidently. This is a limited qualitative review, not independently labeled ground truth.

This holdout includes no known positive example of a false identity merge. Therefore zero splits cannot establish true-positive recall, false-split rate, overall tracking accuracy, or threshold generalization. The two cameras share one short scene and limited diversity; the guard remains experimental and is not applied to the product baseline. In particular, its rule still does not detect identity changes between consecutive observations.

Reproduce after preparing the exact relaxed configuration with:

```bash
.venv/bin/python scripts/probe_site03_byte095.py --camera C0001055_v4 --camera C0001056_v2
.venv/bin/python scripts/probe_site02_byte095.py --conf 0.1
.venv/bin/python scripts/evaluate_site02_gap_guard.py
```

Detailed gaps and hashes are in `gap-guard.json` in the holdout output directory. The one-command site03 verification remains separate from this optional GPU comparison.
