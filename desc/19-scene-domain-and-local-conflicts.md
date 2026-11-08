# Scene-domain review and local identity conflicts

2026-11-07. Corrects an overly pessimistic interpretation of outside-scene projections in document 18.

Visual inspection sampled camera1 frames 0,3,98,101 and camera2 109,120,140,154. Red outside-scene boxes correspond to people visible in the public corridor beyond the storefront, while green in-scene boxes cover the foreground store person. This supports the scene domain excluding external traffic; it does not prove every outside observation is correctly projected. Review images: data/processed/site02-outside-review/.

Do not expand scene bounds or force these points into the store solely to increase accepted observations. Preserve the detector output, lens-hull flag and scene-domain flag independently. Distinguish no-track output from tracks outside the chosen analysis domain; neither implies the store is empty.

scripts/review_site02_roi.py exports all original experimental rows with rejection reasons and complete 218-frame ledgers. Camera1: 219 candidate-domain observations, 216 candidate frames, 2 no-track frames, 2 candidate local IDs. Camera2: 144 candidate observations/frames, 74 no-track frames, 1 candidate local ID. Camera1 exclusions: 4 outside scene and 4 outside both lens hull and scene. Camera2 exclusions: 47 outside scene, spread over five other local IDs. None of these ID counts is a customer count.

The apparent second camera1 in-domain ID warrants a quality flag: ID1 has 212 observations spanning 0-217; ID9 has 7 observations spanning 191-198. Frames191-193 have simultaneous strongly nested boxes; frame195 visually shows one person with ID9. ID1 returns at199. This is qualitative evidence of duplicate/fragmented local tracking, not a validated same-person annotation. Strong containment can also occur with genuinely overlapping people, so no automatic merge or deletion is performed.

Derived overlap-conflicts.json records same-frame pairs with intersection/min(box area)>=0.9 for review only. It is a diagnostic heuristic, not a deduplication algorithm. All raw trajectories remain preserved.

Tradeoff: prioritize source-domain filtering and uncertainty flags rather than more detector threshold tuning. Before W06 accept no implicit one-ID-one-person assumption. Next native-camera projection comparison and synchronization evidence remain required; then evaluate local tracklet continuity using existing upstream implementations. Reference dataset has only one path, which is insufficient evidence of complete annotation coverage across the whole camera image.

Reproduce domain ledgers: .venv/bin/python scripts/review_site02_roi.py
All scope statements remain experimental: floor calibration, identity and business events are not independently validated.
