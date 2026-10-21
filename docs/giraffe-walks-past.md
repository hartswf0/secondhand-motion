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

## Refinement round: every subject held to the Giraffe Walks Past bar

The bar was measured first. Giraffe Walks Past itself was given to a fresh blind critic with the same packet
every other subject gets (16 evenly spaced frames of the animation, the same 16 frames of footage, four keys,
the doodle). It scored 3 of 5, motion "broken", follows the film "yes". So a score of 3 with the identity bar
met is the Giraffe Walks Past level under this protocol, and a 4 is above it.

What changed in the tools for this round:

- `rigs/inbetween.py`: optional point-by-point optical-flow tracking between keys (spec `track`), turned on or
  off per subject by the pops measure; a Gaussian `smooth` over every pose value; scalar pose entries eased.
- `rigs/template_rig.py`: turns through yaw with `front_regions` (front strokes shift, outline narrows),
  `_face` and `_xscale` for a flipbook turn, jaw parts moved by `shift_by`, foreshortening limits.
- `tools/critic_packet.py --dense`: 16-frame strips; `tools/pops.py` and `tools/pop_frames.py` measure centre
  acceleration and size steps against the Giraffe Walks Past baseline (0.103 and 0.062).
- Field subjects (rain, hurricane) and the tornado and sheep scenes drop cel paint (`no_cel`) where it erased lines.

Result after up to four critic rounds per subject (latest verdict, `shots/<slug>-gwp/reviews/`):

- Above the bar (4): butterfly, flying saucer, windmill.
- At the bar (3): duck, tornado (both raised from 2 this round), cow, horse, hurricane, rabbit, monkey, fan,
  helicopter, mosquito, raccoon, rain, roller coaster, sailboat, see-saw, sheep, skateboard, spider, tiger,
  tractor; bicycle scores 3 but its identity bar is not met (the frame crops to a single wheel).
- Below the bar (2): cat, dog, pig, giraffe (head close-up). Each needs drawn keys the rig cannot make by
  moving the doodle: the pig turning to face the camera, the giraffe's jaw opening and closing at one head
  size, the cat and dog turning. Repairs that only re-timed or re-scaled these shots did not raise them.

## Wave 4: twenty-five more subjects (`data/wave4.json`)

The same line, run for twenty-five subjects at once, with one agent per subject for the hand work.

- **Choosing.** Twenty-five categories from the 100-clip pool were surveyed in CI. One planning agent per five
  subjects read each contact sheet and doodle bank and wrote the plan with `tools/plan_subject.py` (interval,
  key times, detector label, doodle). Six clips were rejected on sight: parachute (the clip is the inside of a
  hot-air balloon), fire truck (a still close-up of a cab), motorbike (only a wheel and a helmet), sea turtle
  (1.75 s between dissolves), saxophone (no saxophone in the clip) and saw (a machine saw under a guard). Ten
  replacements were surveyed from `candidate-reserves.json`; squirrel and parrot were rejected, elephant (a
  building shaped like an elephant) and camel (occluded, with an undetected cut) were dropped to keep the wave
  at twenty-five.
- **Tracking** for all twenty-five in CI as before. The camera clip's first frame belonged to the previous shot
  and is trimmed on import.
- **Rig, keys and scene** by one builder agent per subject, from one written procedure. Builders placed keys from
  the frames whenever SAM followed something else (the cellist instead of the cello, the trumpet player instead
  of the trumpet, the penguin's white belly only, the whole sea, the whole cloud bank) and measured motion
  directly where that was more exact than placing by eye (the dragon's pull-back and head rock by feature
  alignment, the trumpet by image alignment, the lion's camera by phase correlation on fixed scenery).
- **New: scenery that changes during a shot** (`tools/gwp_build.py`). A scene object may carry `visible`
  [f0, f1], or `rig_poses`: keys for a second copy of the character's own rig, drawn every frame by the same
  rig. The second ant meeting the first, and the first lion turning its head as it leaves, use it. Copies on
  the character plane are drawn in black in critic packets.
- **Critics.** One fresh blind critic per subject on the 16-frame packet; a repair by the subject's own builder
  when the critic named a fixable gap; at most three rounds.

Result (latest verdict per subject, `shots/<slug>-gwp/reviews/`): identity bar met for all twenty-five. Fifteen
score 4 (speedboat, van, swan, snake, crab, frog, flower, lighthouse, guitar, trumpet, shovel, paintbrush,
light bulb, camera, aircraft carrier) and ten score 3 (ant, dragon, lion, cloud, ocean, alarm clock, cello,
broom, penguin, rhinoceros); none is below the Giraffe Walks Past level. Stated plainly: several of the 4s are
shots where the film's subject barely moves (camera, shovel, frog, flower, guitar), so there is little for the
drawing to get wrong. The 3s share the earlier kinds of gap: motion the doodle has no part for (the cello's bow,
the ocean's foam, the cloud's swelling contour), turns shown by narrowing instead of turning (alarm clock), and a
fast sweep that the smoothing either lags or lets jump (broom: rounds 2 and 3 scored lower than round 1, and
round 1's build was restored).

## Drawn keys: keyframes drawn by hand over the footage (`tools/drawn.py`, `tools/draw_key.py`)

The rig can only bend the doodle. It cannot turn a head toward the camera, open a mouth, or add a bow, a pedal leg or a splash. This pass adds keys drawn by hand over the footage at the frames that matter, in the manner of the CINEOSIS handmade film, and judges every subject with a fresh blind critic using the SCION brief (`docs/scion-brief.md`).

- **A drawn key** is `shots/<slug>/drawn/k###.json`: the doodle's own strokes at that frame with their points moved, plus optional `extra` strokes for parts the doodle never drew (a bow, a crank and leg, eyestalks, a second eye, a hand). Each key has a one-line `why`. `xsheet.json` names the line (the one beat the shot exists for), holds, and `ease` (`linear` for steady travel).
- **How it is applied** (`tools/drawn.py`, called by `tools/gwp_build.py`). At a drawn frame the drawing is the key. Between keys the difference from the rig is eased from key to key. An undrawn rig key counts as a key with no change, so drawers either draw every rig key or rewrite the pose file so its keys fall on the drawn frames.
- **Sheets for drawing** (`tools/draw_key.py`). `frames` shows every frame with the drawing on it. `key` shows a frame enlarged with a grid in frame pixels and numbered strokes and points, and writes the template. `check` shows the key over the footage and alone on white.
- **Procedure.** One drawer per subject reads the baseline critic's description of the film, finds the line, the extremes, contacts and turns, draws the keys, rebuilds and looks at least three times. Then a blind critic judges the 16-frame strip against the footage. When the verdict is "reference stronger", the drawer repairs from the critic's `primary_gap` and `closes_when`. A subject gets at most three rounds.
- **Baseline.** Before any drawing, every subject was judged by the same critic prompt (`shots/<slug>/drawn/baseline.json`).

Result (52 subjects with a baseline; pig was run separately and ended at 3 after three rounds, with a written inquiry in `shots/pig/drawn/inquiry.md`):

- **Mean motion score** rose from 3.23 to 3.71.
- **Verdicts.** "Bar met" went from 20 subjects to 38.
- **Per subject.** 22 rose, 26 stayed the same and 4 fell.
  - **Fell:** aircraft carrier, cello, rabbit and see-saw. Each fell for a reason the critics named: a three-quarter view the doodle has no construction for (carrier, rabbit), a scaled-down instrument plus an added hand (cello), and added figures whose lift reads in jumps (see-saw).
- **Common gap among the subjects still at 3** (cat, alarm clock, horse, raccoon, rhinoceros, giraffe, penguin, bicycle, hurricane, ocean). A turn or a change of construction still reads as one drawing swapped for another rather than one drawing rotating.

What the critics taught the drawers, stated plainly:

- At strip size, a drawing that is redrawn reads as a pop even when the in-betweens are smooth. Turns have to be built from one outline whose points move, not two constructions that switch.
- Keep the doodle's own proportions before matching the film's: identity failed whenever a key was stretched to fit the footage.
- Undrawn rig keys and the rig's own in-betweens leak into the shot. Several fixes were keys on every frame of a fast passage.
- Props and other actors the subject reacts to (a pole, a hand, a bow, a second ant, a woman lifting a child) need to be drawn, as scene objects with `visible` windows or as extra strokes.

| Subject | Baseline | Drawn-key rounds | Final verdict | Identity |
|---|---|---|---|---|
| aircraft-carrier | 3 | 2 → 2 → 2 | reference stronger | bar_not_met |
| alarm-clock | 3 | 3 → 3 → 3 | reference stronger | bar_met |
| ant | 3 | 3 → 4 | bar met | bar_met |
| bicycle | 3 | 3 → 3 → 3 | reference stronger | bar_met |
| broom | 3 | 4 | bar met | bar_met |
| butterfly | 4 | 4 → 3 → 4 | bar met | bar_met |
| camera | 5 | 5 | bar met | bar_met |
| cat | 2 | 3 → 3 → 3 | reference stronger | bar_met |
| cello | 4 | 3 → 3 → 3 | reference stronger | bar_met |
| cloud | 2 | 4 | bar met | bar_met |
| cow | 2 | 4 | bar met | bar_met |
| crab | 4 | 4 | bar met | bar_met |
| dog | 2 | 2 → 4 | bar met | bar_met |
| dragon | 3 | 4 | bar met | bar_met |
| duck | 2 | 4 | bar met | bar_met |
| fan | 4 | 4 | bar met | bar_met |
| flower | 4 | 4 | bar met | bar_met |
| flying-saucer | 4 | 4 | bar met | bar_met |
| frog | 4 | 4 | bar met | bar_met |
| giraffe | 2 | 3 → 3 → 3 | reference stronger | bar_met |
| guitar | 4 | 4 | bar met | bar_met |
| helicopter | 4 | 4 | bar met | bar_met |
| horse | 3 | 3 → 3 → 3 | reference stronger | bar_met |
| hurricane | 2 | 2 → 3 → 3 | reference stronger | bar_met |
| light-bulb | 3 | 4 | bar met | bar_met |
| lighthouse | 4 | 4 | bar met | bar_met |
| lion | 3 | 3 → 4 | bar met | bar_met |
| monkey | 3 | 4 | bar met | bar_met |
| mosquito | 3 | 3 → 4 | bar met | bar_met |
| ocean | 3 | 3 → 3 → 3 | reference stronger | bar_met |
| paintbrush | 4 | 4 | bar met | bar_met |
| penguin | 3 | 3 → 3 → 3 | reference stronger | bar_met |
| rabbit | 3 | 3 → 3 → 2 | reference stronger | bar_not_met |
| raccoon | 2 | 3 → 3 → 3 | reference stronger | bar_met |
| rain | 3 | 4 | bar met | bar_met |
| rhinoceros | 3 | 2 → 2 → 3 | reference stronger | bar_met |
| roller-coaster | 2 | 3 → 3 → 4 | bar met | bar_met |
| sailboat | 2 | 4 → 4 | bar met | bar_met |
| see-saw | 4 | 2 → 3 → 3 | reference stronger | bar_met |
| sheep | 4 | 3 → 4 | bar met | bar_met |
| shovel | 4 | 4 → 4 | bar met | bar_met |
| skateboard | 3 | 3 → 3 → 4 | bar met | bar_met |
| snake | 4 | 4 | bar met | bar_met |
| speedboat | 4 | 3 → 4 → 4 | bar met | bar_met |
| spider | 2 | 3 → 4 | bar met | bar_met |
| swan | 4 | 4 → 4 | bar met | bar_met |
| tiger | 3 | 3 → 4 | bar met | bar_met |
| tornado | 4 | 3 → 4 | bar met | bar_met |
| tractor | 3 | 4 | bar met | bar_met |
| trumpet | 4 | 4 | bar met | bar_met |
| van | 4 | 3 → 4 → 4 | bar met | bar_met |
| windmill | 4 | 4 | bar met | bar_met |

Baseline is the motion score before drawn keys; the rounds column lists each critic's motion score in order (1-5). Verdicts and identity are from the last round.

## Wave 5: fifty subjects held to the SCION bar (`data/wave5.json`)

The goal for this wave was fifty new subjects that a blind critic passes on all three counts: the verdict is
"bar met", the identity of the doodle is kept, and the motion scores 4 or 5 out of 5.

- **Survey and plan.** About half of the first candidate clips did not show their subject, so 127 more were
  surveyed in CI. Planning agents wrote a plan, a doodle choice or a rejection for each. 55 clips had real motion;
  59 others were still shots and were kept as spares.
- **Build.** One builder agent per subject made the rig, keys and scene, with three to six look-and-fix rounds
  measured by `tools/pops.py` against the Giraffe Walks Past numbers (centre step 0.103, size step 0.062).
- **Motion sheets.** Each critic packet now has three extra sheets made every frame: the animation (e.png), the
  footage (f.png) and the drawings overlaid on one panel (g.png). The critic reads frame-to-frame jumps from these
  instead of from a 16-frame strip.
- **Drawn keys and repairs.** When a critic named a gap, a repair agent drew keys over the footage
  (`shots/<slug>/drawn/`) or changed the scene, then a fresh blind critic judged it again. 140 critic verdicts
  were written in all.
- **What repairs learned** (now in the drawing instructions): keep each stroke's point count so resampling does not
  flicker corners; draw a key on every rig key frame; turn a rigid part by rotating one fixed shape, never by
  redrawing it; hide lines behind a part by cutting them at its outline a little more each frame, never by removing
  a whole stroke at once; scenery that moves (a hand, a rope of ice cream, a turning base) is drawn as one copy per
  frame, each visible on its own frame.

Result: **54 subjects pass** (bar met, identity met, motion 4 or 5). 5 score 5
(fish, baseball-bat, umbrella, popsicle, cell-phone). The rest score 4.
1 did not pass after repeated rounds and are reported as they stand: book (5 rounds, motion 3). In each the critic still sees one gap: the timing of a fast event spread or bunched against the film, or a part that changes shape in one frame.

Stated plainly: the critics judge still frames, not playback. Their requests sometimes conflict between rounds
(one critic asked the apple to shrink at the end, the next said the film's apple does not shrink), and the
animal-migration critics read the row breaks of the motion sheet as scenery jumps that measurement showed were not
in the frames. Lobster needed eight rounds; it passed only when the swinging claw was redrawn as a mirror of the
doodle's own left claw.

| Subject | Critic rounds | Final verdict | Motion | Identity |
|---|---|---|---|---|
| ambulance | 4 | bar met | 4 | bar met |
| animal-migration | 5 | bar met | 4 | bar met |
| apple | 5 | bar met | 4 | bar met |
| baseball-bat | 2 | bar met | 5 | bar met |
| basket | 2 | bar met | 4 | bar met |
| bat | 3 | bar met | 4 | bar met |
| binoculars | 2 | bar met | 4 | bar met |
| bus | 2 | bar met | 4 | bar met |
| cannon | 3 | bar met | 4 | bar met |
| canoe | 4 | bar met | 4 | bar met |
| cell-phone | 1 | bar met | 5 | bar met |
| coffee-cup | 3 | bar met | 4 | bar met |
| diving-board | 4 | bar met | 4 | bar met |
| dolphin | 3 | bar met | 4 | bar met |
| door | 3 | bar met | 4 | bar met |
| eye | 1 | bar met | 4 | bar met |
| face | 2 | bar met | 4 | bar met |
| fish | 2 | bar met | 5 | bar met |
| flamingo | 2 | bar met | 4 | bar met |
| frying-pan | 2 | bar met | 4 | bar met |
| garden-hose | 4 | bar met | 4 | bar met |
| hammer | 3 | bar met | 4 | bar met |
| hand | 1 | bar met | 4 | bar met |
| hat | 4 | bar met | 4 | bar met |
| helmet | 2 | bar met | 4 | bar met |
| hourglass | 2 | bar met | 4 | bar met |
| ice-cream | 9 | bar met | 4 | bar met |
| ladder | 7 | bar met | 4 | bar met |
| lantern | 1 | bar met | 4 | bar met |
| lobster | 8 | bar met | 4 | bar met |
| lollipop | 1 | bar met | 4 | bar met |
| map | 1 | bar met | 4 | bar met |
| mermaid | 2 | bar met | 4 | bar met |
| microwave | 1 | bar met | 4 | bar met |
| mug | 3 | bar met | 4 | bar met |
| palm-tree | 1 | bar met | 4 | bar met |
| pencil | 1 | bar met | 4 | bar met |
| pickup-truck | 2 | bar met | 4 | bar met |
| popsicle | 2 | bar met | 5 | bar met |
| river | 1 | bar met | 4 | bar met |
| sandwich | 1 | bar met | 4 | bar met |
| sleeping-bag | 2 | bar met | 4 | bar met |
| star | 1 | bar met | 4 | bar met |
| stove | 1 | bar met | 4 | bar met |
| submarine | 2 | bar met | 4 | bar met |
| tooth | 2 | bar met | 4 | bar met |
| traffic-light | 1 | bar met | 4 | bar met |
| train | 4 | bar met | 4 | bar met |
| umbrella | 1 | bar met | 5 | bar met |
| vase | 2 | bar met | 4 | bar met |
| wheel | 3 | bar met | 4 | bar met |
| wine-bottle | 1 | bar met | 4 | bar met |
| wine-glass | 1 | bar met | 4 | bar met |
| yoga | 2 | bar met | 4 | bar met |
| book | 5 | reference stronger | 3 | bar met |
