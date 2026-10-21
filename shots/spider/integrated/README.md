# Spider across its web

73 frames at 24 fps, eight source-paired keys. The source interval is clip-relative 6.000–9.000 seconds from **Spider Engineers** (1956). See `source.json` for archive ids, original film interval, raw SHA-256 and reported rights.

Open `index.html` offline. The three tabs share one playhead: cartoon, source beside cartoon, and source excerpt. Editable native strokes and each decoded source frame index are in `shot.json`; reasons for the eight keys are in its exposure sheet. `correspondence.json` maps the original open body outline and eight unequal leg strokes. No image model generated these vectors.

Body position, attitude and eight reach endpoints were observed on exact raw keyframes. The eighth reach is partly hidden and constrained, not claimed as a tracked contact. `camera.json` stores background-only Lucas–Kanade flow with the spider region excluded. Macro stems and web are held geometry; the background factor 0.5 is authored, not depth calibrated. Geometry extends beyond frame so camera motion cannot expose a finite plate edge.

The fresh independent critic inspected all eight source/key pairs and the real design. Source framing/pose and drawing identity pass on those stills. The critic did not view actual normal-speed playback; motion remains unapproved. The filled rig/SAM score **fails**: mean 0.2535, minimum 0.1754 against bars 0.65/0.45. The mask broadly captures body and legs, with thin tips and some web contamination. A still-pose pass does not overturn the metric. No verified planted intervals were established, so that gate fails its minimum of four. Classifier unrun. Character trace recall and all pieces retained are 1.0 for all eight keys. This is a review copy, not an accepted training pair. No training ran.

## Rebuild

The observed inputs (`camera.json`, the eight anchors in the builder, and audited SAM evidence) accompany the code. To rerender the exact source-keyed candidate:

```sh
python shots/spider/build_integrated.py --source /path/to/a975d12c-ffcb-58f5-9c3f-4abf577b102e.mp4 --mask-cache /path/to/spider-snapshot
python shots/spider/record_integrated.py
python shots/spider/build_integrated_page.py
```

Omit `--mask-cache` to use the committed `sam/clip.json` and `sam/track.json`. The source SHA must match the reviewed raw clip. Rendering uses a unique temporary directory, finishes each encoder, decodes and counts all frames, then atomically installs its movie. `video-validation.json` records final bytes. Rebuilding exact same pixels preserves the still verdict; changed artwork requires a new independent review and ledger revision.

Quick, Draw! key **5924220649340928**, Quick, Draw! contributors / Google Creative Lab, CC BY 4.0. All nine strokes retain original point correspondence. Background and web drawn by agent from the archive source.
