# Three brooms sweep the floor

Seventeen native strokes describe the main straw broom. Two separately moving background brooms are preserved from the frozen source-observed scene, all native copies. The moving apron/operator is omitted, not treated as stationary extracted geometry.

Integrated review candidate. Independent source-pose and native-identity checks pending; normal-speed motion and classifier unrun. Legacy masks switch one/twobrooms, not stable threeinstanceunion; no measured drawingfit orverifiedbristlecontacts.

Reproduce with `python tools/integrated_batch.py --subject broom --config shots/broom/integrated/config.json --source /path/to/raw.mp4`. Inputs are frozen under input/ and the source hash is pinned. The raw source remains external.

Native topology: True. Native first-stroke IDs and point counts retained. Extra strokes are explicitly credited in compatibility.json. Camera/scenery remain separate from native cast. No SAM silhouette is used as a cel.

Linear vector interpolation is a baseline, not an approved performance. Recognition, final mask fit, material contacts and normal-speed playback require separate evidence. Still-image approval cannot make a training pair eligible. No training ran.
