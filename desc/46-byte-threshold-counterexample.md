# ByteTrack association threshold counterexample

The fixed ByteTrack baseline uses match_thresh 0.8. A two-camera experiment changed only this value to 0.95, keeping video, model, GPU, detector threshold, image size and tracker configuration otherwise the same. The exact config and output hashes are recorded in `data/processed/site03-byte095-experiment/`. Reproduce with:

```bash
.venv/bin/python scripts/probe_site03_byte095.py --camera C0001055_v4 --camera C0001056_v2
.venv/bin/python scripts/compare_site03_byte095.py
.venv/bin/python scripts/compare_site03_byte095_reference.py
```

In C0001056, mutually unique same-frame box correspondence maps baseline IDs 9 (63 frames) and 14 (220 frames) to relaxed ID 5. This is consistent with reconnecting that fragmented candidate. The relaxed run yields five local IDs rather than six, but fewer IDs do not establish better identity tracking. C0001055 IDs 4 and 10 remain separate.

The same relaxed C0001056 ID 3 also maps to baseline ID 4 at frame 67 and baseline ID 1 at frames 92?95. The former baseline observation has reference proximity proxy ID 1; the latter four have proxy ID 0. Video inspection of the boxed detections shows a white-shirt person at frame 67 and a red-shirt person at frames 92?95 bearing relaxed ID 3. This is direct visual evidence of a likely false identity merge, not merely a proxy mismatch. The proxy uses baseline pose-qualified floor points and mutually unique IoU >= 0.8 box correspondence; it is incomplete, uses related evidence, and is not an accuracy estimate.

Therefore the relaxed threshold is rejected as a default despite repairing one candidate break. The current ByteTrack baseline remains in place; no model weights, reference labels, or source videos were changed. A viable next approach must discriminate competing people with additional evidence and explicitly preserve uncertain connections, then validate on held-out sequences and report both fragmentation and false merge risk.
