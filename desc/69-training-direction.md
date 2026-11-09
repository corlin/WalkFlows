# Training direction and project scope update

2026-11-09: The user clarified that WalkFlows is intended as an open-source, non-commercial product and requested use of more of the public multiview-retail-tracking dataset for training and optimization. This supersedes the original MVP restriction against model training; it does not authorize new video collection or manual frame-by-frame labeling. There is currently no project LICENSE file, so this statement does not select specific legal terms for the repository. Data, model, framework and dependency licenses remain distinct.

The dataset publisher lists 81 runnable testcase scenarios, 45 with annotated floor tracks, plus unlabeled footage. The release is CC BY-NC 4.0. Its current documentation describes 2D pose side files and standard tracking exports as planned, not yet released. Floor-track reference points are not automatically per-camera detection boxes or pose-keypoint labels. Unlabeled footage can be considered for self-supervision or carefully qualified pseudo-labels, but model predictions must never be presented as independent ground truth. See the [dataset documentation](https://huggingface.co/datasets/prcvlabs/multiview-retail-tracking).

Next steps: inventory the pinned dataset and actual label schemas; separate training, validation and untouched testing by site or recording before fitting or model selection; define a measurable task and baseline appropriate to available labels; record data, model, configuration and artifact hashes; run controlled GPU experiments in the existing project environment; and evaluate position, association, coverage and downstream events separately. The previous 006 and site02 results influenced model selection, so they are not untouched test sets. Non-commercial intent does not by itself resolve every license or release question.

As of this update, no new model has been trained and no generalized performance improvement is claimed. The usable previous baseline and optional direct-pose experiment remain available.

## Pinned full-dataset inventory

The fixed revision `6cf0e1066653f7efe1d0aae5c49860b19ef9a6e5` contains 1,912 files totaling 4,641,571,868 bytes according to the repository API: 855 calibration files, 817 testcase files, 238 unlabeled files and two root files. There are 45 testcase `ground-truth.json` files and 677 MP4 files across the full repository. These are file counts, not independent people or training examples. The reproducible inventory and optional complete download are:

```sh
.venv/bin/python scripts/fetch_multiview_dataset.py
.venv/bin/python scripts/fetch_multiview_dataset.py --download
```

The downloader uses three workers, verifies each Git blob or LFS SHA-256 against the pinned revision, resumes incomplete transfers and records results under ignored local data. A complete download is not a trained model, and the downloaded files should not be used for supervised fitting until their actual label semantics and site-level splits are checked.

## Initial site-isolated partition

Before fitting, the pinned file inventory is partitioned by anonymized site: site01/02/03/04/05/08 for training, site06 for validation, and site07 for final testing. This yields 604/43/30 videos and 35/2/8 existing floor-reference files respectively; calibration and repository metadata are listed as shared resources, not training labels. The split includes unlabeled material, which is not supervised truth. It is an initial fixed partition, not proof that identities or recording sessions never overlap across sites. Site02/03 were previously explored and therefore are not held out. No site07 test label or frame should be used for model fitting, threshold selection, or repeated iterative tuning.

Run `.venv/bin/python scripts/create_training_splits.py` after creating the pinned inventory. The ignored `data/processed/multiview-inventory/site-splits.json` records every path and the inventory hash. Unknown or ambiguous site names fail closed. Successful partitioning does not confirm that any selected task has appropriate ground-truth labels or that a model has been trained.

## Scene geometry check before fitting

The first train and validation metadata checked are 045_site04_sitting_2 and 011_site06_standing; no site07 test data was inspected. Site04 has a nonidentity global transform: a 180-degree rotation about Z and a translation of (0.8, 1.27, 0). The upstream [scene reader](https://raw.githubusercontent.com/prcvlabs/multiview/7e334db96ca7ab685628365a2eaa2d5e8117eac3/multiview/multiview_cpp/src/perceive/scene/scene-description-info.cpp) composes this into each camera transform. Its [composition operator](https://raw.githubusercontent.com/prcvlabs/multiview/7e334db96ca7ab685628365a2eaa2d5e8117eac3/multiview/multiview_cpp/src/perceive/geometry/euclidean-transform.hpp) applies the scene transform after the camera transform. Omitting this step would substantially move camera centers and corrupt projected training candidates. Site06 also lists Y bounds in descending order, whereas the reference grid spans ascending coordinates.

`walkflows/scene_transforms.py` implements the source-aligned composition and explicit bounds normalization; tests cover identity, noncommuting rotations, scale and malformed input. `.venv/bin/python scripts/audit_training_scenes.py` verifies the selected scene, manifest and reference files against the pinned inventory and checks their coordinate bounds. This is a numerical contract check, not independent physical calibration validation or a trained model.
