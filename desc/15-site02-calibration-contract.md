# site02 calibration contract audit

2026-11-07. W05 in progress; physical floor accuracy and cross-camera fusion remain unvalidated.

Fixed source commit: 7e334db96ca7ab685628365a2eaa2d5e8117eac3 of prcvlabs/multiview. Local assets: data/upstream-research/. Source SHA256 inventory: data/processed/site02-calibration-audit/source-hashes.json.

Recovered scene, both binocular JSON files (each embeds two sensors), distorted-camera.hpp, polynomial-model.hpp and TOUR.md. Both left sensors use polynomial<8>, coefficients 2x45, calibration 2592x1944, working 896x672, scale 2.892857142857143 on both axes. Baselines: 0.1670798913 and 0.1642977341 m.

Camera 1: 223/227 box-bottom centers inside calibration hull; four outside. Camera 2: 191/191 inside. Inclusion is a model-domain check, not a physical position accuracy result. Occluded box bottoms are not necessarily visible feet.

Reference: one path, 218 points, frames 0-217, grid 38x50, hist_sz=0.1, origin [-0.75,-2.5]. Frames 214-217 have grid [23,50], outside half-open cell bounds. Continuous/inclusive boundary semantics are not ruled out. Preserve and flag these points; do not silently clip or call them erroneous labels.

polynomial-model.hpp conditions pixels as (D * working_scale - center) * scale and applies calibration::lift followed by A. It is not OpenCV radial/tangential distortion. The lift coefficient order must be verified from source.

distorted-camera.hpp explicitly defines q as world-to-camera; backproject_ray inverse-applies q to the undistorted homogeneous ray. plane_ray_intersect uses camera center and ray. Use make_distorted_camera_pair and plane_ray_intersect; scene quaternion direction and make_camera_extrinsics still require .cpp verification. Unit quaternion norm does not verify convention.

Decision: do not write an approximate Python projector. Prefer a minimal native geometry invocation over duplicating distortion. Recover transform implementation, lift order and histogram conversion; test with existing upstream calibration correspondences. Follow-up source downloads hit TLS errors this round. Full HyperPose/TensorRT is unnecessary merely to validate geometry.

Before fusion reject outside-hull, parallel-ray and behind-camera projections; retain occlusion uncertainty. Projection round-trip alone cannot establish real spatial accuracy.

Reproduce: .venv/bin/python scripts/audit_site02_calibration.py
Output: data/processed/site02-calibration-audit/audit.json
