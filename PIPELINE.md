# Pipeline: archive shot → doodle cartoon

One shot is one folder, `shots/<category>/`, and one state file, `shot.json`. Every stage reads
files from that folder and writes new files to it; every page is a view of those files. Stages are
numbered so a ledger line can say where a repair went back to.

Two lanes have been tried, and the pipeline joins them:

- **Look lane** (`batches/2026-10-20-selected-drawings`): an image model draws four strong still keys
  per subject in the doodle's identity, reviewed by fresh critics. Good drawing; no motion; the
  background is redrawn on every key.
- **Motion lane** (`shots/giraffe-walks-past`): a vector rig keyed by the agent over SAM
  silhouettes, in-betweened with planted feet, laid out on six depth planes under the measured
  camera. Real motion and measurable tests; the drawing is weaker.
- **The join** is stage 5: trace look-lane keys into strokes (`tools/trace_keys.py`), then fit the
  motion lane's rig to them. Tracing works (recall 0.99, every ink piece kept, across all 40 keys).
  Holding the background does not yet: separate character and background drawing is required.

| # | Stage | Reads | Writes | Runs where | Gate |
|---|---|---|---|---|---|
| 0 | Select | `dataset/clips.csv`, `data/subject_queue.json` | `source.json`, `contact-sheet.png` | agent + browser (archive video) | continuous event, subject ≥ 1/10 of frame |
| 1 | Observe | source video | `clip.json` (frames at 12 fps), `camera.json`, `scene_masks.json` | browser: SAM 2.1 + Grounding DINO; Python: phase-correlation pan | mask on ≥ 95% of frames |
| 2 | Identity | Quick, Draw! category file | `design.json`, `design.png` | CLIP joint space + classifier + agent pick | doodle recognised, typical stroke style |
| 3 | Plan | masks, footage | x-sheet draft in `shot.json` | agent | each key has a written reason |
| 4 | Keys (look) | frames, design, plan | `keys/art-key-*.png`, `keys/bg-plate.png`, prompts | image model or agent drawing | identity critic; M1; B1 |
| 5 | Trace | raster keys | `keys/traced.json` | `tools/trace_keys.py` | T1: recall ≥ 0.98, `parts_kept` = 1.0 |
| 6 | Rig | traced keys, masks | `poses.json` | agent + `rig.py` | M3 mask fit; rig redraw matches the trace |
| 7 | In-between | poses, camera, masks | per-frame cast strokes | `inbetween.py` | M4–M6 |
| 8 | Planes | bg plate, masks, doodles | `shot.json` | `build_shot.py` | each object names its source and plane |
| 9 | Tests | `shot.json` | `tests.json` | `tests.py` | all measured and structural tests |
| 10 | Critic | critic packet only | `reviews/*.json` | fresh agent | stills, then playback at normal speed |
| 11 | Ledger | every proposal and verdict | `ledger.jsonl` | `loop.py` | append-only, hash-chained |
| 12 | Pairs | accepted shots | `pairs/` | script | only playback-accepted shots are train-eligible |

## The two lanes, measured on one scale (20 Oct 2026)

`tools/style_score.py` simplifies any drawing the way Quick, Draw! simplified its own data, then
compares six stroke statistics with real doodles of the category (`data/lane_compare.json`):

- The motion lane (giraffe shot) has about the right number of strokes but lines that turn too often
  and run too long between points: the rig's wobble reads as jitter.
- The look lane (traced giraffe, cat, duck keys) has lines that turn like a person's but three to seven
  standard deviations too many strokes.
- So the join keeps the look lane's line and the motion lane's stroke budget: fit the rig to the trace,
  then redraw each rig part as one traced stroke.

`tools/match_strokes.py` gives the look lane its first motion: keys aligned by translation, strokes
matched key to key, matched strokes interpolated and the rest swapped at the midpoint (test T3).
Both lanes play side by side with their footage in `pages/projector.html`.

## Where learning comes in

Nothing has been trained yet. What exists is search: an agent proposes, tests and critics judge, the
ledger keeps every attempt. That is the data a learner would need:

1. **Pose from silhouette.** Each accepted key is a pair (footage frame + SAM mask → rig pose). With
   a few hundred pairs per body plan (quadruped, bird, vehicle), a small model can propose keys that
   the agent then corrects; the corrections are the next round's data.
2. **Preference over repairs.** Each ledger line holds a before, an after and a critic verdict. Those
   are preference pairs for a reward model over drawings, scored together with the measured tests,
   not instead of them. The classifier alone is a misleading reward: it accepts traced silhouettes.
3. **In-betweening.** Accepted shots give dense key → in-between sequences in one topology, which is
   what a learned in-betweener needs. Until then `inbetween.py` is the baseline to beat.

Training starts when a pair set exists that a fresh critic has approved at playback speed. Still-key
approval alone does not make a pair train-eligible.

## Tests

Current tests, as `shots/giraffe-walks-past/tests.py` computes them, plus the two the join adds:

| Id | Name | Bar | Kind |
|---|---|---|---|
| M1 | Reads as the category | classifier p above 0.75 (real human doodles score 0.75) | measured |
| M2 | Looks hand-drawn | stroke-style percentile at least 30 among real doodles (traced outlines: 36) | measured |
| M3 | Holds the footage pose | mask fit mean at least 0.65, no frame below 0.45 | measured |
| M4 | Planted feet stay put | under 2 px drift, on at least 4 planted intervals | measured |
| M5 | Body keeps its proportions | under 10% variation for each body segment | measured |
| M6 | Head travels on smooth arcs | under 4 px jerk | measured |
| T1 | Trace keeps the drawing | recall at least 0.98 and every ink piece kept | measured (new) |
| B1 | Background holds | at least 90% of background strokes unchanged between keys on a locked-off shot | measured (new) |
| S1 | Near planes move faster | sky slowest, foreground fastest | structural |
| S2 | Every drawing has a source | all objects | structural |
| S3 | Exposure sheet covers the shot | every frame, keys marked | structural |
| S4 | Page works on a phone | no sideways scroll at 390 px, no script errors | structural |
| S5 | Nearer things hide farther ones | no far lines inside the character | structural |
| J1 | Story reads with sound off | a fresh viewer names the action and every subject | judged |
| J2 | Drawn beats traced | blind A/B preference for the drawn version | judged |
| J3 | Keys alone tell it | keys-only playback reads as the action | judged |

Lessons that set these bars:

- A test can pass by measuring nothing. The first foot-slide test found no planted frames and
  passed; it now fails with fewer than four planted intervals.
- A number can pass while the drawing gets worse. Forcing one leg length passed the proportion
  test and crumpled the legs. Every numeric pass is followed by looking at the frames.
- Precision of the tracer is 1.0 by construction (traced lines sit on ink); recall and
  `parts_kept` are the informative numbers. `parts_kept` exists because recall stayed at 0.85
  while a cat's eye was missing.

## Scaling to more drawings

- Wave 1 (done to stage 5): rabbit, duck, horse, dog, cat, butterfly, bicycle, windmill,
  helicopter, giraffe. Giraffe is through stage 10 as a full shot.
- Wave 2 (queued): the next ten categories with a moving subject, by archive match score, in
  `data/subject_queue.json`. A high score only means the archive search found a likely shot.
- One agent per subject, run with `AGENTS.md`; critics are separate agents with fresh context.
- Body plans are shared: a quadruped rig serves dog, horse, cow, pig and raccoon. Build a rig once
  per body plan, then key many subjects with it.
