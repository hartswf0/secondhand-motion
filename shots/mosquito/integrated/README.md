# Mosquito on skin

Assembled review copy: 121 frames at 24 fps, eight integrated keys, synchronized comparison. Open `index.html` or play `comparison.mp4`. Normal-speed playback has not been approved. No training ran.

The character uses the same real Quick, Draw! key `6165377341980672` and all eight original strokes. Its native left-facing orientation matches the footage; the earlier isolated preview was mirrored. Skin and hair context are drawn once against the source. The source shows a mosquito remaining on skin with abdomen pitch changes; no takeoff, flight or grooming cycle is invented.

Download the video named by `../source.json` → `video_url`, then from the repository root:

```sh
python shots/mosquito/build_integrated.py --source /path/to/mosquito.mp4
python shots/mosquito/build_integrated_page.py
```

Dependencies: Python, OpenCV, NumPy, SciPy, Pillow, CairoSVG, scikit-image; ffmpeg with libx264. The renderer checks source SHA-256, uses an isolated temporary folder and validates complete temporary movies before atomic installation.

`source-track.json` / `source-clip.json` are upstream SAM 2.1 source observations, retained with branch/commit/hash provenance in `shot.json`. Predicted SAM confidence is not drawing fit. The filled drawing versus nearest 12 fps source masks does not meet the source-fit bar. Recognition and independent contact tests remain unapproved.

Three independent still reviews were completed. The third accepts the native doodle identity but rejects late registration: the source shifts upward-left while the current insect camera coordinates remain nearly held. This remains the one primary repair; the player states it prominently. Rejected v1/v2 integrated revisions and all unedited reviews are retained. Stage durations were not separately instrumented.
