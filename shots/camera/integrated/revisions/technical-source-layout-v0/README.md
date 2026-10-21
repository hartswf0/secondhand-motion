# Camera holds on its lens

Four native strokes keep the box camera and concentric lens. Source is a severe close crop; source controls become separately credited held scene marks. Camera action is a near-hold with slight registration changes, not invented lens spin.

Integrated review candidate. Independent source-pose and native-identity checks pending; normal-speed motion and classifier unrun. Legacy mask almostwholecroppedcamera, notlens-only; no measured drawingfit.

Reproduce with `python tools/integrated_batch.py --subject camera --config shots/camera/integrated/config.json --source /path/to/raw.mp4`. Inputs are frozen under input/ and the source hash is pinned. The raw source remains external.

Native topology: True. Native first-stroke IDs and point counts retained. Extra strokes are explicitly credited in compatibility.json. Camera/scenery remain separate from native cast. No SAM silhouette is used as a cel.

Linear vector interpolation is a baseline, not an approved performance. Recognition, final mask fit, material contacts and normal-speed playback require separate evidence. Still-image approval cannot make a training pair eligible. No training ran.
