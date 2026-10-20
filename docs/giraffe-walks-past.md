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
