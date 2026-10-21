# Van turns across the yard

Passenger van drives left across the yard, changes from three-quarter to side view, and shrinks as the camera pulls back; interval excludes the later foreground pole overlap.

Fresh identity and source-pose critique pending; classifier and normal-speed playback unrun. Review copy, no training ran.

Reproduce with `python tools/integrated_batch.py --subject van --config shots/van/integrated/config.json --source /path/to/raw.mp4`. Inputs are frozen under input/ and the source hash is pinned. The raw source remains external.

Native topology: True. Native first-stroke IDs and point counts retained. Extra strokes are explicitly credited in compatibility.json. Camera/scenery remain separate from native cast. No SAM silhouette is used as a cel.

Linear vector interpolation is a baseline, not an approved performance. Recognition, final mask fit, material contacts and normal-speed playback require separate evidence. Still-image approval cannot make a training pair eligible. No training ran.
