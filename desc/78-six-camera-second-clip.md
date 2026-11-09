# Six-camera evaluation on the second site03 clip

The separate 007 clip has six cameras, but the existing direct-pose and baseline comparison processes only C0001055 and C0001056. This predeclared follow-up uses all six pinned videos and existing calibration, with the same fixed detector models, confidence 0.1, image size 640, ByteTrack, ankle confidence 0.5, duplicate containment 0.9, association radius 0.5, support of at least 10 frames and five consecutive frames, and unchanged illustrative north/south regions and event settings. Generate the two-camera default and the six-camera comparison into separate directories; retain input and script hashes and do not use reference labels for association.

This is a second recording from the same site and calibration. Its reference and two-camera event failure have already been inspected, so it is development evidence, not a blind held-out evaluation. Compare coverage, spatial conflicts, reference-near proxies and existing region-event candidates without asserting identity accuracy, recall or real business outcomes. Preserve the default two-camera behavior and explicitly show missing cameras or input mismatch. Validate the CLI and all output artifacts and rerun the full relevant test suite.


## Results

Both modes completed with the same model settings. Source videos, reference, scene, per-camera calibration, model weights and script hashes were checked. The journey builder checked that every eligible input observation was retained exactly once in hypothesis sources.

| Mode | Pipeline | Source observations | Research hypotheses | Multicamera hypotheses | Reference-near pairs | Unmatched predicted positions | Spatial conflicts |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Two cameras | baseline | 423 | 10 | 1 | 270 | 128 | 0 |
| Two cameras | direct pose | 537 | 12 | 1 | 418 | 62 | 2 |
| Six cameras | baseline | 470 | 18 | 2 | 278 | 157 | 0 |
| Six cameras | direct pose | 727 | 22 | 2 | 429 | 218 | 5 |

The six-camera direct pipeline provides 11 more reference-near pairs than the two-camera direct pipeline, but also 156 more unmatched predicted positions and three more conflicts. Unmatched predictions are not automatically false positives: the published reference does not independently establish full visibility and annotation coverage. Differences in association and inputs prevent attributing the change to one camera or interpreting the counts as precision or identity accuracy. Frame observations are correlated.

With the unchanged illustrative north/south regions, the reference contains a candidate transition at exit frame 358 and arrival frame 364. Both baseline and direct hypotheses produced no uninterrupted or interrupted candidate in either camera mode. Therefore adding four cameras did not recover that event in this clip. Neither the example regions nor the reference-near identities represent verified customer behavior.

## Reproduction and limitations

Run the following commands in the existing project .venv after preparing the pinned 007 data and models. The first set preserves the historical two-camera output; the second writes a separate six-camera output.

    .venv/bin/python scripts/compare_site03_holdout.py
    .venv/bin/python scripts/evaluate_site03_holdout_journeys.py
    node scripts/compare_site03_holdout_events.js
    .venv/bin/python scripts/compare_site03_holdout.py --all-cameras
    .venv/bin/python scripts/evaluate_site03_holdout_journeys.py --all-cameras
    node scripts/compare_site03_holdout_events.js --all-cameras

Outputs are ignored under data/processed/site03-007-comparison and data/processed/site03-007-six-comparison. The shared mode definition is hashed in the inference and journey reports; the event script verifies the journey and mode code hashes before consuming the hypotheses. This is not the independent site07 test and is not a reason to promote the six-camera research variant. Further work should investigate where unmatched observations originate and evaluate identity and events against suitable independent evidence.


## Wrap-up verification

Both camera modes were rebuilt and the event command verified the current journey and mode source hashes. The site03-only research verifier passed, including 124 Python unit tests and the JavaScript checks. These checks establish reproducibility and mode isolation for the available local inputs; they do not establish person identity or business acceptance.
