# Camera coverage and public-data limits

The fixed site03 baseline (`yolo11n.pt`, ByteTrack, confidence 0.10, image size 640) decodes 400 frames per camera. In `C0001025_v1`, tracker output contains untracked boxes in seven frames and zero tracked observations; in `C0001053_v5`, it contains untracked boxes in two frames and zero tracked observations. This is tracker output, not a complete record of raw detector predictions. Sampled frames 0, 60, 120, 180, 240 and 300 show mainly displays, with possible partial people at the image edges. These samples alone cannot establish that all 400 frames are empty.

A controlled full-clip probe using the same pinned model, `--conf 0.03 --imgsz 960`, produced 164 observations in two local track IDs for `C0001025_v1`, and zero observations for `C0001053_v5`. The first track covers frames 0?102 and the second frames 339?399; their boxes occupy approximately the same image region. Inspecting frame 0 shows the first box surrounds a lamp and display, not a visible person. This is a concrete false positive for that frame; it does not label every observation or prove absence of missed people. More tracking boxes alone are not evidence of an improvement. The production research baseline is unchanged.

Reproduce after preparing the fixed data and model:

```sh
.venv/bin/python scripts/probe_site03.py --camera C0001025_v1 --camera C0001053_v5 --conf 0.03 --imgsz 960 --output data/processed/site03-camera-coverage-review/conf003-size960
```

The output contract records source and weight hashes, tracker configuration and library versions; cache reuse checks both CSV hashes. The probe changes confidence and image size together and therefore does not attribute the difference to either setting separately. No new labels were created.

The pinned `site03_scene03` calibration has empty `background-image` and `cad-model-key` fields, so the page's coordinate grid is not a real store plan. The [dataset documentation](https://huggingface.co/datasets/prcvlabs/multiview-retail-tracking) lists CAD files for the wider dataset, but this scene does not reference one. It also reports that anonymization reduced recall for its own HyperPose pipeline on this scenario, and says original-video pose files are planned for publication. Those reported results concern a different pipeline and are not a measured effect on WalkFlows or a reason to remove anonymization. Continue using the privacy-preserving source and treat pose availability as unconfirmed until actual files and licensing are verified.
