# site03 tracker comparison

The 400-frame left-eye recordings for C0001055_v4 and C0001056_v2 were rerun with the same YOLO11n weights, confidence 0.1, 640 input size, CUDA device, videos and dependencies as the fixed ByteTrack baseline, using the installed default `botsort.yaml`. The config enables sparse optical-flow camera-motion compensation and explicitly has `with_reid: False`; it is not an appearance-ReID experiment. The video, model, tracker configs and output hashes are recorded in the run and comparison JSON files.

The first camera produced 307 vs 308 tracked observations and four local IDs in each run; the second produced 412 vs 416 observations and six local IDs in each run. Mutual same-frame IoU >= 0.8 yielded 279 and 404 unique box correspondences respectively; the unmatched observations remain explicit. The identified baseline IDs 4 and 10 in the first view correspond separately to BoT-SORT IDs 4 and 10; baseline IDs 9 and 14 in the second view likewise correspond separately to IDs 9 and 14. This supports the narrow conclusion that the default configuration does not remove these observed ID breaks. ID numbers or track counts alone are not identity accuracy. Unmatched boxes, position errors and selection bias preclude an overall accuracy ranking.

The source video inspection showed first-view IDs 4 and 10 coexist at frames 195?201 with overlapping boxes; second-view ID 9 ends at frame 169 and ID 14 begins at 175. These are investigation candidates, not independently verified person identities. Since this comparison does not demonstrate an improvement, the existing ByteTrack baseline stays in use. ByteTrack itself associates low-score detections with existing tracks ([paper](https://arxiv.org/abs/2110.06864)); tracking literature also cautions that motion and appearance cues can conflict ([DeconfuseTrack](https://openaccess.thecvf.com/content/CVPR2024/papers/Huang_DeconfuseTrack_Dealing_with_Confusion_for_Multi-Object_Tracking_CVPR_2024_paper.pdf)).

Reproduce on the existing project environment:

```bash
.venv/bin/python scripts/probe_site03_botsort.py --camera C0001055_v4 --camera C0001056_v2
.venv/bin/python scripts/compare_site03_trackers.py
```

The experiment is optional and not a prerequisite for the baseline verifier. Its results are under `data/processed/site03-botsort-experiment/`. The runner uses the existing GPU and one project virtual environment; it verifies existing video/model inputs and per-camera output hashes before reuse.
