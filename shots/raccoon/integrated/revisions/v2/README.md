# Raccoon at the waterline

Assembled review copy: 67 frames at 24 fps, eight integrated keys, synchronized source comparison. Open `index.html` or play `comparison.mp4`.

Original Quick, Draw! raccoon `5643141870780416`, fourteen original strokes, CC BY 4.0. The crouch uses one keyed topology. A single bank drawing receives source-derived camera translation; water occludes the unobserved feet/tail. Frame poses are authored against the source, not estimated by SAM.

To rebuild, download the video URL from `../source.json` to a local file outside the repo, then run from the repository root:

```sh
python shots/raccoon/build_integrated.py --source /path/to/raccoon.mp4
python shots/raccoon/build_integrated_page.py
```

Requires Python with OpenCV, NumPy, SciPy, Pillow, CairoSVG and ffmpeg on PATH. The renderer verifies the downloaded file's SHA256 against `../source.json` and uses an isolated temporary render folder.

`revisions/v1/` preserves the first assembled draft. `review-v1.json` and `review-v2.json` retain independent still reviews. Successful decoding does not establish motion quality; normal-speed playback approval, recognition classifier and numeric source mask fit are pending. No training ran.
