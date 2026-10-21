# Trumpet held at the mouth

Player holds trumpet at his mouth, makes small instrument bobs, lifts slightly near3.5s, then settles.

Fresh still review v1: native identity met; source framing/pose not met. The horn’s bell occupies far too much vertical space and hangs well below the supporting hand; the source bell is a small opening on a slender horn aimed left and slightly down from the player’s mouth. This changes the sampled playing pose despite the similar horizontal placement. Recognition classifier, audited final mask fit, four verified contacts and actual normal-speed playback remain unrun or unmet. No training ran.

Reproduce with `python tools/integrated_batch.py --subject trumpet --config shots/trumpet/integrated/config.json --source /path/to/raw.mp4`. Inputs are frozen under input/ and the source hash is pinned. The raw source remains external.

Native topology: True. Native first-stroke IDs and point counts retained. Extra strokes are explicitly credited in compatibility.json. Camera/scenery remain separate from native cast. No SAM silhouette is used as a cel.

Linear vector interpolation is a baseline, not an approved performance. Recognition, final mask fit, material contacts and normal-speed playback require separate evidence. Still-image approval cannot make a training pair eligible. No training ran.
