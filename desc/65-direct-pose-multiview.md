# Direct pose: multiview and region-event comparison

Direct YOLO11s-pose tracking was also run for C0001055. An isolated mixed experiment replaces the two main cameras' baseline observations with independently detected/tracked small-pose observations, keeps the other four cameras' original observations, and recomputes proximity-based cross-camera proposals and research hypotheses. It applies the existing ankle, projection, duplicate exclusion, unique 0.5-distance association, minimum 10-frame/five-consecutive support and 0.5 fusion-conflict rules. No reference positions are used to construct the proposals. Every chosen source observation is conserved exactly once. Inputs and generated hypotheses are hash recorded.

At the same 0.5 scene-unit reference proximity gate, the baseline gives 353 matched pairs, 28 unmatched valid model points, 697 unmatched reference points and one conflict; this mixed variant gives 435, 22, 615 and four, respectively. It uses 681 source observations and produces eight hypotheses, one multi-camera, versus the baseline nine hypotheses, two multi-camera. These are sample counts and experimental hypothesis groupings, not people counts or precision/recall. Reference coverage and physical localization remain unverified; unmatched observations cannot be treated as proven errors.

For the arbitrary north/south example in document 53, the baseline has zero uninterrupted model transitions. The mixed variant yields one north-to-south candidate with exit confirmation at frame 100 and arrival at frame 114. The published reference candidate confirms exit at 99 and arrival at 114. The experimental candidate combines C0001055 local ID 3 and C0001056 local ID 2; its per-frame one-to-one spatial match is reference ID 0 at every frame 90?114. This is a useful reproducible example, not independent identity validation, customer-count accuracy, or evidence that the example rectangles correspond to actual business zones. The same data influenced the choice of model and example; another scene and representative region definitions are needed before generalizing or changing defaults.

Reproduce after the standard pipeline and optional weight fetch:

```sh
.venv/bin/python scripts/probe_site03_pose_direct.py --camera C0001055_v4
.venv/bin/python scripts/probe_site03_pose_direct.py --camera C0001056_v2
.venv/bin/python scripts/evaluate_site03_direct_pose_journeys.py
node scripts/compare_site03_direct_pose_events.js
```

The ignored `data/processed/site03-direct-pose-journeys/` directory contains candidate support, hypotheses, frame-level matching and event evidence. The optional comparison does not alter the default review bundle or strict quality gates.
