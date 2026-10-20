# Storm surge at the building

A complete **review assembly**, not a released or training-approved cartoon: 74 frames at 24 fps, 3.083 seconds, eight source-event keys. `index.html` opens the cartoon, a synchronized source/cartoon comparison, and the source excerpt. The actual event is storm water against a building; no rotating cyclone is visible.

The original Quick, Draw! hurricane drawing is key **4791481996935168**, all seven strokes. Stroke order and point correspondence persist through every key and dense frame. `shot.json` stores dense casts in a 320 × 240 viewbox rendered at 480 × 360. The building is drawn once by the agent and moved by source-derived roof/eave template translation. The near water edge occludes its lower facade. Crest changes are manually keyed against source samples; lower-water optical flow only supplies bounded texture drift and does not track physical water particles.

Source: *Shock Troops of Disaster: The Story of the New England Hurricane* (1938), clip `83e2cd5e-159b-57e5-b374-72233abf89ce`, clip-relative 31.1311311311–34.2008675342 seconds. Source SHA256 is verified before rendering. Archive rights were not provided and remain unverified. Quick, Draw! is credited under CC BY 4.0.

## Reproduce

From the repository root, with Python packages `numpy`, `scipy`, `opencv-python`, `Pillow`, `cairosvg`, `scikit-image`, and `ffmpeg`/`ffprobe` installed:

```sh
python shots/hurricane/build_integrated.py --source /path/to/hurricane.mp4 --mask-cache /path/to/hurricane-cache
python shots/hurricane/audit_integrated.py
python shots/hurricane/build_integrated_page.py
```

The source file is the complete archive clip. The cache supplies `track.json` and `clip.json`, pinned to tracking commit `2dc19de1e1d56b643cb8f0c5c4d7ac9823e4bcb8`. Default local cache paths are conveniences; neither is required when explicit flags are used. Rendering uses an isolated temporary directory, fully decodes temporary movies, then atomically replaces each final movie. A rebuild resets review metadata to pending; saved reviews apply only to the inspected candidate.

## Limits

- All three current movies fully decode, and every frame has source time and seven corresponding native vector paths. Decode is not playback approval.
- The unchanged default `tools/trace_keys.py` measured minimum raster recall **0.9514354478**, with every significant ink piece retained. The 0.98 recall bar **fails**; native vector correspondence does not bypass that gate.
- SAM2.1 ran upstream, but its final water mask switches to the building. Estimated model IoU is not measured cartoon fit. Persistent water-instance tracking and M3 fit are not established.
- No classifier or normal-speed independent playback approval ran. Zero planted-foot intervals does not pass the four-interval foot-slide gate. No physical water-particle correspondence or recovered 3D geometry is claimed.
- No training ran. Agent drawing and critique here are search and repair, not trained reinforcement learning.

Blind reviews are preserved unedited in `review-v1.json`, `review-v2.json`, and `review-v3.json` when available. Rejected drawings and complete movies remain in `revisions/v1/` and `revisions/v2/`. Every proposal and verdict is appended to `../ledger.jsonl`; failed gates keep candidates rejected even if a still-image critic approves the drawing.

Final blind round 3 preserves original identity and building framing but rejects source-event fidelity: **continuing foreground surge is underrepresented in later keys**. The three-round limit is reached; this gap remains openly flagged beside the player. All five ledger entries verify; integrated revisions v1, v2 and v3 are rejected, with no accepted or train-eligible revision.
