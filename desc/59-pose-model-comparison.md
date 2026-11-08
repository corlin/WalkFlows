# Optional YOLO11s-pose comparison

The official [Ultralytics YOLO11 model catalog](https://github.com/ultralytics/yolo11) lists nano and small pose variants. The optional small weights were retrieved from the [Ultralytics YOLO11 repository](https://huggingface.co/Ultralytics/YOLO11); the repository LFS SHA-256 is `1060bda4a27012060eca246f9b2adeea22eabb045a1e58f8d229be29b7ebc2ba` and the file is 20,373,161 bytes. The default pinned nano weights and normal pipeline are unchanged. Both variants use the existing `.venv`, fixed videos, tracking CSVs, 640 input, confidence 0.1 and unique pose/track-box IoU 0.5 matching. No model training or new labels were used.

For C0001055, nano vs small had 201 vs 230 usable, geometrically valid ankle points out of 307 track observations; C0001056 had 326 vs 371 out of 412. These counts are before the local duplicate-box exclusion used in downstream pose-floor candidates. Under a 0.5 unique reference-proximity proxy and on the shared valid-pose support, the first camera had 187 paired samples with median reference distance 0.105 vs 0.099 scene units; the second had 233 paired samples with 0.126 vs 0.135. Under the 1.0 proxy gate, support and comparisons differ. The reference proxy is chosen using box-bottom projection and has no per-camera visibility truth; adjacent frames are correlated. These results do not establish unbiased physical localization accuracy, identity accuracy or generalization.

A separate mixed experiment uses small pose on the two cameras and the existing nano outputs on the other four. With unchanged duplicate, geometry and association rules, pose-qualified source observations increase from 549 to 623 and valid hypothesis-frame points from 381 to 414; both versions retain two supported multi-camera edges and nine research hypotheses. Counts are not people. On the example north/south regions, neither version yields an uninterrupted transition candidate. The nano linked experiment yields a gap-interrupted clue, while the mixed linked experiment does not: in the latter the north exit cannot be confirmed after a gap. Thus better raw coverage did not establish a better result for this event. The small model is not promoted to default without broader independent visibility, position and identity validation.

Reproduce with the existing project environment:

```bash
.venv/bin/python scripts/fetch_site03_pose_s.py
.venv/bin/python scripts/probe_site03_pose_s.py
.venv/bin/python scripts/compare_site03_pose_models.py
.venv/bin/python scripts/evaluate_site03_pose_s_effect.py
node scripts/compare_site03_pose_s_events.js
```

The optional fetch supports resume and verifies the LFS hash before adopting the file; standard pipeline inputs are not changed. Reports, per-camera cache contracts, per-observation paired distances and separate mixed outputs are under `data/processed/site03-pose-s-*` and `site03-pose-model-comparison`. The paired summary handles empty support as unknown and has numerical unit tests. These optional GPU comparisons are intentionally not required by the default verifier.
