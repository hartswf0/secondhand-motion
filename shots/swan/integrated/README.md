# Swan neck dip and lift

Swan glides on the lake with its head held low and then lifts the curved neck near the end while the camera pans. Source and drawing share a fixed 2× viewport crop so the small bird can be inspected.

12 paired keys and 73 frames at24fps. Native Quick, Draw! key 4762067460423680; stroke IDs and original point counts retained. Explicit extra strokes and held scene objects keep their own source credits.

Fresh still review v3: native identity met; source framing/pose not met. In the early low-neck samples, the drawing folds the neck down from the top of the back and hangs the head below it. The source retains a small upright hooked neck with its crown above the back and its bill at the water. Key 1 makes this difference particularly clear. Recognition classifier, audited final mask fit, four verified contacts and actual normal-speed playback remain unrun or unmet. No training ran.

Trace recall 0.98972603; all pieces kept 1.0. Trace gate passes. Both technical verifiers pass: decoded movie/key image agreement and independent raw-video/PTS/viewport source pairing. These checks do not approve motion. All reviewed/rejected candidates and raw verdicts are retained in revisions/ and review-v*.json; ledger is ../ledger.jsonl.

Reproduce with `python shots/swan/build_integrated.py --source /path/to/299e589e-f689-595b-9f3c-e5537e5c84a6.mp4`. Source SHA and frozen input snapshots are retained. Quick, Draw! contributors / Google Creative Lab, CC BY4.0. No training ran.
