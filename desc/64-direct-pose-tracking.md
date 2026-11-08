# Direct pose detection and tracking experiment

The existing two-stage pipeline only runs pose inference on frames that already contain a detector track, and only retains poses uniquely matched to one such track. It therefore cannot recover a person absent from the detector tracks. To investigate the long unmatched reference path in document 63, this optional experiment runs the already-pinned YOLO11s-pose model directly on all 400 left-eye frames of C0001056 and tracks its person boxes with ByteTrack. This changes both detector/model size and pipeline ordering, so it cannot isolate which change caused any difference. It does not replace the default pipeline or quality policy.

With identical confidence 0.1, image size 640, ankle score 0.5, calibration/scene bounds, same-camera duplicate-box exclusion and framewise one-to-one reference matching at radius 0.5, the existing baseline produces 326 comparable position observations and 301/23/0 proximity matches to reference IDs 0/1/2. Direct small-pose tracking produces 420 comparable observations and 348/46/24 matches to those IDs. The 24 ID-2 matches come from experimental local track 19 during frames 373?398, with two missing frames. Frame 399 has no reference and is excluded. These samples are temporally correlated; reference proximity is not identity confirmation, accuracy or recall, and the two pipelines do not have identical source boxes. Additional raw detections can be false positives.

Qualitative inverse projection at frames 150, 220 and 300 places reference ID 2 near the camera's lower edge, where a seated figure is partly occluded by furniture. The same reference projection was outside the valid left-eye inverse domain for the other five cameras in these samples. This is an exploratory numerical inverse, not independently verified visibility or proof of the person's identity. It explains why more boxes alone cannot establish a full recovery: the new ID-2 proximity evidence occurs mainly near the end of the clip, not throughout the 295-point reference path.

Reproduce with the existing project environment and prepared baseline:

```sh
.venv/bin/python scripts/fetch_site03_pose_s.py
.venv/bin/python scripts/probe_site03_pose_direct.py
```

The ignored output directory `data/processed/site03-direct-pose-probe/` contains tracked boxes, selected ankles, projection and frame-level matching evidence plus input and output SHA-256 hashes. The optional GPU experiment is not part of the default verifier. No new manual annotation or training was used. Before promotion, evaluate independent clips, identity continuity, localization and downstream region events, including failures and false positives.
