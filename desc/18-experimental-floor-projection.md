# Experimental pixel-to-floor intersection

2026-11-07. W05 research experiment; no validated physical localization or cross-camera identity.

## Source evidence

EuclideanTransform header to_json_str and to_1line_json_str explicitly serialize rotation.x,y,z,w. apply(x) rotates scaled local x then adds translation; inverse_apply subtracts translation then applies conjugate rotation. distorted-camera.cpp converts scene transform into camera center et.translation and world-to-camera et.rotation.inverse(). Combined with backproject_ray inverse application, local sensor rays use the original scene rotation to reach world coordinates. Current scene global transform is identity and per-camera scales are one; the probe explicitly requires these conditions.

## Executable approach and limits

scripts/probe_site02_floor.py uses the compiled exact upstream lift<8> fixture for conditioned distorted pixels, then the stored 2x45 A matrix for normalized undistorted coordinates. It uses scipy quaternion rotation, independently cross-checked against the unit-quaternion vector formula, and intersects the forward ray from camera center with z=0. This is a source-aligned hybrid diagnostic, not the complete upstream DistortedCamera implementation or inverse distortion pipeline. It deliberately does not invoke RetailVision fusion.

Output CSV retains every observation, local ID, pixel center, experimental world position and separate flags for calibration hull, nonparallel forward ray and scene bounds. Rejected positions remain diagnostic rows and must never be consumed as validated floor observations merely because numbers are finite.

## Results

| Camera | Observations | In hull | Forward rays | In scene | All gates | Median floor displacement for +5px y |
|---|---:|---:|---:|---:|---:|---:|
| C0001001 | 227 | 223 | 227 | 219 | 219 | 0.05784 m |
| C0001011 | 191 | 191 | 191 | 144 | 144 | 0.08311 m |

All 418 observations were processed. Plane residual <=4.5e-16 is guaranteed by intersection construction and does not measure calibration error. The +5px displacement is a one-direction sensitivity probe, not a calibrated uncertainty interval. Hull/scene inclusion is not proof of a physically correct footpoint. Camera 2 has 47 outside-scene observations despite all pixels being inside the lens calibration hull; source conventions, detector box truncation/occlusion and actual coverage all remain possible contributors.

## Decision and next evidence

Do not enable global identity or increase fusion radius to absorb these observations. Preserve masks and inspect outside-scene cases against the annotated video. Next compare original native camera construction or existing upstream calibration correspondences, verify parser/composition behavior, and examine cross-camera time alignment. Correct-looking trajectories and round trips do not replace independent physical checks. Avoid nearest-reference matching as an accuracy score while reference coverage/identity is uncertain.

No new labels or training were created. All work used corlin. Reproduce: .venv/bin/python scripts/probe_native_lift.py followed by .venv/bin/python scripts/probe_site02_floor.py. Outputs: data/processed/site02-floor-probe/. Source inventory: data/processed/site02-calibration-audit/source-hashes.json.
