# Observation quality adapter implementation plan

Goal: implement the observation/position-quality contract from desc/02 and the uncertainty boundary from desc/23, without implementing tracking or fusion again.
Architecture: immutable local observation and quality records, explicit hard rejection and verification reasons, dependency-injected upstream Observation factory. Strict default blocks unvalidated inputs; research override labels uncertain and cannot bypass invalid geometry or duplicate-candidate gates.
Files: walkflows/quality.py; tests/test_quality.py; scripts/export_site02_quality.py.
Constraints: corlin and home workspace; Python uv; no new runtime dependencies; no global IDs; preserve every input in export; keep complete 218-frame ledger.
Review risks: nonfinite positions/confidence; invalid local keys; changing same numeric ID across cameras; experimental override bypassing hard exclusions; unknown foot/sync/floor state accidentally accepted; local duplicate candidates.
Tasks:
- [x] Write failing behavioral tests for strict and research modes plus invalid inputs and provenance.
- [x] Implement minimal immutable contract and upstream adaptation, run tests.
- [x] Export all 418 observations with reasons and frame coverage; call actual pinned upstream factory for research candidates only.
- [x] Verify integration and update current state/roadmap; no identity/accuracy acceptance inferred from contract tests.
