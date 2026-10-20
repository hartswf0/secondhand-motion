# How Giraffe Walks Past was made

Giraffe Walks Past is the one shot in this repository that a critic watched and mostly believed.
This page records exactly how it was built, step by step, with the files each step left behind,
so the same method can be run on every other subject. Everything below is in
`shots/giraffe-walks-past/` unless another path is given.

## 1. Source

- Clip: *Wonderful World (Part II)*, Moving Image Archive, found by the archive's own search for "giraffe".
- 33 frames at 8 fps, 480 × 360, stored as JPEG data inside `clip.json` (`frames[i].im`).
- One adult giraffe walks right past two young giraffes and a bare thorn tree; the camera pans.

## 2. A silhouette for every frame (SAM)

This is the step the later redraws skipped, and it is the one everything else leans on.

- Run in the browser (transformers.js 4.3.1, onnxruntime-web): Grounding DINO
  (`onnx-community/grounding-dino-tiny-ONNX`) finds the giraffe from the text "giraffe" and gives a
  box; SAM 2.1 (`onnx-community/sam2.1-hiera-small-ONNX`) turns the box into a mask, about 1–2 s a frame.
- Every one of the 33 frames has a mask: 48 polygons in all, SAM's own quality score 0.82–0.93
  (`clip.json`, `frames[i].p` and `frames[i].iou`).
- The scenery got masks too: the two trees (`scene_masks.json`). The right-hand tree was then
  matched to a real Quick, Draw! tree by silhouette overlap (`match_tree2.json`, IoU in the file).

## 3. The camera

- The pan was measured from the footage frame to frame (`camera_raw.json`: about 76 px left over the
  first 13 frames, then still), then smoothed (`camera.json`).
- Planes slide by `camera × (z_ref / z)`, so near planes move faster than far ones.

## 4. A first pose from the silhouette

- `autopose.py` reads each mask and places body points from its geometry: head at the top, nose at the
  leading edge of the top band, body at the widest band, rump and chest at its ends, hooves at the bottom.
- `pose_auto.json` holds the result. It is a starting point, not a drawing.

## 5. Keys drawn over the silhouette

- The agent moved those points by eye with the SAM silhouette drawn under the footage, the way
  Mechner traced over silhouettes for Prince of Persia: 5 keys first (`pose_agent.json`, every 8th frame),
  then 9 keys every 4th frame after review (`pose_agent_v2.json` … `pose_agent_v5.json`).
- Each key names head, nose, neck base, chest, rump, tail root, thigh, both bellies, four hooves and knees.

## 6. A rig that draws in the doodle idiom

- `rig.py` turns a pose into Quick, Draw!-style strokes: straight segments with a little wobble, a muzzle,
  ossicones, a tufted tail. It was written for one body plan, the giraffe's.
- Its parameters were chosen by search against a three-part score (`reward.py`, `top_params.json`):
  the Quick, Draw! classifier's confidence, how typical the stroke statistics are among 4,971 real giraffe
  doodles, and how much ink falls inside the SAM silhouette. No term alone was trusted: the classifier
  also accepts traced outlines.

## 7. In-betweens that follow the silhouette

`inbetween.py` makes every frame between keys:

- body points on Catmull-Rom curves through the keys;
- plus the **SAM residual**: how far the silhouette's centre departs from the straight line between the
  keys' centres, smoothed, added back, so in-betweens track the real animal and not only the keys;
- hooves that barely move between keys stay planted in world space (camera removed), others lift on arcs;
- legs re-solved per frame with each key's own leg lengths and knee direction (inverse kinematics).

## 8. Six planes

`build_shot.py` lays out the shot (`shot.json`):

| Plane | z | What is on it |
|---|---|---|
| Sky | 10 | two real Quick, Draw! clouds |
| Far treeline | 6 | real Quick, Draw! bushes |
| Trees | 3 | an agent-drawn bare thorn tree (no doodle matched above 0.58 IoU), the matched doodle tree, the ground line |
| Young giraffes | 2.5 | the adult's own rig at about 40 % scale, so all three share one drawing convention |
| Walking giraffe | 2 | the rigged character, following the footage |
| Grass | 1.2 | real Quick, Draw! grass |

## 9. Cel paint

The SAM silhouette is filled with paper under the walker, so lines on planes behind it do not show through
its body (structural test S5).

## 10. Tests and critics

- `tests.py` writes `tests.json`: recognition (M1), typicality (M2), silhouette fit (M3), planted feet
  (M4), proportions (M5), smooth arcs (M6), plane order, sources, x-sheet, phone layout, occlusion.
- Three rounds of blind critics, each fixing one named gap: young giraffes looked like pitchforks and the
  adult had no head; lines showed through the legs (fixed by cel paint); young giraffes read as llamas
  (redrawn with the adult rig). A blind A/B at five keys preferred the drawn key over the traced
  silhouette 4 times in 5 (`critic_key.json`).

## What the ten redraws did differently, and why they read worse

| Giraffe Walks Past | Puppet redraws (`shots/<cat>-redraw/`) |
|---|---|
| SAM silhouette on every frame | none: keys placed by eye on blurry footage, no silhouette |
| keys drawn over the silhouette | keys placed on raw frames, often misread |
| 9 keys, one every 4 frames | 4 keys (5 for the dog), one every 12–20 frames |
| in-betweens pulled to the silhouette every frame | in-betweens only interpolate the keys |
| a rig built for the body plan | one doodle stretched by two-point bones |
| rig parameters searched against classifier, typicality and fit | no search |
| scenery matched to SAM scene masks, on depth planes | one background plate |
| cel paint from the silhouette | white halo only |
| three critic rounds, one gap repaired each | one critic round, no repair |

And the drawn starting poses were not used: the batch already holds 40 keys an image model drew in the
doodle's identity, each approved by a fresh critic as matching the footage pose. The puppet redraws
ignored them and started from the bare doodle. The next pass starts from those drawn keys and puts them
over SAM silhouettes, which is this shot's method with better drawings.

## The second pass: drawn keys over SAM (`shots/<cat>-sam/`)

What was done for all ten subjects, following this shot's method:

- SAM 2.1 + Grounding DINO in the browser on every frame (`tools/browser/sam_run.js`, about 1.3 s a frame
  on WebGPU), imported with `tools/sam_import.py`: masks, polygons, a camera measured with the subject
  masked out, and a `silhouettes.png` sheet.
- `tools/key_align.py` finds the excerpt frame each drawn key's still matches (the stills were cut by a
  seek that lands 1 to 2 frames later than the key times) and the transform between them (near identity).
- `tools/sam_keys.py` leaves each drawing where it was drawn, splits it point by point into character
  (near this frame's silhouette) and scenery (also drawn by other keys away from their subject), draws the
  scenery once from key 0, and makes in-betweens by stroke matching plus the same silhouette pull as step 7.
  The silhouette is painted as a cel.
- Mistake in the first version: it searched a scale and shift for each drawing to raise ink-inside-mask
  fit (M3). That shrank and moved drawings that were already in place (rabbit to 75 %, 47 px), while part of
  the same drawing stayed on the scenery, so the subject showed twice. M3 rewarded the error: it went up
  (rabbit 0.28 to 0.81) while the picture got worse. Round 1 critic verdicts on that version are kept in
  `reviews/round1-misaligned/`.
- Each shot has its own page in this shot's viewer (`pages/<cat>-sam.html`) with cartoon, over footage,
  footage, planes in depth and silhouettes, and appears in the projector under "Drawn keys over SAM".

What the tests and ten blind critics said (round 2, on the corrected shots, `shots/<cat>-sam/reviews/critic-2.json`):

- Every critic named the subject. None saw the subject drawn twice. Critics flagged an offset from the
  footage only for bicycle (frames 1-4) and helicopter (frames 5-8), where the stills matched the excerpt
  worst; horse still splits head and muzzle across the fence rail.
- Identity failed for all ten (J4): the drawn keys are detailed traced-looking drawings, not doodles, and
  the classifier agrees (M1 near 0 except cat 0.35). The image model drew the footage, not the doodle.
- Motion broke for all ten at the swap between keys: four keys over 33 to 50 frames, with key drawings
  that do not share strokes (T3 0.02 to 0.49), so in-betweens cannot match them and the drawing pops.
  Giraffe Walks Past avoided this because one rig draws every frame; the keys only move points.

So the next step is the giraffe's other half: keep SAM and the drawn keys as pose references, but draw
every frame with one stroke set (a rig or a single doodle deformed to each key), and search its
parameters against classifier, typicality and fit, as in step 6.

## The third pass: the Giraffe Walks Past way, for all ten (`shots/<cat>-gwp/`)

The second pass still fell short because it skipped the giraffe's drawing work: a rig that draws every
frame, keys posed by hand every few frames, and real doodle scenery on planes. This pass does that work.

- **The rig is the chosen doodle itself** (`rigs/template_rig.py`, `rigs/<cat>_spec.json`). The doodle's own
  vertices and strokes are kept. A root similarity places the whole drawing (where, how big, how tilted)
  and keeps the doodle's proportions; named parts turn at joints (the rabbit's ears, head and front leg;
  the dog's head and four legs; the duck's head), wings fold toward the body, spokes, rotor blades and
  windmill sails spin. Every frame is the same drawing, bent; it is never redrawn (test T3).
- **Keys by eye over the silhouettes**, as for the giraffe: 9 to 20 per shot, each placed on an enlarged
  frame with a numbered grid and the SAM outline (`tools/key_grid.py`, `shots/<cat>-sam/pose_agent_v*.json`).
  Each spec says what its pose points mean.
- **In-betweens** (`rigs/inbetween.py`) as the giraffe's step 7: Catmull-Rom through the keys plus the
  smoothed SAM residual; number-valued pose entries (wing opening, spin angle) ease between keys. Size can
  be held steady for the whole shot, which the first rabbit critic asked for.
- **Scenery** (`rigs/<cat>_scene.json`, `tools/gwp_build.py`): real Quick, Draw! doodles (door, tree, bush,
  bucket, grass, fence, flower, leaf, hand, mountain, cloud, wheel) fitted into boxes placed by eye, on
  depth planes that slide with the measured camera; agent-drawn ground lines where no category fits, each
  with its reason. The rabbit's camera is the door edge tracked in every frame, because phase correlation
  failed on that clip.
- **Cel** from the SAM silhouette, as before.

Ten fresh blind critics, each shown the strip, the footage at the same frames, four keys and the doodle
(`shots/<cat>-gwp/reviews/`):

- **Identity bar met for all ten** (J4). This is the first pass where any subject met it.
- Follows the film: yes for rabbit and helicopter, partly for the rest.
- Motion smooth for windmill and duck; the others still jump at a turn or a size change (dog's turn,
  rabbit's entrance, giraffe's scale, horse at the end, helicopter's mast at the zoom).

Tests that still fail, stated plainly: silhouette fit (M3 0.04 to 0.41) fails everywhere, because the rig
keeps the doodle's proportions rather than the animal's, and a big-headed two-stroke rabbit does not fill a
real rabbit's silhouette; smooth arcs (M6) fail except the duck, because the footage moves fast and keys
are 4 frames apart; typicality (M2) is low where the chosen doodle is itself unusual (the rabbit doodle is
at the 26th percentile of real rabbits). Likeness to the chosen doodle (M2b) passes for all ten.

The next repairs the critics named: a connected turn for the dog instead of a squash and flip; the duck's
and cat's head turning toward the viewer and to profile; the giraffe's jaw opening; the horse's head going
down into the hay at a steady size; the helicopter's mast kept short and upright.

## Wave 2: the full pipeline on ten new subjects (`shots/<slug>-gwp/`)

The ten wave-2 subjects had six draft keys each from an image model, approved as stills, but no frames,
masks or motion. They now go through the same method, with three additions:

- **Frames, SAM and depth on GitHub's machines.** The archive's media host is not reachable from the agent
  workspace, so `.github/workflows/wave2-track.yml` runs `tools/wave2_track.py` per subject: the key interval
  at 12 fps, Grounding DINO + SAM 2.1 (hiera-small) on every frame, Depth Anything V2 Small per frame. Each job
  pushes its output to branch `wave2-track/<slug>`; `tools/wave2_import.py` brings it into `shots/<slug>-sam/`
  and summarises depth (subject vs. top, middle and bottom of the scene). Two clips had a cut inside the
  interval (fan's last frame, flying saucer's first) and are trimmed.
- **Drawing toward the generated keys.** `tools/key_grid.py --target` draws each generated key (blue) over its
  frame, the SAM outline (red) and the rig (black). The generated keys carry the pose and the doodle's
  construction, but they were drawn on their own canvas: for the raccoon, flying saucer and mosquito they sit
  well away from the subject and at the wrong size. So keys take pose from the generated drawing and place
  and size from the silhouette. `rigs/fit_to_key.py` does a first automatic fit of the rig to a generated key
  (chamfer distance), corrected by eye.
- **Plane depths from measured depth.** A scenery plane with `z_from_depth` gets z = z(character) x subject
  depth / band depth, so a far fence slides slower than near ground because the depth map says so.

Rigid subjects (tractor, flying saucer, fan, tornado) are placed by two points and their wheels, blades or
nothing spin. Rain and storm surf are a field of marks (`rigs/field.py`): the doodle's own strokes repeated,
falling at a procedural speed (rain) or moved by the water's measured motion (surf).

## Wave 3, and the line for scaling it (`docs/production-line.md`, `tools/subject.py`)

Each subject is still made by hand, one at a time; what scales is everything around the hand work.

- **Survey in CI** (`survey.yml`, `tools/survey.py`): for a whole wave at once, a contact sheet of every clip
  (a frame every 0.25 s with its time), cut detection, and a bank of 40 real doodles of the category. The
  agent reads these to choose the interval and the doodle: in wave 3 that took one look per subject, and it
  rejected two clips the archive search ranked well (fire truck: a parked cab, nothing moves; bulldozer: a
  power shovel). Cuts it found by eye: the monkey clip cuts to a penguin, the cow to a title card, the tiger
  at 3.0 s.
- **Tracking in CI**: listing slugs in `data/track-now.json` runs frames, SAM and depth for that wave.
- **Rig specs by region** (`rigs/template_rig.py`): a part can be a box of the doodle instead of vertex
  ranges, read off the numbered doodle sheet (`tools/doodle_sheet.py`), so a new rig is a few lines.
- **First-pass keys** (`rigs/autoroot.py`, or placement from the silhouette for rigid things) and grids
  (`tools/subject.py sheets`), then correction by eye. The first pass is often wrong (SAM covers a cow's
  whole body when the doodle should sit on its head; it covers the whole flock instead of one sheep, where
  the agent tracked one sheep by template matching instead); the hand pass is where the shot is made.
- **Extras from the character's own doodle** (`copy_of_design` in a scene): the flock is the chosen sheep
  doodle, repeated small.
- **One fresh blind critic per subject**, and one repair round where the critic names a fixable gap
  (skateboard: spinning the lumpy wheel loops opened them; round 2 passed).

Wave 3 result: eight subjects built; identity bar met for all eight, the skateboard after one repair. Motion
reads broken for all but follows the film at least partly; the gaps named are the same kinds as before: jumps
where keys are far apart or the size changes, and head turns the rig only slides instead of turning
(monkey, tiger). The line page lists every subject's state and next step.
