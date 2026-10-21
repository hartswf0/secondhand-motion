# Tiger — integrated review candidate

This folder joins one real Quick, Draw! tiger to a retained archive event. It is a review candidate, not a playback-approved cartoon or a training pair. No training ran.

`index.html` is the offline comparison player. `comparison.mp4` shows source and cartoon together; `cartoon.mp4` and `source-excerpt.mp4` are separate full movies. Seven `source-NN.jpg` / `key-NN.png` / `key-NN.svg` pairs are exact samples of the 67-frame, 24fps timeline. `source-contact-sheet.jpg` contains16 inspected source samples. The held rock background and separated character keys have their own PNG/SVG files.

## Source and drawing

- Archive: *Andy's Animal Alphabet* (1950), source `ac8a9aed-52c4-5df8-adcc-2e1a8f6bfcfa`, clip `21f72c0b-0951-50f9-8016-8dbbc3669858`.
- Retained clip-relative interval3.25–6.0s; original-film interval457.004–459.754s. The interval follows the cut near3s and contains a resting tiger's modest head turn, with no observed body movement or camera pan. The16 samples support continuity; continuous source playback was unavailable.
- Raw source SHA256: `cafbd01e4e428dcc820d068d8bc3c3e7154c76a7685f0815ade52a4c2347bbfa`. Archive reports `public_domain`; independent rights verification has not run.
- Locked native doodle `6296227597516800`, candidate27 from the local tiger survey. Quick, Draw! contributors / Google Creative Lab, CC BY4.0. Original stroke arrays and credit are in `design.json`.
- The parent folder's original provisional face-only key `5746588771155968` remains untouched and is preserved in `preflight/`. It was unsuitable for the visible lying body and paws. `compatibility.json` records the pre-key selection.

## Editable construction

All11 original stroke identities and point counts survive in every dense frame. Native head/ears, eyes, triangular nose and bent mouth have stable bindings; native body, folded legs, tail and stripe zigzags hold. Source head/nose/eye landmarks drive a small timed head turn; there is no invented chewing cycle. The hidden far body/tail is cropped, not reconstructed. The coarse source-framed rocks are separately agent-authored once and remain held. The native folded-leg simplification cannot represent photographed paw anatomy in detail.

`shot.json` contains every dense frame's source time, raw source index, pose, strokes, key indices and x-sheet. `correspondence.json` retains the original point counts and source observations. `traced.json` comes from `tools/trace_keys.py`; it measures character ink recall and retained pieces independently of the editable native stroke identities.

## Evidence and limits

`assembly-checks.json`, `mask-fit.json` and `video-validation.json` contain actual measurements. Whole-tiger mask fit compares the filled native character to nearest12fps SAM samples, not to the model's confidence estimate. The cache is pinned in `sam/provenance.json`; four parent-inspected targets covered the visible lying head/body/paws. Soft mask edges, approximate resampling and thin whiskers limit the boundary evidence.

Independent raw reviews are `review-vN.json`; rejected full versions remain in `revisions/vN/`. The parent folder's `ledger.jsonl` is append-only and hash-linked. The page's prominent review note reports the latest still verdict and remaining gaps. Actual normal-speed playback, category classifier, independent390px browser-layout inspection and four verified planted-contact intervals remain unavailable/unrun. Zero intervals fails the contact gate. No artistic or motion approval follows from full decoding or saved-key/movie pixel agreement.

## Rebuild and verify

From the repository root:

```sh
python shots/tiger/build_integrated.py --source /path/to/21f72c0b-0951-50f9-8016-8dbbc3669858.mp4 --mask-cache shots/tiger/integrated/sam
python shots/tiger/record_integrated.py
python shots/tiger/build_integrated_page.py
python tools/verify_integrated.py tiger
```

The builder asserts raw-video and cache hashes, uses a unique temporary render directory, fully decodes/counts each new movie before atomic installation, and builds pair boards only after the movie writers finish. Recording and page rebuilding restore the independent review status after a deterministic render. The verifier checks complete decoded counts, exact key positions against both published movies with a lossy RGB-MAE threshold, strict JSON, local page links, JavaScript syntax and ledger integrity. Its scope is technical artifact integrity only.
