# Speedboat leap and landing

Boat emerges into view, pitches bow-up in flight, levels, drops bow-first and lands with spray, then flattens on the water.

Fresh still review v2: native identity not met; source framing/pose not met. After landing, keys 8–12 add a huge closed triangular shape rising from the left bow across the deck. It reads as a mast/sail attached to the boat, changing the original low speedboat silhouette. In the source the landing spray rises behind the boat toward the right, not as a rigid triangle rooted at the bow. Recognition classifier, audited final mask fit, four verified contacts and actual normal-speed playback remain unrun or unmet. No training ran.

Reproduce with `python tools/integrated_batch.py --subject speedboat --config shots/speedboat/integrated/config.json --source /path/to/raw.mp4`. Inputs are frozen under input/ and the source hash is pinned. The raw source remains external.

Native topology: True. Native first-stroke IDs and point counts retained. Extra strokes are explicitly credited in compatibility.json. Camera/scenery remain separate from native cast. No SAM silhouette is used as a cel.

Linear vector interpolation is a baseline, not an approved performance. Recognition, final mask fit, material contacts and normal-speed playback require separate evidence. Still-image approval cannot make a training pair eligible. No training ran.
