# Tornado beyond the street

The current source-paired assembly lives in `integrated/index.html`. It contains six deliberate source keys and 73 dense frames at 24 fps, with cartoon, original excerpt and side-by-side video views. The earlier isolated key experiment remains under `keys/`.

The original Quick, Draw! tornado, key `6522189199179776`, keeps its three strokes and original point counts. Six observed contour/camera anchors vary width, crop, sway and placement. The source does not establish a spin cycle or exposed ground contact; neither is invented. A street, trees, cars and utility wires were drawn once from the source and registered with manually observed camera landmarks. Foreground fills hide the lower column.

The SAM 2.1 result is not a reliable tornado silhouette: masks switch between sky and foreground tree, despite high model estimates. Pinned track/clip JSON, hashes, branch/commit and an audited overlay are in `integrated/sam/`; no mask-fit pass is claimed. A numerically unstable optical-flow camera estimate was rejected in favor of manual observations.

Rebuild from the repository root (Python requires OpenCV, NumPy, SciPy, Pillow and CairoSVG; FFmpeg/FFprobe must be installed):

```sh
python shots/tornado/build_integrated.py --source /path/to/original/tornado.mp4
python shots/tornado/build_integrated_page.py
```

The source hash must match `source.json`. The default mask cache is the committed `integrated/sam/` JSON/audit snapshot. To regenerate the mask audit from the original pinned cache, add `--mask-cache /path/to/cache` containing `clip.json`, `track.json` and `frames/fNNN.jpg`. Video renders use a temporary workspace, wait for complete writers, decode every output fully and check actual frame counts before atomic replacement.

Character keys are exported separately and traced with `tools/trace_keys.py`. Raw independent still reviews and rejected assembly versions are retained; every reviewed proposal/repair is appended through `loop.py` to `ledger.jsonl`. The player displays the current review limitation next to the video. Still inspection does not approve motion. Recognition and normal-speed playback remain unrun. No training ran; this shot is not train-eligible.

Source: Moving Image Archive, *Tornado*, clip `b615f6f9-22b3-571b-bbb6-0739a4f7cf1d`, clip-relative 0.2335666667–3.2699333333 seconds (film-relative 851.3835666667–854.4199333333 seconds). Reported archive rights are unavailable/unverified. Quick, Draw!: contributors / Google Creative Lab, CC BY 4.0. Drawing, repairs and set geometry by agent. Stage timings were not independently recorded.
