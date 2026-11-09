# Weakly supervised position-correction pilot

This is an initial experiment, not the requested full-data training or a production model. Existing YOLO11s-pose observations are projected using the pinned per-scene calibration, and paired to published floor positions only when the spatial candidate is unique in both directions within 0.5 scene units. Those pairs are weak proxies: floor annotations do not establish camera visibility or per-camera identity, unmatched observations are not negative labels, and the distance gate selects already-near samples. Test-site data is explicitly rejected by the exporter.

The first GPU pilot used site02/03 training scenarios 002, 006 and 007, with site06 scenario 011 for validation. A 7-input, 32-hidden-unit residual network trained for 100 fixed epochs on 1,527 weak pairs and was evaluated on 521 validation pairs. The overall validation median distance changed from 0.2051 to 0.1787 scene units and mean from 0.2090 to 0.1994, but 235 samples improved while 286 worsened. By camera, C0001074 median changed 0.1269 to 0.1067 (116/169 improved), C0001086 changed 0.3226 to 0.2579 (98/98 improved), and C0001091 changed 0.1269 to 0.1445 (only 21/254 improved). Neighboring frames are strongly correlated.

Because one camera regresses and labels are selected proximity proxies, the model is not promoted or used in the review. The held-out site07 test set was not read. Two initial site04 sitting scenarios yielded zero weak pairs; their empty support was retained instead of manufacturing labels. Further work must expand training scenes, inspect visibility and matching bias, validate on distinct recordings and only then consider a final independent test.

Reproduce after the pinned full-dataset inventory, site split, required files and optional weights are ready:

```sh
.venv/bin/python scripts/export_weak_position_labels.py --scenario 002_site02_gaze
.venv/bin/python scripts/export_weak_position_labels.py --scenario 006_site03_tracks
.venv/bin/python scripts/export_weak_position_labels.py --scenario 007_site03_sparse_tracks
.venv/bin/python scripts/export_weak_position_labels.py --scenario 011_site06_standing
.venv/bin/python scripts/train_weak_localizer.py
```

Ignored artifacts under `data/processed/weak-position-labels/` and `data/processed/weak-localizer-pilot/` contain provenance, counts, per-frame weak pairs, model, and per-camera validation evidence. Repeated training with the same setup produced the same model and prediction hashes locally; this is not a guarantee across hardware or library versions.


## Expanded experiment

A subsequent fixed 100-epoch run used 4,191 weak pairs from 23 contributing training scenarios across sites 02, 03 and 04. Thirty-two of the 35 designated training scenarios completed export; nine of those produced no weak pairs, and scenarios 001, 004 and 010 failed export and were excluded. Validation used 679 weak pairs from two site06 scenarios. The median distance increased from 0.2415 to 0.2560 scene units and the mean from 0.2212 to 0.2341; 123 pairs improved and 556 worsened. Both validation scenarios regressed in median distance. This experiment does not support deploying the model or claiming that the expanded training improves localization.

The proximity-based pair selection, correlated frames and lack of verified camera visibility limit the conclusions. Site07 remains untouched for independent testing. The export failures require separate investigation rather than treating missing scenarios as successfully trained. Reproduce, once all required inputs are available, with `.venv/bin/python scripts/export_train_split.py`, the validation exports for scenarios 011 and 044, and `.venv/bin/python scripts/train_weak_localizer.py --expanded`. The ignored `data/processed/weak-localizer-expanded/report.json` records exact inputs, exclusions, hashes and per-camera results.


## Follow-up export corrections

The published scenario name `010_site05` has no suffix; the exporter now accepts that inventory form. Its one camera produced 793 weak pairs in the local run. For `004_site01_clutter`, the declared reference frame count is 499 but five annotation points have index 499; both verified videos decode to 500 frames at 15 fps. The exporter explicitly recognizes only this audited case as an inclusive boundary, extends the processed extent to 500, and records the original count and policy in each cache. This is a documented interpretation of inconsistent source metadata, not an independent verification of all annotation timestamps. The source scene omits `global-transformation`; the upstream scene loader defaults that missing field to the identity transform, so the exporter does the same.

With these corrections the two cameras of 004 produced 1,634 and 1,073 weak pairs locally. These counts do not establish identity or visibility. Scenario 001 remains excluded: its 25 fps videos conflict with the reference's 15 fps frame duration and its reference boundary also disagrees. A fresh batch and evaluation are required before comparing a model trained with the added pairs to the earlier experiment.
