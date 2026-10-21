# Three brooms sweep the floor

Seventeen native strokes describe the main straw broom. Two separately moving background brooms are preserved from the frozen source-observed scene, all native copies. The moving apron/operator is omitted, not treated as stationary extracted geometry.

2 independent still review round(s). Native identity: True; sampled source pose: True. No sampled still gap identified; actual normal-speed playback, recognition and material contacts remain unapproved. Normal-speed playback, classifier and verified material contacts remain unrun. No training ran.

Current candidate: **integrated-v2**, 13 source-paired keys and 61 frames at24fps. Native Quick, Draw! key **6486360229675008**. Independent sampled native identity: **True**; sampled source pose: **True**. Final raw verdict: `review-v2.json`. Normal-speed playback is unrun and motion remains unapproved.

No sampled still gap identified. Recognition, contact verification and actual normal-speed playback remain unapproved.

Native stroke/point counts remain intact. Extra operating/support geometry has separate source credit in `compatibility.json`; it is not original doodle ink. Source metadata preserves raw SHA-256, interval, decoded source PTS/index per frame, archive ids/URLs and reported rights. Classifier, audited same-instance mask fit and material contacts remain unmet or unrun. No zero-contact pass is claimed. No training ran.

Rebuild with `python shots/broom/build_integrated.py --source /path/to/raw.mp4`. Frozen inputs are under `input/`; prior full candidates and raw reviews remain under `revisions/`. The external raw source must match its pinned hash. The shared engine separates static geometry/camera from character/support motion, writes temporary frames outside the repository and atomically replaces fully decoded movies.

`integrated/verification.json` checks saved keys against decoded movie frames and source photographs/left movie panels against pinned raw video and nearest decoded PTS. Artifact/source agreement is not artistic motion approval. Final own-file hashes are in `integrated/freeze.json`.

Open `integrated/index.html` for the mobile comparison player.
