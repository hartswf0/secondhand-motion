# Speedboat leap and landing

Boat emerges into view, pitches bow-up in flight, levels, drops bow-first and lands with spray, then flattens on the water.

Fresh still review v1: native identity met; source framing/pose not met. The landing is reduced to a clean hull with tiny wake ticks. The source’s tall impact splash and broad trailing spray, which dominate the late samples and identify the landing/skid event, are missing. Recognition classifier, audited final mask fit, four verified contacts and actual normal-speed playback remain unrun or unmet. No training ran.

Reproduce with `python tools/integrated_batch.py --subject speedboat --config shots/speedboat/integrated/config.json --source /path/to/raw.mp4`. Inputs are frozen under input/ and the source hash is pinned. The raw source remains external.

Native topology: True. Native first-stroke IDs and point counts retained. Extra strokes are explicitly credited in compatibility.json. Camera/scenery remain separate from native cast. No SAM silhouette is used as a cel.

Linear vector interpolation is a baseline, not an approved performance. Recognition, final mask fit, material contacts and normal-speed playback require separate evidence. Still-image approval cannot make a training pair eligible. No training ran.
