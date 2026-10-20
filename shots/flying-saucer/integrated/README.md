# Flying saucer borrows a NASA CGI aeroshell attitude

53 frames at 24 fps, eight integrated keys. Open `index.html` for cartoon, source, and synchronized comparison. This transfers a banked attitude from NASA CGI; it is not physical UFO footage. The raw decoded 416×240 aspect is retained at520×300. No training ran.

Download the clip named by `../source.json` → `video_url`, then rebuild from the repository root:

```sh
python shots/flying-saucer/build_integrated.py --source /path/to/flying-saucer.mp4 --mask-cache /path/to/sam-snapshot
python shots/flying-saucer/build_integrated_page.py
```

The cache contains `track.json` and `clip.json` from the pinned `wave2-track/flying-saucer` snapshot. The builder verifies the source SHA-256, renders in a unique temporary directory, validates complete MP4 decoding and atomically installs each movie. Python dependencies: OpenCV, NumPy, SciPy, Pillow, CairoSVG and scikit-image; ffmpeg with libx264 must be on PATH.

Original native stroke indices remain the same across every key. Filled rim/dome overlap is measured against SAM and is not predicted SAM confidence. Hidden lower contour geometry is unverified where cropped; recognition and actual normal-speed playback approval are pending. Raw reviews and rejected attempts remain alongside the current review copy.

Final review is v3, after three independent still-critique rounds. Source framing/pose passes; same-doodle identity does not: the rim/body marks migrated onto the dome. This known gap is displayed beside the player. Actual normal-speed playback and recognition remain unrun; no motion approval or training eligibility. Rejected v1/v2 artifacts and all three raw critiques are preserved. Seven hash-linked ledger entries include append-only verdict/reference normalization.
