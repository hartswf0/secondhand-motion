# Cartoon Archive

Any shot in the [Moving Image Archive](https://www.movingimagearchive.com/) should be watchable as a
moving [Quick, Draw!](https://github.com/googlecreativelab/quickdraw-dataset) cartoon: the subject
redrawn in the identity of one real doodle, moving as the footage moves, on depth planes that slide
with the real camera.

Open `index.html` (or the GitHub Pages site) to start. Every page works from the file system.

## Start here

- **`PIPELINE.md`**: the 13 stages from archive shot to cartoon, with what each reads, writes and must pass.
- **`AGENTS.md`**: the prompt that hands one subject to an agent. Fill `{CATEGORY}` and `{WAVE}` from
  `data/subject_queue.json`. Critics are separate agents and see only the critic packet.
- **`index.html`**: where every subject stands, every page so far, and the tests on the full shot.

## Two lanes, and the join

| | Look lane | Motion lane | Join |
|---|---|---|---|
| Where | `batches/2026-10-20-selected-drawings/` | `shots/giraffe-walks-past/` | `tools/trace_keys.py`, `traced/` |
| What | image model draws 4 still keys per subject in the doodle's identity; fresh critics review | vector rig keyed over SAM silhouettes, in-betweened, 6 depth planes, measured camera | raster keys traced to strokes, split into what holds and what moves |
| Status | 10 subjects, 40 keys accepted as stills | 11 of 14 tests pass; playback review still open | recall ≥ 0.98 on all 40 keys; backgrounds are redrawn per key (fix upstream) |

## Rebuild

```sh
pip install numpy pillow scipy scikit-image markdown
data/quickdraw/fetch.sh                        # exact Quick, Draw! slices the shot scripts read
cd shots/giraffe-walks-past
PRM='{"leg_w":0,"seg":16,"wobble":3,"spots":0,"ossicones":true,"tail":true,"bend":5,"muzzle":7,"tail_len":34,"tuft":true}'
python3 inbetween.py pose_agent_v5.json "$PRM" drawn_frames_v5.json
python3 build_shot.py && python3 tests.py      # shot.json and tests.json rebuild byte-identical
cd ../..
python3 tools/trace_keys.py batches/2026-10-20-selected-drawings traced/traced_keys.json
python3 tools/build_pages.py                   # every page in pages/ and index.html
```

The browser stages (SAM 2.1, Grounding DINO, CLIP, the Quick, Draw! classifier, all through
transformers.js / onnxruntime-web) and the image-model keys were run interactively; their outputs
are committed. Their scripts are not yet in the repository.

## What has and has not happened

- No model has been trained. Agents proposed, tests and fresh critics judged, ledgers kept every
  attempt. That is search, and it is the data a learner would need later (`PIPELINE.md`, "Where
  learning comes in").
- Still-key approval is not motion approval. No shot has yet passed a playback review.

## Credits

See `ATTRIBUTION.md`. Footage: Moving Image Archive (rights as reported per source record).
Doodles: Quick, Draw! by Google Creative Lab and its contributors, CC BY 4.0.
