# Sailboat coming alongside

Review candidate from the first continuous approach in **Dordrecht (1926)**, clip `4c3c2e00-a804-5f5a-a743-66e58774123a`, clip-relative 3–9 seconds. The original four-stroke Quick, Draw! sailboat is key `5193394433294336`, credited to Quick, Draw! contributors / Google Creative Lab, CC BY 4.0. Reported archive rights are public domain; the source record retains the archive/original links.

Nine source-paired keys, 145 frames at 24 fps, editable native strokes in every timeline frame. The four original strokes keep the native single sail to the left of a near-upright mast, through observed hull, central-mast and left-sail anchors. The source also has a broad right-hand jib, which this one-sail doodle does not represent. That source-to-drawing mismatch is retained explicitly; no extra native sail is invented. The distant-vessel plate is drawn once and receives measured screen drift. That drift is a camera proxy which does not prove distant vessels are stationary. The trailing dinghy is separately source-keyed and drawn by agent. Reflection is an approximation through held water gaps. No invented sail flutter or rotation.

Open `index.html` for the cartoon, source and synchronized comparison. Exact decoded source frame indices/times are recorded beside nominal 24 fps sample times. `source-contact-sheet.jpg` contains 16 samples of the retained continuous interval; `whole-source-contact-sheet.jpg` contains 24 samples of the complete clip, including the excluded title and later cut.

Rebuild:

```sh
python shots/sailboat/build_integrated.py --source /path/to/archive-clip.mp4 --mask-cache /path/to/pinned-sailboat-snapshot
python shots/sailboat/build_integrated_page.py
```

Without `--mask-cache`, the renderer uses the committed `integrated/sam` JSON. It decodes the source interval once, uses a unique temporary directory, fully decodes each encoded movie, then installs finalized media atomically. The source file is not included. Its exact SHA256 is recorded in `source.json`.

`assembly-checks.json`, `mask-fit.json` and `traced.json` report actual measured checks. SAM is pinned to branch `wave2-track/sailboat`, commit `e9dd70601b9540492132b8e7906343bfba65070a`. Model IoU estimates are not measured drawing fit. The final inspected mask omits part of the hull, and thin rigging is approximate. The numeric filled sail/hull overlap therefore measures agreement with a partial model target, not ground truth.

Fresh reviews are retained verbatim. Still approval cannot supply motion approval. Recognition and independent normal-speed viewing are unrun; zero observed planted intervals do not pass the four-interval foot-contact gate. No training ran. These are not accepted training pairs.

Final third review: original doodle identity passes, but source pose does not, because the source's substantial right-hand sail is missing. Adding a second sail would change the selected native drawing. The three-round cap is reached; this source/design mismatch is retained rather than silently replacing the doodle. T1 passes at minimum recall 0.98330/all parts 1.0. Filled native boat/SAM overlap fails its mean bar at 0.61101 (minimum 0.54689). No motion approval or training eligibility.
