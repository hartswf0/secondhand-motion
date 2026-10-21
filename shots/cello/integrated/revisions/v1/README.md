# Cello bow crosses the strings

Five native cello strokes preserve body, neck, strings and fholes. Agent-drawn bow and moving hand are separately credited; instrument and lower bow remain cropped like source. The simplified held player edges do not assert a full-body performance reconstruction.

Integrated review candidate. Independent source-pose and native-identity checks pending; normal-speed motion and classifier unrun. LegacySAMselectsperson/head/torso, notinstrument; invalidcellofittarget. Bowandfingercontactsnotverified.

Reproduce with `python tools/integrated_batch.py --subject cello --config shots/cello/integrated/config.json --source /path/to/raw.mp4`. Inputs are frozen under input/ and the source hash is pinned. The raw source remains external.

Native topology: True. Native first-stroke IDs and point counts retained. Extra strokes are explicitly credited in compatibility.json. Camera/scenery remain separate from native cast. No SAM silhouette is used as a cel.

Linear vector interpolation is a baseline, not an approved performance. Recognition, final mask fit, material contacts and normal-speed playback require separate evidence. Still-image approval cannot make a training pair eligible. No training ran.
