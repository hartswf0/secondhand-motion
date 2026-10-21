# Cloud bank billows

A cropped bank of cloud keeps the original four angular strokes while its three lobe heights follow the observed time-lapse. The bottom boundary stays below the frame rather than inventing a floating closed cloud.

Final third-round source right-lobe repair awaiting fresh review. No normal-speed playback or classifier approval; no training ran.

Reproduce with `python tools/integrated_batch.py --subject cloud --config shots/cloud/integrated/config.json --source /path/to/raw.mp4`. Inputs are frozen under input/ and the source hash is pinned. The raw source remains external.

Native topology: True. Native first-stroke IDs and point counts retained. Extra strokes are explicitly credited in compatibility.json. Camera/scenery remain separate from native cast. No SAM silhouette is used as a cel.

Linear vector interpolation is a baseline, not an approved performance. Recognition, final mask fit, material contacts and normal-speed playback require separate evidence. Still-image approval cannot make a training pair eligible. No training ran.
