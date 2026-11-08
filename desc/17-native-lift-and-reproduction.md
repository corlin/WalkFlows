# Native polynomial lift and offline artifact acceptance

2026-11-07. Work performed as corlin in /home/corlin/WalkFlows.

Recovered fixed-commit calibration-utils.hpp, quaternion.hpp and euclidean-transform.hpp through Windows curl with the local 7890 proxy, writing through wsl -u corlin. WSL curl, direct and proxy routes, GitHub API, CDN route and GitHub connector failed intermittently. A successful host fetch is a useful fallback, not proof that all host downloads are reliable. Download pipeline must check success before writing a destination; one initial failed fetch produced an empty header and was replaced before use.

scripts/probe_native_lift.py extracts the exact upstream lift template from calibration-utils.hpp and compiles it with g++. Only Eigen fixed-vector storage is replaced by a checked std::array shim. This is an isolated native algorithm fixture, not a build of the complete upstream geometry library.

Verified ordering: descending total degree 8 through 0, descending x exponent within each degree: x^8, x^7*y, ..., y^8, x^7, ..., 1. Five asymmetric/negative/zero input cases compare all 45 terms with independent monomial formulas; maximum absolute error 8.881784197001252e-16. Results, exponents, source hash and generated C++ fixture: data/processed/site02-native-lift/.

Reproduce: .venv/bin/python scripts/probe_native_lift.py

Quaternion header declares x,y,z,w and array constructor in that order. This alone is not full scene JSON serialization verification; scene parser and transform composition still need tracing. Do not silently replace the full camera pipeline with assumed quaternion semantics.

Added scripts/verify_site02_artifacts.py as a download-free acceptance entry. It checks fixed video hashes, both camera runs, all six annotated videos, complete per-frame ledgers, observation totals, per-frame counts, local IDs, relative timestamps and reference conversion for all three tracking settings. All checks pass. It validates consistency, not recall, identity correctness or physical calibration accuracy.

Reproduce: .venv/bin/python scripts/verify_site02_artifacts.py

Decision: retain the isolated native fixture as a contract test and proceed to camera construction/transform parsing. No full HyperPose/TensorRT installation is needed for these geometric questions. W05 remains in progress; W06 must wait for valid floor positions and synchronization evidence.
