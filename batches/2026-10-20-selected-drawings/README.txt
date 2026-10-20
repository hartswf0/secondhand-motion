CARTOON ARCHIVE: SELECTED DRAWINGS AND REPAIRS

Open index.html. Choose a subject to see the source excerpt beside its four held
drawings, plus original QuickDraw identity, still-key review and provenance.

FIRST CURATED SET
Rabbit, duck, horse, dog, cat, butterfly, bicycle, windmill, helicopter, giraffe.
40 selected key drawings: 36 newly selected in this run and 4 carried giraffe keys.
Nine new subjects required 19 image-generation passes (76 candidate key drawings).
Each new subject was independently reviewed, repaired and reviewed again with
fresh context. Butterfly needed a third pass. All ten selected sets passed their
STILL-KEY bar; timing, transitions and continuous motion have no independent
playback approval. This is a drawing milestone, not finished inbetween animation.

Selection was a GPT visual judgment from temporal samples of 24 downloaded
candidate clips, not an exhaustive best-of-archive ranking. The earlier dataset
contains 345 categories and many unverified search candidates. Those are not all
drawn here. Explicit intervals exclude mixed-species cuts and dissolve frames.

ACTUAL REPAIR POLICY
The source photographs and selected actual doodle were supplied to built-in
image generation. Each review named a bounded cause; GPT made the corresponding
edit request and retained all candidates and exact prompts. No RL weights,
SAM, CLIP, V-JEPA or learned inbetweening model were trained or run. Agent search
is executed here; policy training is not. data/repair-ledger.jsonl contains the
19 real draw/review records, with train_eligible=false throughout. The carried
giraffe checkpoint is explicitly separate from the new-call count.

Inspect reviews/ for independent timed still evidence. The code ledger checks
declared evidence; it cannot authenticate a critic or evaluate image quality.
Drawing acceptance never supplies evidence for continuous motion acceptance.

REPRODUCE
Python 3, numpy, Pillow, opencv-python-headless, and ffmpeg/ffprobe executables.
python build_gallery.py
This uses the included source excerpts when the original downloaded full clips
are absent. If originals remain at ../mia-quickdraw-dataset/<local_video_path>,
the excerpts are re-extracted from them with the declared clip-local interval.
python build_gallery.py --skip-video
Rebuilds images/gallery/payload while retaining current videos.
python loop.py select --ledger data/repair-ledger.jsonl
python verify.py

Artwork itself is nondeterministic to regenerate. Exact prompts and input images
are retained in each subjects/<name>/ folder; already-generated outputs allow
deterministic crop/exposure reconstruction. The held-key videos use twelve
frames/second delivery with no morph or crossfade. Preview thumbnails are six
frames/second and may be lower resolution; source photos retain full chosen size.

ATTRIBUTION / PROVENANCE
Quick, Draw! by Google Creative Lab / contributing drawers, CC BY 4.0:
https://github.com/googlecreativelab/quickdraw-dataset
https://creativecommons.org/licenses/by/4.0/
The original chosen vector record is design.json and its exact rendering design.png.
New generated drawings are adaptations, not original QuickDraw observations.
Moving Image Archive source URLs, film offsets, reported rights, original archive
URLs, clip IDs and original file hashes are retained in each source.json.
https://www.movingimagearchive.com/
Reported rights metadata is retained as source information, not an independent
project-wide rights determination. Some archive collections include mixed rights;
consult the specific source record before downstream reuse.

All selected drawings are synthetic training candidates. Their still-key reviews
are agent judgments with retained evidence, not independently measured motion
ground truth. Filmmakers/viewers still need to review the eventual performance.
