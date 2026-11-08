# Native geometry comparison and cross-view consistency

2026-11-07. W05 numerical evidence; W06 exploratory candidates only.

scripts/probe_native_quaternion.py extracts the exact upstream quaternion product from fixed source header, compiles a minimal C++ wrapper and compares all 418 local observations against the source-aligned Python floor probe. Maximum differences: camera1 3.55e-15, camera2 7.11e-15. This cross-checks the arithmetic and conventions used in the probe. It does not build complete native camera construction, calibration caches, JSON parser or stereo rectification; shared source assumptions can still be wrong.

scripts/probe_site02_consistency.py adapts only candidate_in_domain rows and reuses walkflows.candidates.candidates_at_frame. Multiple candidates in either camera are excluded from this diagnostic, not silently assigned. Same frame index is an explicit assumption, not a synchronization result.

Zero-offset result: 143 common observed frames, one excluded for multiple candidates, 142 single-candidate pairs; median distance 0.4935439 m, zero pairs within 0.25 m, 85 within 0.50 m, all within 1.0 m. Signed camera2-minus-camera1 median displacement is approximately [-0.3972,-0.2473] m. This suggests a substantial cross-view discrepancy under the assumed correspondence. It does not establish that every pair belongs to the same person or identify the cause.

The initial offset sweep changed its support as frame coverage changed, so it could confound timing and missing-data effects. Added a fixed 102-frame support set available uniquely at every offset -5..5. Median distances remain 0.4673..0.4865 m; offset0 is 0.4809 m. Do not pick the smallest median as a calibrated offset: spatial bias, occlusion, trajectory shape and correlated samples can dominate. The historical 20.666ms metadata difference is separate evidence and not a justified clip correction.

Conditional comparison of the longest in-domain local track per camera with the single reference path gives median distances 0.3053 m (ID1,212 observations) and 0.5962 m (ID2,144 observations). These are provisional correspondence diagnostics, not accuracy scores: identity alignment, reference semantics and full coverage are not validated. No bias correction was fitted or applied.

Decision: retain local and experimental spatial candidate outputs, do not enable global ID merging, and do not enlarge fusion radius to conceal discrepancy. Prioritize existing physical calibration correspondences and footpoint visibility. Full TensorRT installation does not directly answer these geometry questions.

Reproduction: scripts/probe_native_quaternion.py and scripts/probe_site02_consistency.py under .venv Python. Outputs: data/processed/site02-native-quaternion and site02-consistency. scripts/verify_site02_research.py sequences eight offline evidence steps and existing unit tests; all pass. Result is consistency evidence, not physical accuracy acceptance.
