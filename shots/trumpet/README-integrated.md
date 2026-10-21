# Trumpet held at the mouth

Player holds trumpet at his mouth, makes small instrument bobs, lifts slightly near3.5s, then settles.

12 paired keys and 121 frames at24fps. Native Quick, Draw! key 6590023216398336; stroke IDs and original point counts retained. Explicit extra strokes and held scene objects keep their own source credits.

Fresh still review v3: native identity met; source framing/pose not met. The drawn hand shapes sit below and toward the mouthpiece side of the valve cluster rather than enclosing and pressing the valves as in the source. The trumpet reaches the mouth, but the sampled playing grip is not represented at the valve position. Recognition classifier, audited final mask fit, four verified contacts and actual normal-speed playback remain unrun or unmet. No training ran.

Trace recall 0.99597747; all pieces kept 1.0. Trace gate passes. Both technical verifiers pass: decoded movie/key image agreement and independent raw-video/PTS/viewport source pairing. These checks do not approve motion. All reviewed/rejected candidates and raw verdicts are retained in revisions/ and review-v*.json; ledger is ledger.jsonl.

Reproduce with `python shots/trumpet/build_integrated.py --source /path/to/015d2d81-d328-592c-8b82-ed667cb5376c.mp4`. Source SHA and frozen input snapshots are retained. Quick, Draw! contributors / Google Creative Lab, CC BY4.0. No training ran.
