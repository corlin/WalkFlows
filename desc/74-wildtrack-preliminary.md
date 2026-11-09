# WILDTRACK preliminary independent-sample investigation

2026-11-09. This is a feasibility probe, not a benchmark or a production gate. The official [EPFL dataset page](https://www.epfl.ch/labs/cvlab/data/data-wildtrack/) provides synchronized images, camera calibration and ground-plane annotations. Direct and host-proxy HEAD requests for its ZIP both timed out during TLS setup. This says nothing definitive about availability. The dataset's permission and redistribution terms were not established by this probe.

## Sources and provenance

One annotation, one undistorted C1 frame, and C1 zero-distortion intrinsic and extrinsic files were obtained from a third-party [Hugging Face mirror](https://huggingface.co/datasets/disl/my_dataset) at revision 8a45bb947ca237921d5b873fe8f15f213730898e. This is not the official distribution; mirror provenance and equivalence to the original ZIP have not been independently verified. Data are not committed. SHA-256 hashes of the four inputs and pinned YOLO11s-pose weights are recorded in the ignored local data/processed/wildtrack-single-frame-probe.json. The corresponding exploratory script is data/processed/wildtrack-single-frame-probe.py and is also ignored; it is not yet an audited or versioned pipeline.

## Coordinate discrepancy

The mirror's dataset README and [MVDet dataset loader](https://raw.githubusercontent.com/hou-yz/MVDet/master/multiview_detector/datasets/Wildtrack.py) use X = -300 + 2.5 * (positionID % 480), Y = -900 + 2.5 * (positionID // 480), in centimeters. The dataset author's [toolkit example](https://raw.githubusercontent.com/Chavdarova/WILDTRACK-toolkit/master/intersecting_area.py) instead states a Y origin of -90 cm for its grid drawing example. These source statements are not interchangeable without verification.

Using the mirrored first frame's C1 calibration, 33 visible annotation boxes, and the projected annotated ground points, median distance to the corresponding box-bottom center was 5.89 pixels with Y origin -900 cm and 169.74 pixels with -90 cm. Means were 8.67 and 264.18 pixels respectively. This supports -900 cm for this sample and positionID interpretation, but is not independent physical calibration validation: box bottoms may have been derived from the same model or grid and are not manually labeled feet. Do not generalize this single-view comparison to the complete dataset.

## Fixed one-frame detector probe

With pinned YOLO11s-pose weights, confidence 0.1, image size 640, class person, one-to-one IoU assignment followed by a 0.5 IoU gate, and ankle confidence 0.5, this mirrored C1 frame had 33 visible reference boxes, 14 predicted boxes, 7 matched at the chosen gate, and 7 matches with a supported ankle. On the same seven matches, median ground error relative to the reference position was 0.234 m for detector box bottom and 1.015 m for the ankle-based foot estimate. No correction model was applied. These are conditional sample statistics, not recall or full-data benchmark estimates; the assignment algorithm, occlusion, projection, uncertain source and correlated annotation construction limit interpretation. The 26 unmatched visible references cannot be assigned meaningful false-negative causes from this sample alone.

## Next work

Confirm official data provenance and terms; audit the mirror hashes against an authorized original if available. Freeze a held-out frame selection, use multiple cameras and independent recordings when possible, and build a tested importer plus explicit one-to-one matching and coverage accounting. Examine pose, box, geometry and detection separately. Do not tune on this single exploratory frame or claim that its ranking generalizes to site03 or retail stores.


## Frozen follow-up sample plan

Before inspecting additional results, select C1 frames 00000000, 00000500, 00001000, 00001500 and 00001995 from the same pinned third-party revision; frame 00000000 is already exploratory, so the other four are the new observations. Use the same pinned weights, confidence 0.1, image size 640, IoU gate 0.5, ankle confidence 0.5 and -900 cm Y origin, with no threshold selection on these frames. Report per-frame visible references, detections, matches, pose support, and conditional box-bottom and ankle median errors; distinguish missing inputs and do not average frame medians as person-level evidence. One camera and five correlated time points cannot establish generalization, and the third-party mirror and unknown dataset terms remain explicit limitations.


## Frozen five-frame C1 results

The prescribed follow-up completed with the same pinned inputs and fixed parameters. Frame 0 was exploratory and the four subsequent frames were chosen before their results were observed. Each frame uses one-to-one assignment maximizing total IoU followed by the 0.5 gate; it is not guaranteed to maximize the number of above-gate matches. Distances are conditional on a supported ankle for the same matched detections:

| Frame | Visible references | Detections | Matches | Ankle-supported | Box median, m | Ankle median, m |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 33 | 14 | 7 | 7 | 0.234 | 1.015 |
| 500 | 20 | 6 | 5 | 5 | 0.246 | 0.833 |
| 1000 | 24 | 18 | 12 | 12 | 0.157 | 0.584 |
| 1500 | 21 | 9 | 7 | 7 | 0.140 | 0.698 |
| 1995 | 22 | 11 | 9 | 9 | 0.149 | 0.841 |

Per-frame ignored local reports are data/processed/wildtrack-probe-00000000.json through the other selected frame numbers; each lists exact input and weight SHA-256 hashes. The exploratory script is data/processed/wildtrack-five-frame-probe.py. It is not a versioned pipeline. The reference boxes, reference positions and camera model may share annotation or projection assumptions. One camera, five frames, selection by 2D IoU and no independent feet annotations preclude a general model-quality or tracking conclusion. These results motivate investigating point selection and visibility, not promoting a correction or changing product defaults.


## Annotation coupling confirmed

The dataset authors' [paper, appendix C](https://arxiv.org/html/1707.09299) states that annotators position a shared three-dimensional cylinder across views, with per-view rectangles generated by projecting candidate cylinders. Thus reference rectangles and reference ground positions are coupled by construction; the close reference-box-bottom reprojection is not independent confirmation of physical foot position. Matching detector boxes against these rectangles and then comparing box-bottom and ankle projection to the same ground reference can favor box geometry related to the annotation model. The five-frame table is useful for diagnosing compatibility with this particular annotation protocol, but it is not evidence that box bottoms locate actual feet better in real retail environments. Independent foot or ground-position evidence is needed to decide that question.
