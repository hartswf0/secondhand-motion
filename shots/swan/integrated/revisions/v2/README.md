# Swan neck dip and lift

Swan glides on the lake with its head held low and then lifts the curved neck near the end while the camera pans. Source and drawing share a fixed 2× viewport crop so the small bird can be inspected.

Fresh still review v1: native identity met; source framing/pose not met. The neck pose does not reproduce the source dip-and-rise: early keys hang a narrow head below the body, while the final keys retain a short forward hook instead of the source swan’s tall raised curved neck. Recognition classifier, audited final mask fit, four verified contacts and actual normal-speed playback remain unrun or unmet. No training ran.

Reproduce with `python tools/integrated_batch.py --subject swan --config shots/swan/integrated/config.json --source /path/to/raw.mp4`. Inputs are frozen under input/ and the source hash is pinned. The raw source remains external.

Native topology: True. Native first-stroke IDs and point counts retained. Extra strokes are explicitly credited in compatibility.json. Camera/scenery remain separate from native cast. No SAM silhouette is used as a cel.

Linear vector interpolation is a baseline, not an approved performance. Recognition, final mask fit, material contacts and normal-speed playback require separate evidence. Still-image approval cannot make a training pair eligible. No training ran.
