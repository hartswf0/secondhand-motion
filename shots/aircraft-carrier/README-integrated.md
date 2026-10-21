# Aircraft carrier turns past the bow

Five native strokes describe deck and hull. Island, parked aircraft and crew are absent from this sparse source drawing; no new technical detail is invented.

3 independent still review round(s). Native identity: True; sampled source pose: False. Across all 15 paired keys the long deck runs off the upper frame, while the source shows the foreshortened deck and its aft extent within the image. The cartoon presents an oversized elongated bow/deck crop instead of the source whole-carrier framing. Normal-speed playback, classifier and verified material contacts remain unrun. No training ran.

Current candidate: **integrated-v3**, 15 source-paired keys and 87 frames at24fps. Native Quick, Draw! key **6257793294139392**. Independent sampled native identity: **True**; sampled source pose: **False**. Final raw verdict: `review-v3.json`. Normal-speed playback is unrun and motion remains unapproved.

Across all 15 paired keys the long deck runs off the upper frame, while the source shows the foreshortened deck and its aft extent within the image. The cartoon presents an oversized elongated bow/deck crop instead of the source whole-carrier framing.

Native stroke/point counts remain intact. Extra operating/support geometry has separate source credit in `compatibility.json`; it is not original doodle ink. Source metadata preserves raw SHA-256, interval, decoded source PTS/index per frame, archive ids/URLs and reported rights. Classifier, audited same-instance mask fit and material contacts remain unmet or unrun. No zero-contact pass is claimed. No training ran.

Rebuild with `python shots/aircraft-carrier/build_integrated.py --source /path/to/raw.mp4`. Frozen inputs are under `input/`; prior full candidates and raw reviews remain under `revisions/`. The external raw source must match its pinned hash. The shared engine separates static geometry/camera from character/support motion, writes temporary frames outside the repository and atomically replaces fully decoded movies.

`integrated/verification.json` checks saved keys against decoded movie frames and source photographs/left movie panels against pinned raw video and nearest decoded PTS. Artifact/source agreement is not artistic motion approval. Final own-file hashes are in `integrated/freeze.json`.

Open `integrated/index.html` for the mobile comparison player.
