# Rain over the demonstration road

Review candidate: 105 frames at 24 fps, eight source-paired keys, 4.375 seconds.
Retained source: *Knights on the Highway* (1938), clip-relative 34.4344344344–38.8054721388 seconds. Source rights remain unverified in the supplied manifest.

The final independent still review does **not** meet the bar. Framing, original nine-stroke QuickDraw identity, and sampled buildup read clearly. Late water response remains too isolated and center-weighted: road-wide wash and rail-side splash crests need further work. Three bounded review rounds are recorded; the first two complete assemblies remain in `revisions/v1/` and `revisions/v2/`.

Normal-speed source/cartoon playback has not been independently viewed or approved. A complete decode is a file-integrity check. No classifier ran, no training ran, and this candidate is not release- or training-approved.

## Motion evidence

One held studio/road plate follows the actual camera framing. All nine native doodle strokes retain point order and local shape; their falling phase is authored at 112 source-space pixels per second, not an estimated fall speed. Eight separated character exports are traced with minimum ink recall 1.0 and parts kept 1.0.

1,243 positive local luminance-change events supply source times and road positions. A five-frame source-energy envelope controls an authored mapping to ripple visibility and lifespan. The added rings and tiny crowns are illustrative. No individual raindrop or splash identity is established. The broad SAM2.1 puddle/scene mask is not valid individual-drop ground truth; model confidence is not a quality measurement. The JSON snapshots include the exact upstream cache commit and content hash.

## Rebuild

From the repository root, with Python, NumPy, OpenCV, Pillow, CairoSVG, scikit-image, SciPy, and ffmpeg available:

```sh
python shots/rain/build_integrated.py --source /path/to/rain.mp4 --mask-cache /path/to/rain-cache
python shots/rain/build_integrated_page.py
```

The source hash must match `../source.json`. The cache must contain `clip.json` and `track.json`. Rendering uses a unique temporary directory; each movie is installed atomically only after a complete ffmpeg decode. The builder regenerates the trace. Rebuilding creates a new pending-review artifact; it does not constitute renewed independent approval. Review metadata must be reconciled before publication. `../record_integrated.py` appends recorded reviews without rewriting prior ledger history.

The native scene lives in `../build_integrated.py`; full-scene and separated character SVG keys remain editable. The source photographs, synchronized comparison, event observations, raw reviews, and pinned mask provenance are beside this file.
