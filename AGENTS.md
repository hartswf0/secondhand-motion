# Agent prompt: turn one archive shot into a doodle cartoon

You are working in the Cartoon Archive repository. The goal of the project is that any shot in the
Moving Image Archive can be watched as a moving Quick, Draw! cartoon: the subject redrawn in the
identity of one real doodle, moving the way the footage moves, on depth planes that slide with the
real camera. You take **one subject** from the queue and carry it through the pipeline as far as the
gates allow. A smaller result that passes its gates is worth more than a complete one that does not.

Read `pages/pipeline.html` (or `PIPELINE.md`) for the stage contracts before you start. This prompt
tells you how to work; the pipeline tells you what each stage must produce.

## Your assignment

- Subject: `{CATEGORY}` (from `data/subject_queue.json`, wave `{WAVE}`).
- Work folder: `shots/{CATEGORY}/`. Create it. Everything you make goes there, nowhere else.
- Starting state: if the folder already has a `shot.json` or a `ledger.jsonl`, read both and continue
  from the last accepted revision. Never start over silently.

## How to work

1. **Watch before you choose.** Search results are ranked by an image-text model, not by a person.
   Look at a contact sheet of at least 12 frames across every candidate clip before picking one.
   Reject clips with cuts, dissolves, a different species or object, or a subject smaller than about
   a tenth of the frame. Write down why the chosen interval is one continuous event.
2. **Pick one doodle and keep it.** The character must stay recognisably the same Quick, Draw!
   drawing in every key: same construction, same stroke habits, same simplifications. Record its
   `key_id`. A conventional cartoon of the animal is a failure even if it looks better.
3. **Plan keys from the footage, not from habit.** Choose key times where the motion changes:
   contacts, extremes, turns, a head lifting. Write one line per key in the x-sheet saying what
   happens there.
4. **Draw the character and the background separately.** Draw the background plate once per shot
   and the character on a blank ground for each key. When an image model redraws the whole frame
   per key, the set dressing changes every key and the background boils (the selected-drawings
   batch had this problem: in the dog shot, where the trees and bowl barely move, only about a fifth of the traced strokes stay in place from key to key).
5. **Trace every key to strokes** with `tools/trace_keys.py`. Vector strokes are what can be
   in-betweened, placed on planes and measured. A raster key is a reference, not a deliverable.
6. **Give the keys one topology.** In-betweening needs the same parts in every key. Fit the
   subject's rig (pose points: head, body, limbs, contacts) to each traced key over the SAM
   silhouette, or establish stroke-to-stroke correspondence. Do not morph unmatched strokes.
7. **In-between with the footage's physics.** Feet that are planted in the footage stay planted in
   world space; the camera pan comes from the footage; held frames are allowed and often right.
8. **Run the tests, then look.** Every numeric pass is followed by looking at the frames, because
   tests can pass while the drawing gets worse (see the notes in `pages/pipeline.html`).
9. **Get a blind critique.** Hand the critic only the files listed under *Critic packet*, never your
   reasoning or this conversation. Repair the one bounded gap the critic names, then ask a fresh
   critic. Stop after three rounds and record what is still wrong.
10. **Write everything to the ledger.** Each proposal, critic verdict and repair is one line in
    `shots/{CATEGORY}/ledger.jsonl` (format: `batches/2026-10-20-selected-drawings/schema.json`,
    append with `loop.py`). Rejected candidates stay in the folder.

## Gates you must not lower

| Gate | Bar | Stage |
|---|---|---|
| Continuous source | no cut or dissolve inside the interval, checked on a contact sheet | select |
| Identity kept | a fresh critic shown the doodle and the keys says it is the same drawing | keys |
| Trace fidelity | recall ≥ 0.98 and every ink piece kept (`parts_kept` = 1.0) | trace |
| Held background | ≥ 90% of background strokes unchanged between keys on a locked-off shot | keys |
| Recognition | Quick, Draw! classifier p above 0.75 for the category on every key | keys |
| Mask fit | mean at least 0.65 and no frame below 0.45 | rig |
| Foot slide | planted contacts drift under 2 px in world space, measured on at least 4 planted intervals | in-between |
| Playback | a fresh critic watches at normal speed and approves the motion | critic |

If a gate cannot be met, say so in the ledger and in your report. Never change a bar, a test, or a
threshold to make your work pass. If a test measures nothing (zero intervals, zero frames), it fails.

## What you may and may not claim

- Say exactly what ran. If no model was trained, write "no training ran". An agent choosing among
  candidates with a critic is search, not reinforcement learning.
- Still-key approval is not motion approval. Keep those two verdicts separate everywhere.
- Every drawing names its source: a Quick, Draw! `key_id`, an image-model prompt file, or "drawn by
  agent" with the reason no real doodle fitted.
- Keep the archive's source ids, interval and reported rights in `source.json`. Quick, Draw! is
  CC BY 4.0 and must be credited.

## Deliverables in `shots/{CATEGORY}/`

- `source.json` — clip id, source id, interval, archive URLs, reported rights, why this clip.
- `design.json`, `design.png` — the chosen doodle.
- `contact-sheet.png` — the frames you watched to choose.
- `keys/` — raster keys, prompts, background plate, and `traced.json` from `tools/trace_keys.py`.
- `poses.json` — rig points per key (or `correspondence.json`).
- `shot.json` — the single state file: planes, camera, objects, cast frames, x-sheet. Same schema
  as `shots/giraffe-walks-past/shot.json`.
- `tests.json` — every gate above with value, bar and pass or fail.
- `reviews/` — each critic's verdict file, unedited.
- `ledger.jsonl` — append-only.
- `index.html` — the shot page, built by `python3 tools/build_pages.py`; it must open from the file
  system with no server and no network except fonts.

End with a short report: which gates passed, which failed, the one change that would most improve
the shot, and how long each stage took.

## Critic packet (give the critic only this)

- the source contact sheet and `source.json` interval,
- `design.png` (the doodle the character must stay),
- the keys as stills, and for playback review the rendered shot at normal speed,
- this instruction: "Say whether the bar is met. If not, name the one gap that matters most and the
  smallest repair that would close it. Name what must not be lost in the repair. Do not suggest
  style changes beyond the doodle's own."

The critic does not see the builder's notes, earlier critiques, or test numbers.

## Production coordination

`production/README.md` adds a 100-clip source pool and a local coordinator. Its seven coarse stages organize the pipeline; they do not replace the gates above or `tests/registry.json`. A supervisor must verify each applicable gate against the current artifacts before accepting a coordinator result. The category/wave queue remains separate. Source photographs and proposed keys are not authored artwork, and a queue snapshot does not indicate live workers. Keep one-subject deliverables in `shots/{CATEGORY}/` as above.
