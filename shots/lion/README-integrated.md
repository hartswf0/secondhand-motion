# Lion integrated review

Six source-paired keys and 19 rendered frames at 24 fps retain Quick, Draw! key 6643650639429632 and all six native strokes with their original point counts.

The selected artwork is the earlier independently identity-passing candidate in `revisions/v3`. Its sampled source pose still fails: the resting forepaws and low prone chest remain unclear. The third candidate improved that pose but failed native facial identity, so it remains preserved in `revisions/v4` rather than becoming the selected drawing. `selection.json` verifies that 60 restored artifacts and the dense geometry exactly match the selected snapshot. No fourth repair was made.

Open `integrated/index.html`. Rebuild with `python shots/lion/build_integrated.py --source /path/to/raw.mp4`. Archive IDs, URLs, reported rights, raw SHA-256 and decoded photograph timestamps remain in `integrated/source.json`; frozen vectors remain under `integrated/input`. Vector timing inherited from the legacy study remains approximate. The append-only ledger retains every proposal, independent verdict and selection.

Classifier, audited final mask fit, verified contacts and actual normal-speed playback remain unmet or unrun. This is a review copy, not an accepted training pair. No training ran.
