# WSL progress and critical review

Updated 2026-11-07; corlin; /home/corlin/WalkFlows.

## Evidence

GPU repair: see 11-wsl-environment.md. site02 C0001001_v10.mp4 matches SHA256 9926ccdd05358cab83c292d9a62f2196961de9439e97857c592a75d2993d5276. All 218 frames decode at 15 fps; stereo 1792x672; each eye 896x672. Inspection JSON and contact sheet: data/processed/wsl-site02-inspection/. This proves input decoding only.

## Source review and decisions

- multiview fixed commit 7e334db96ca7ab685628365a2eaa2d5e8117eac3 README supports user-space CUDA 12.8 and TensorRT 10 installation. Reported upstream hardware is RTX 3090 / Ubuntu 24.04, not this WSL / RTX 5060 Ti. HyperPose is optional and requires separate validation. Do not equate compiling the CLI with working pose tracking.
- RetailVision fixed commit a0fae89b97fa45dd7e86ac0627935a682ec68ce8 spatial/fusion.py requires trustworthy floor coordinates, uses greedy grouping and at most one observation per camera per group. Confidence aggregation assumes independence and is not a calibrated business probability. Fusion radius cannot repair invalid calibration.
- Existing run_baseline.py requires CITIC calibration and allows CPU/MPS only. It cannot be applied unchanged to site02. Preserve frame/time and local camera IDs in the first GPU experiment; do not fabricate floor coordinates, global identity or customer totals.
- A stereo right eye is not an additional customer view for counting. One reference track does not establish complete annotation coverage. Sparse visual checks cannot estimate recall.

## Next acceptance milestone

Recover both videos, manifest, reference and fixed pretrained weights with checksums. Process all frames of each left eye with existing detector/tracker components. Persist empty-frame coverage, local observations, device, hashes and timings. Only then decide calibration adaptation and cross-view fusion. No training or new manual annotations.

Network: domestic PyPI works; HF and GitHub assets have intermittent TLS errors. Use partial files and resumable transfers; do not count partial downloads as installed assets.

## Milestone update

Both input videos, manifest, reference and pretrained weights were recovered; full two-camera local GPU runs completed. Earlier download blockers above are historical. Results and next decision: [site02 GPU experiment](13-site02-gpu-baseline.md).
