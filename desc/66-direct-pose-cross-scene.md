# Direct pose tracking on site02

The site03 direct-pose candidate was also run on both existing 218-frame site02 videos. Site02 was used in earlier exploration and is therefore a cross-scene check, not a blind or untouched holdout. It uses the same 640 input, confidence 0.1, ByteTrack configuration, 0.5 ankle threshold, camera-domain/forward-ray/scene bounds, 0.9 same-frame duplicate containment and one-to-one 0.5 reference-distance gate for both variants. The baseline is the existing YOLO11n detector tracks plus uniquely matched YOLO11n-pose; the candidate uses YOLO11s-pose boxes and keypoints directly. Model size, detector and matching strategy change together. No reference is used to build the tracks.

| Camera | Baseline valid points | Direct valid points | Baseline reference-near frames | Direct reference-near frames |
| --- | ---: | ---: | ---: | ---: |
| C0001001 | 194 | 205 | 193 | 205 |
| C0001011 | 3 | 20 | 3 | 19 |

On frames where both variants match the reference, the first camera has 192 paired frames, with baseline and direct median distances of about 0.109 and 0.098 scene units; the second has only three paired frames, with medians about 0.358 and 0.271. The direct variant has 13 and 16 additional reference-near frames respectively; the first camera also loses one baseline-near frame. One-to-one matching selects at most one prediction for each reference point in a frame.

The baseline has no frames where both cameras simultaneously produce reference-near pose points; the direct variant has 19 such frames, with median cross-camera point separation about 0.214 scene units. These frames are selected by reference proximity and correlated in time, so the separation is not an independent identity or synchronization test. The second camera still has only 20 valid direct pose positions over 218 frames. Neither larger sample counts nor closer selected points establish physical accuracy, recall, identity continuity or customer totals; visibility and reference completeness remain unknown.

Reproduce after the standard site02 preparation and optional weight fetch:

```sh
.venv/bin/python scripts/verify_site02_pose_evidence.py
.venv/bin/python scripts/fetch_site03_pose_s.py
.venv/bin/python scripts/probe_site02_direct_pose.py
```

The ignored `data/processed/site02-direct-pose-holdout/report.json` records hashes, per-frame matches, paired support, versions and assumptions. No additional manual labels or model training were used. More independent scenes and robust identity validation are required before accepting this as a default.
