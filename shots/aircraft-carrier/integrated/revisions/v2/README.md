# Aircraft carrier turns past the bow

Five native strokes describe deck and hull. Island, parked aircraft and crew are absent from this sparse source drawing; no new technical detail is invented.

Bounded v2 after blind review: existing deck endpoints now begin receding upper right and finish upper left; existing lower-rail points retain their small irregular steps. Fresh independent review pending; no motion approval or training.

Reproduce with `python tools/integrated_batch.py --subject aircraft-carrier --config shots/aircraft-carrier/integrated/config.json --source /path/to/raw.mp4`. Inputs are frozen under input/ and the source hash is pinned. The raw source remains external.

Native topology: True. Native first-stroke IDs and point counts retained. Extra strokes are explicitly credited in compatibility.json. Camera/scenery remain separate from native cast. No SAM silhouette is used as a cel.

Linear vector interpolation is a baseline, not an approved performance. Recognition, final mask fit, material contacts and normal-speed playback require separate evidence. Still-image approval cannot make a training pair eligible. No training ran.
