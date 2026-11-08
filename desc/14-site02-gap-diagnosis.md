# site02 gap diagnosis and resolution control

2026-11-07. Independent detector outputs were compared by original frame number with saved conf=0.10 / imgsz=640 tracking. Both experiments cover all 218 frames per camera; no new labels were made.

## Gap decomposition at 640

Camera 1 has one two-frame gap (41-42). Camera 2 zero-track runs: 0-26, 33-41, 77-87, 95-104, 192-194, 202-203, 206-217 (74 frames total).

Among camera 2 zero-track frames: 45 have no independent detection at conf>=0.10, 29 have at least one; only 2 have a detection at conf>=0.25. This partitions observed output behavior, not ground-truth detection failures: absence of a box does not establish absence/presence of a person.

A contact sheet of frames 0,15,26,40,82,100,210 shows people partially occluded by the counter with strong privacy blur, including sampled frames without boxes. This is qualitative evidence only, not a complete annotation or recall estimate.

## Resolution control rejects a tempting change

| Metric, camera 2 | imgsz 640 | imgsz 960 |
|---|---:|---:|
| Independent detector positive frames, conf>=0.10 | 173 | 166 |
| Independent detector high-score frames, conf>=0.25 | 124 | 112 |
| Full tracking zero-output frames | 74 | 111 |
| Local track IDs | 6 | 8 |
| Track observations | 191 | 146 |
| Tracking loop seconds (single run) | 4.29 | 4.45 |

Within the OLD 74-frame gap set, 960 yields detections in 38 frames rather than 29, and high scores in 18 rather than 2. Looking only at that subset would misleadingly favor 960; whole-clip detection and actual tracking both worsen. Camera 1 improves from 2 to 0 blank frames and IDs 4 to 3, demonstrating the choice is view dependent. Neither blank-frame count nor ID count is a validated accuracy metric. Do not promote 960; keep 640/conf0.10 as an explicit candidate while preserving all controls.

## Reproduction and artifacts

`.venv/bin/python scripts/diagnose_site02_gaps.py`
`.venv/bin/python scripts/diagnose_site02_gaps.py --imgsz 960 --output data/processed/site02-gap-imgsz960`
`.venv/bin/python scripts/probe_site02.py --conf .10 --imgsz 960 --output data/processed/site02-gpu-conf010-imgsz960`

Independent diagnostic CSVs and summary files: data/processed/site02-gap-diagnostic/ and site02-gap-imgsz960/. Contact sheets are there too. Annotated output and full frame ledgers: site02-gpu-conf010-imgsz960/. All 960 video/CSV frame totals and blank counts were independently checked.

## Research contract and next choice

The fixed multiview data README distinguishes scenes, binocular calibration, sensor distortion, camera positioning and plane data. Scene JSON alone is insufficient to apply a planar transform to raw distorted left-eye pixels. Source: https://github.com/prcvlabs/multiview/blob/7e334db96ca7ab685628365a2eaa2d5e8117eac3/data/README.md . A local snapshot is saved in data/upstream-research/. Scene JSON retrieval failed with TLS error in this round; do not claim its geometry was verified.

Next prioritize recovering the complete calibration asset chain and tracing the upstream pixel-to-ray/plane interfaces. Compare a second pretrained detector only with an explicit evaluation objective and fixed data, not by maximizing box counts. Do not compensate weak detections by inventing floor points or merging global IDs.
