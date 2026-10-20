# Pig turns into the closeup

Assembled review candidate: 47 frames at 24 fps, 6 integrated vector keys, synchronized source/cartoon player. Open `index.html`. The third independent review passes drawing identity and broad composition; the late head still reads as profile rather than turning toward the camera. **Source head-turn repair pending; motion unapproved.**

The 10-stroke Quick, Draw! pig is key 5298401904164864, with its compact spiral snout, paired angular ears and five dangling leg strokes. The source rump stays cropped at right; the close foreground feet leave the bottom edge. The scene is one held fence, panel and yard drawing.

## Rebuild

Download the `video_url` in `../source.json` to a local file outside the repository. From the repository root:

```bash
python shots/pig/build_integrated.py --source /path/to/pig.mp4
python shots/pig/build_integrated_page.py
```

Python dependencies: OpenCV, NumPy, SciPy, Pillow, CairoSVG and scikit-image. ffmpeg with libx264 must be on PATH. The renderer verifies source SHA-256, renders in an isolated temporary folder, validates video decoding and atomically installs each video. `--mask-cache` optionally supplies another directory containing `clip.json` and `track.json`; the default uses the retained `source-masks/` snapshot.

## Evidence and limits

`source-masks/` preserves SAM2.1/DINO output, branch commit and hashes. The overlap in `mask-fit.json` compares a **filled rig envelope** (body/head cels plus 13 px source-space limb envelopes) against SAM. It is a geometric proxy, not rendered cartoon pixel coverage, segmentation model confidence, or independent pose approval. Mean 0.7220/minimum 0.6469 over 23 nominal 12 fps source times. ffmpeg sampling can differ by a source frame.

`traced.json` measures six separated character exports using `tools/trace_keys.py`: recall at least 0.9933, every ink piece retained. Far legs sit behind the torso cel. A consistent native topology drives every rendered frame.

`revisions/v1/` and `revisions/v2/` preserve rejected attempts; the three `review-v*.json` files are unedited blind verdicts. All three proposals remain rejected in the append-only ledger. The source head-turn gate still fails. The recognition classifier and normal-speed playback review did not run. Four planted intervals were not verified, so no foot-slide pass is claimed. No training ran. No acceptance or training-eligible pair is claimed.

Quick, Draw! contributors / Google Creative Lab, CC BY 4.0. Archive source ID, interval and unverified reported rights stay in `../source.json` and `shot.json`.
