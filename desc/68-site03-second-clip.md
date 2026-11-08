# Additional site03 007 clip comparison

A separate 500-frame site03 clip, `007_site03_sparse_tracks`, was fetched at the dataset revision already pinned by this project. The published manifest lists the same six camera versions and scene key as 006. All six videos, the manifest and existing reference tracks were hash checked; the latter contain two nonempty tracks of 410 and 500 points. The experiment below evaluates only C0001055 and C0001056. It is a different clip from 006 but the same site, cameras and calibration; it is not a blind independent site or proof of generalization.

On each selected camera, the baseline uses YOLO11n detector/ByteTrack plus uniquely matched YOLO11n-pose; the candidate directly tracks YOLO11s-pose outputs. Both use confidence 0.1, 640 input, ankle threshold 0.5, geometric and scene-domain checks, same-frame duplicate exclusion and one-to-one matching to existing reference points at radius 0.5 scene units. The two methods change model and pipeline together, so their individual contributions are not isolated.

| Camera | Baseline valid position observations | Direct valid position observations | Baseline reference-near pairs | Direct reference-near pairs |
| --- | ---: | ---: | ---: | ---: |
| C0001055 | 196 | 203 | 84 | 154 |
| C0001056 | 227 | 334 | 213 | 321 |

Pairs count position observations, not distinct frames or people: the direct runs match reference points in 135 and 296 distinct frames respectively. In C0001055 the median distance across all matched pairs is 0.226 baseline versus 0.317 direct, even though direct has more pairs. On the 56 common frame/reference pairs, the medians are 0.135 versus 0.119; direct has 98 additional and loses 28 baseline-near pairs. For C0001056, 204 common pairs have medians 0.175 versus 0.146; direct has 117 additional and loses nine. These are correlated samples selected by a distance gate; a nearby point is not independently verified identity, and missing reference coverage or visibility prevents interpreting unmatched points as definitive errors or computing unbiased precision/recall. The change in all-sample versus shared-support direction illustrates why coverage and localization must be reported separately.

Reproduce in the existing environment:

```sh
.venv/bin/python scripts/fetch_site03_holdout.py
.venv/bin/python scripts/fetch_site03_pose_s.py
.venv/bin/python scripts/compare_site03_holdout.py
```

The downloader retries and resumes partial files and validates published Git blob or LFS SHA-256 values before use. The ignored `data/processed/site03-007-comparison/report.json` contains each match, input hashes, versions and paired counts. The standard 006 review and baseline are not changed. This experiment provides evidence for further evaluation, not justification for accepting the direct method as a verified identity or business-counting system.

## Two-camera trajectory and event follow-up

The per-camera eligible floor observations are now retained as hash-checked evidence and combined with the same 0.5 unique-distance association, 10-frame/five-consecutive support and conflict rules used for the 006 research hypotheses. On 007, the two-camera baseline gives 10 hypotheses, one multi-camera hypothesis, 398 usable hypothesis-frame points and 270 reference-near position pairs. The direct model gives 12 hypotheses, one multi-camera hypothesis, 480 usable points, two conflicts and 418 reference-near pairs. Hypotheses are not verified identities; only two of six cameras participate.

With the unchanged illustrative north/south rectangles, the published reference has one north-to-south candidate at frames 358 and 364. Neither the baseline nor direct hypotheses produce an uninterrupted or interrupted candidate under those rules. Thus extra position coverage does not recover this example event. This is evidence for further tracking/continuity work, not proof of an error rate or a claim about real store zones.

After the three commands above, run:

```sh
.venv/bin/python scripts/evaluate_site03_holdout_journeys.py
node scripts/compare_site03_holdout_events.js
```

The ignored experiment directory contains the inputs, hypotheses, per-frame coverage and event comparison.
