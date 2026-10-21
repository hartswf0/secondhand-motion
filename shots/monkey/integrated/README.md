# Monkey: the same doodle lowers its head and returns

This is a review candidate, not an accepted training pair. No training ran.

- Source: *The Story* (1969), clip `0c93c28c-6d9b-53c2-8cc7-905df20ec940`; raw interval .333333–3.5 s, excluding the opening dissolve. Sixteen actual source frames were inspected. Source framing is 4:3; render 480×360.
- Native Quick, Draw! monkey `6070278159335424`, twelve original stroke identities and point counts in every dense frame. Contributors / Google Creative Lab, CC BY 4.0. Head, face mask, angular eye marks, mouth U and both ear constructions stay assigned. The tail exists in the cast but is outside the close-up crop, with no claim about its hidden source placement.
- Eleven source-event keys, 77 dense frames at 24 fps. Each dense frame records clip-relative source time, actual nearest decoded raw source frame index and timestamp. The x-sheet names lowering, low hold and return events. One held background is composited with separate character keys.
- Archive reports public domain; independent rights verification did not run. See source.json for archive URLs, film time and exact raw SHA.

## Reproduce

From the repository root:

```sh
python shots/monkey/build_integrated.py --source /path/to/0c93c28c-6d9b-53c2-8cc7-905df20ec940.mp4 --mask-cache /path/to/pinned/monkey
python shots/monkey/record_integrated.py
python shots/monkey/finalize_integrated.py
python shots/monkey/build_integrated_page.py
python tools/verify_integrated.py monkey
```

The source and SAM JSON are SHA-pinned. Rendering uses a unique temporary directory, fully decodes each final movie, verifies 77 frames and atomically replaces it. Boards are built after all movie writers and tracing finish. The player opens without a server and keeps the playback position when switching source/cartoon/comparison.

## Evidence and remaining gaps

Current independent review: `review-v3.json` (unedited). The central down-left bow is not embodied in the low head poses: the doodle's face stays upright and high while the whole head moves left. This loses the source event even though the original doodle identity survives.

Trace minimum recall 0.997346, ink pieces retained 1.000. Held background geometry is 100% unchanged. Filled rig/SAM fit mean 0.615984, minimum 0.567650; original bars remain mean ≥.65, minimum ≥.45. The target is an approximate broad fur/body segmentation; CI nominal timestamps differ from raw PTS and are not continuity evidence.

Recognition was not run. No normal-speed motion approval is claimed. No independently observed planted-foot intervals are available in this close-up, so the minimum-four foot-contact gate fails. No depth/parallax validation or phone browser check ran. All rejected full revisions and unedited independent reviews remain available; the parent ledger is hash-linked and append-only. Still-image components and the overall animated bar are separate.

Assembly and final decode/key comparison reports contain measured results. Technical validation does not establish drawing recognition or approved motion.

Stage wall-clock durations were not instrumented; no duration measurements are claimed.

Final technical verification passed: three movies fully decoded at 77 frames / 24 fps; 22 cartoon/comparison key checks, maximum RGB MAE 1.901559 against the fixed 2.0 bar; 65 relative links, inline JS, strict JSON and 3 hash-linked ledger records checked. See final-verification.json. All 11 pre-encode reviewed key rasters were reproduced exactly before a codec-only CRF 19→12 change; see codec-reencode.json.
