# Reference floor export and transform semantics

2026-11-07. Evidence milestone under W05; not a completed camera-to-floor calibration.

## Implementation-level findings

Fixed multiview commit 7e334db96ca7ab685628365a2eaa2d5e8117eac3, geometry/projective/distorted-camera.cpp: make_camera_extrinsics(et) returns camera center et.translation and rotation et.rotation.inverse(). The header defines the resulting rotation as world-to-camera. make_distorted_camera_pair initializes each sensor model and applies working image format; the right camera transform comes from make_et1(et0). Thus the scene transform rotation and the DistortedCamera rotation are inverses. This is source-level verification, not an empirical calibration accuracy measurement.

cost-functions/floor-histogram.hpp unproject_hist_xy computes grid_x * hist_sz + top_left_x, and similarly y. There is no half-cell offset. The corresponding forward function produces floating coordinates, rather than requiring an integer cell index. This clarifies why reference coordinates must not be treated solely as image array indices.

The guessed path calibration/polynomial.hpp returned 404, rather than a network error. polynomial-model.hpp actually includes calibration/calibration-utils.hpp. Retrieval of that header and quaternion/EuclideanTransform implementation still failed with TLS errors. Polynomial lift ordering and serialization convention remain unresolved. Do not invent coefficient order from the JSON dimensions.

## Reference artifact

scripts/export_site02_reference.py exports all 218 reference points into data/processed/site02-reference-floor/reference_floor.csv. It preserves original grid coordinates, clip frame, relative time, converted floor coordinates and both half-open-grid and closed-scene-bound flags. Original start-frame=4702 remains provenance in source JSON; it is not added to the clip-relative time.

Four points at frames 214-217 have grid y=50 and world y=2.5. All 218 points lie inside closed scene bounds [-0.75,-2.5,3,2.5]. This resolves the apparent conflict with half-open grid height=50 at the coordinate-conversion level; it does not prove how every upstream raster consumer handles boundary points.

reference-floor.png visibly labels itself UPSTREAM REFERENCE ONLY, x right / y down. It shows the upstream reference and supplied entrance polygon; it is not a measured store layout, reconstructed customer path or detector output. No zone dwell or business funnel has been derived.

## Dependency tradeoff

Reviewed build/environment.yml and setup-env.sh. Native upstream environment includes GCC13, CMake, OpenCV4.12, Eigen3.4, Boost1.86 and CUDA12.8; HyperPose adds TensorRT10 separately. Existing host has cmake/g++ but micromamba and ninja are absent from default PATH. User-space conda exists; no environment has been modified. Do not run the complete installer merely to calculate a planar ray intersection. Prefer a minimal upstream geometry target, and keep Python runtime/dependencies under uv.

Next: recover calibration-utils.hpp/lift, quaternion serialization and existing native geometric testcases; determine minimal compilation dependencies. Compare against upstream behavior before enabling projection in the baseline. Full HyperPose/TensorRT tracking is a separate decision. W06 cannot be validated by assuming zero camera offset or matching nearest projected points.

Reproduce reference export: .venv/bin/python scripts/export_site02_reference.py
Source checksums are recorded in data/processed/site02-calibration-audit/source-hashes.json.
