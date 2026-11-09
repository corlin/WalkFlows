# Collaboration handoff and current direction

Updated 2026-11-09. This is a handoff index, not a replacement for product requirements in desc/01-05 or later user-approved scope updates. Historical findings and their limits remain in their numbered documents.

## Authoritative workspace and constraints

- Develop in WSL2 Ubuntu20.04 as user corlin, at /home/corlin/WalkFlows. Never directly use root. Windows D:/homedev/WalkFlows is not the authoritative development checkout; do not blindly overwrite either copy.
- Use the existing /home/corlin/WalkFlows/.venv. Do not create additional project virtual environments. Work generally under corlin home; /opt and /data are permitted when appropriate.
- The main branch is main and the remote is https://github.com/corlin/WalkFlows. Verify important work, commit and synchronize it to remote main. Inspect worktree changes and the remote head first; preserve others' uncommitted work and do not force-push.
- The Windows host proxy listens on port 7890; discover the current WSL gateway using ip route show default. Network transfers are unreliable: verify, resume, and inspect process status before restarting.
- The user intends an open-source, non-commercial project; no specific project license has been selected. Dataset, model and dependency rights are separate and must be checked individually.

## Current behavior and limits

The project has a six-camera site03 research review with trajectories, movement directions, region and route candidates, heatmaps and evidence; see desc/38-71 and the project README. These are research demonstrations, not validated cross-camera identity, deduplicated customer counts or production business metrics. Physical ground-plane accuracy, cross-camera identity, reliable events and end-to-end acceptance remain incomplete.

Pinned dataset revision: 6cf0e1066653f7efe1d0aae5c49860b19ef9a6e5; inventory: 1,912 files. Site split: site01/02/03/04/05/08 train, site06 validation, site07 reserved for final independent testing. Do not use site07 to fit, select models or repeatedly tune. Unlabeled video is not supervised truth; a site split does not prove identity disjointness.

Of 35 training scenarios with floor tracks, 34 exported. Scenario 001 is excluded because its 25 fps video conflicts with the 15 fps reference duration and its camera version mapping is unresolved. An explicit audited 499/500-frame boundary correction applies only to scenario 004; do not generalize it. Training uses unique spatial-proximity proxy pairs; these do not establish camera visibility or identity. With 7,691 train and 679 validation pairs, fixed training increased validation median distance from 0.2415 to 0.2614 scene units. The model is not promoted. The validation pairs come from just six scenario-scoped reference tracks; frames are correlated. See desc/72.

An exploratory leave-one-training-site-out run used the same fixed 7-32-2 residual network, 100 epochs and Adam. Baseline to corrected medians: site01 0.1136 to 0.1054; site02 0.1063 to 0.1250; site03 0.1478 to 0.1377; site04 0.1420 to 0.1648; site05 0.0925 to 0.0912. Site05 mean worsened despite its median. These correlated weak proxies do not establish generalization or business benefit. The prototype script and report exist only in ignored data/processed/weak-localizer-leave-site-out.py and .json; they are not yet a versioned, independently reproducible pipeline. Audit completeness, provenance and tests before relying on or versioning them.

## Additional datasets

- [MMPTRACK](https://github.com/iccv2021-mmp/iccv2021-mmp.github.io/blob/main/subpage/dataset.html): simulated retail and other indoor settings, camera boxes and identity, footpoints and calibration. Research use only; official access requires a signed agreement and email request. Do not sign or email on the user's behalf.
- [WILDTRACK](https://www.epfl.ch/labs/cvlab/data/data-wildtrack/): seven real overlapping outdoor views, synchronized frames, calibration, ground positions and boxes; 400 annotated frames at 2 fps. Useful for an independent localization comparison, but not a retail scene. Verify usage and redistribution terms. A direct HEAD of the official ZIP hit an SSL timeout on 2026-11-09; this does not establish that the resource is unavailable. Check proxy and official source.
- [EPFL multi-camera pedestrian videos](https://www.epfl.ch/labs/cvlab/data/data-pom-index-php/) and [MultiviewX](https://github.com/hou-yz/MultiviewX) provide additional calibration, multiview and synthetic data. Verify terms and annotation coverage per sequence.
- [RetailAction](https://openaccess.thecvf.com/content/ICCV2025W/RetailVision/papers/Mazzini_RetailAction_Dataset_for_Multi-View_Spatio-Temporal_Localization_of_Human-Object_Interactions_in_ICCVW_2025_paper.pdf) focuses on retail human-object interactions; check its separate agreement and do not treat actions as complete person trajectories.

## Coordination across tools

Inspect the worktree, this document, relevant desc files and live processes before taking a task. Independent research or verification may run in parallel when it does not write the same files. Coordinate work touching the same code, GPU, download target or data/processed cache to avoid overwrites, duplicate downloads and invalid provenance. A process is running only if its live PID and state confirm it; do not restart solely from this historical note. A full-dataset downloader was started as .venv/bin/python scripts/fetch_multiview_dataset.py --download with three network workers; the user cares about background process count, so inspect actual status before resuming.

Record input revisions, parameters, splits, output paths, verification, failures and limits. Models and datasets normally remain in Git-ignored data; do not commit large artifacts. Freeze experimental decisions and retain an independent test. At handoff verify the worktree, documentation and actual process state; commit important milestones to main and check remote alignment.

## Next actions

1. Monitor the existing full-data transfer and verify checksums; avoid duplicate downloaders.
2. Check official WILDTRACK access, usage terms and annotation coordinate conventions; build a traceable independent comparison without mixing it into the reserved test split.
3. Audit the leave-site-out prototype and provenance. Plan comparisons that avoid repeatedly tuning against one validation site and report site- and track-level support.
4. Continue toward real, verified localization, cross-camera identity, events and the complete user flow; weak-proxy regression alone does not complete the project.


## WILDTRACK preliminary probe

See [74-wildtrack-preliminary.md](74-wildtrack-preliminary.md) for the third-party mirror revision, source-hash caveat, a Y-origin discrepancy, and a single-frame conditional detector/foot comparison. It is exploratory only, not an official benchmark. Dataset usage and redistribution conditions remain unverified.


## Dataset download completion

The pinned multiview-retail-tracking download completed on 2026-11-09: download-report.json records status complete, 1,910 previously verified files, 2 downloaded files, and no failures for this final pass. All 1,912 manifest entries were verified by the downloader. The exact report and data are local and ignored by Git. Completion of download is not equivalent to using every file in training: unlabeled media and the held-out test split retain their separate roles.


## Unlabeled-data feasibility

See [75-unlabeled-multiview-pilot.md](75-unlabeled-multiview-pilot.md) for a fixed 46-frame, two-camera train-site probe. Only two sampled frames produced cross-view unique proximity candidates; these are not verified identities. This single sparse segment does not represent all unlabeled data, and the ignored exploration script is not a production pipeline.
