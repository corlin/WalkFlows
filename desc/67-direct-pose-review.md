# Direct-pose research review

When the optional direct-pose experiment and its mixed hypotheses are present and pass provenance checks, the site03 page offers a fourth analysis source: direct-pose experiment. Selecting it updates the analysis track choices, plane trajectories, heatmaps, region candidates, transitions and funnel. Its export uses a distinct `experimental_direct_pose_not_validated_customer_counts` scope and records the hypothesis SHA-256.

The display explicitly states that camera-local video boxes, local-observation quality rows and the fixed model-versus-reference comparison remain based on the original baseline. Direct-pose hypothesis member IDs must not be confused with those baseline local box IDs. No experimental result is used as a verified identity or customer count.

The builder loads optional data only when the experiment report, hypotheses, baseline hash, reference, scene, per-camera input hashes, weights, video, sensor and producing scripts match. Missing or stale optional artifacts are omitted rather than silently displayed. To add the experiment, execute the commands in document 65, then run `.venv/bin/python -m walkflows prepare --cross-scene`; the normal preparation does not download the optional model or start its GPU experiment. No extra environment is needed.

Tests check source-specific export scope and reject missing provenance, and loader tests check missing and changed artifacts. Browser verification selected the direct-pose source and displayed eight hypotheses, 457 valid samples and four conflicts without changing the user's saved layout. These are research counts, not people.
