# site02 complete GPU local-tracking experiment

2026-11-07; corlin; /home/corlin/WalkFlows. Research probe, not a production pipeline.

## Reproduction

`.venv/bin/python scripts/probe_site02.py`
`.venv/bin/python scripts/probe_site02.py --conf 0.10 --output data/processed/site02-gpu-conf010`

Torch 2.9.1+cu128, torchvision 0.24.1+cu128, Ultralytics 8.3.162, GPU 0 RTX 5060 Ti. YOLO11n downloaded from publisher Ultralytics/YOLO11 on Hugging Face; SHA256 0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1. This hashes the downloaded artifact; it is not a separate upstream signature verification. No training. Each camera gets a new model/tracker; left eye only. Fixed dataset revision and both video checksums match document 10.

## Results

| Detector conf | Camera | Frames | Track observations | Local IDs | Zero-track frames | Processing seconds |
|---|---|---:|---:|---:|---:|---:|
| 0.25 | C0001001 | 218 | 225 | 4 | 2 | 7.69 |
| 0.25 | C0001011 | 218 | 157 | 6 | 97 | 3.95 |
| 0.10 | C0001001 | 218 | 227 | 4 | 2 | 7.73 |
| 0.10 | C0001011 | 218 | 191 | 6 | 74 | 4.29 |

Times cover decode/tracking/render/encode loop, excluding model construction. They are single-run observations with order/warmup effects, not a hardware benchmark. Outputs include complete frame ledgers, local observation CSVs, annotated MP4s and run.json under data/processed/site02-gpu-probe and site02-gpu-conf010. All four output videos decode to 218 frames; CSV frame indices and observation totals were checked. Four existing unit tests pass.

## Interpretation and limitations

Installed ByteTrack YAML uses high=0.25, low=0.10, new_track=0.25. Detector conf=0.25 discards the low-score band before the tracker; lowering to 0.10 admits that band for secondary association. C0001011 zero-track frames decrease from 97 to 74, but ID count stays six. This is a continuity observation, not measured recall or identity accuracy; additional boxes might include false positives. Keep both outputs. Do not promote 0.10 as a validated optimum.

The returned_boxes column is post-tracker output, not an independent raw detector count. Zero-track frames do not prove no people were present. Local IDs are not unique customers and cannot be summed across cameras. Reference coverage and floor alignment have not been independently established.

Published short-clip manifest sets both timestamps to zero. The embedded historical config in ground-truth.json records 15:00:00.018725 and 15:00:00.039391 (+20.666 ms difference). This historical difference is evidence to investigate, not a justified correction for the distributed clips. Preserve original start-frame=4702 as provenance; do not add it twice to local clip frames.

## Tradeoff and next milestone

Use conf=0.10 as a candidate continuity baseline while retaining conf=0.25 as control. Next inspect longest gaps, distinguish detection failure from tracker filtering, and verify stereo projection using upstream calibration. Do not spend time on business funnels or cross-camera identity before spatial/time contracts are validated. Keep the upstream multiview route open; compiling its no-pose CLI would not validate actual tracking.

License scope remains internal noncommercial research: CC BY-NC 4.0 data; detector/tracker dependency and weights require separate license review before distribution.
