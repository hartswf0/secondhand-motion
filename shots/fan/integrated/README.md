# Fan assembly review copy

Open `index.html` to watch the cartoon, the synchronized comparison, or the source. Six integrated keys and 75 frames at 24 fps. Normal-speed motion approval remains pending; no training ran.

To rebuild, download the clip named by `../source.json` → `video_url`, then run from the repository root:

```bash
python shots/fan/build_integrated.py --source /path/to/fan.mp4
python shots/fan/build_integrated_page.py
```

The renderer verifies the source SHA-256. It requires Python with OpenCV, NumPy, Pillow and CairoSVG, plus ffmpeg with libx264. Doodle credit and source rights are recorded in the player and timeline.
