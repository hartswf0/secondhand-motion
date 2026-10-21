# Cow: the cow chews toward us

Current review copy: `integrated-v2`. Open `index.html` for the source/cartoon comparison and ten exact source-key pairs. 84 frames at24fps,3.5seconds. Independent review passes original-doodle identity and sampled source framing/pose. Filled-rig/SAM fit remains below its mean threshold. Normal-speed motion approval and recognition remain unrun. No training ran.

The real Quick, Draw! design is key5459491900358656, credited to Quick, Draw! contributors / Google Creative Lab, CC BY4.0. All17original stroke IDs and original point counts are retained in every editable cast frame. Separate semantic mappings carry the head, eyes, ears, muzzle and mouth mark. Lower body strokes remain assigned but the source close-up crops most of them. This is authored vector adaptation, not a photographed silhouette outline.

The archive source is *Triple Goodness*(1948), clip1f60b8f5-a603-5713-b971-a95ca6401d04. Raw clip-relative interval1.5–5seconds; film-relative interval1313.38–1316.88seconds. The source film and declared public-domain status are attributed in source.json; independent rights verification has not run. SourceSHA256783ccd872a3c2f6ecc4d16b954bf2bb004a3b29e3a1819af9c48bcea115b65be.

Observed keys follow the early head turn and later opening/closing jaw extrema. Jaw position, ear placement and poll/muzzle anchors were read on decoded source grids; intermediate poses use monotone cubic interpolation. Individual keys establish sampled correspondence, not natural continuous performance. The background sky and horizon are drawn once. The scene is source-aspect4:3, rendered480×360.

Current separate-character trace minimum recall0.999774,all pieces retained1.0. Filled-rig/SAM IoU mean0.625039,minimum0.562980; mean bar0.65 FAILS. SAM snapshot commit44af07db8fe9559e69b56fb94f65aa9179aca08c, fixed hashes in sam/provenance.json; audit.jpg shows four inspected samples. Broad head/ears are selected; dark shoulders are ragged. Model-estimated IoU does not measure drawing fit or jaw correctness. CI resampling timestamps are approximate.

Independent reviews are preserved unedited. v1identity failed because the broad native muzzle was lost; bounded v2widens that same polygon beyond the head while retaining placement and chew states. v2individual still identity and source framing/pose pass. Its reviewer caught a stale last image on the paired board; boards were regenerated from final key PNGs after writers exited, and decoded movie keyframes are checked separately in movie-key-audit.json. The individual key pixels reviewed are unchanged. No fourth or hidden revision is implied. v1 remains under revisions/v1; the append-only ledger retains every reviewed candidate. The ledger has two reviewed visual candidates and one append-only verdict-scope correction. The raw critic overall bar remains false; passing still components do not imply animated approval. All decisions remain rejected because applicable constraints are failed or unknown.

Rebuild from the exact original source bytes and committed SAM JSON:

```sh
python shots/cow/build_integrated.py --source /path/to/1f60b8f5-a603-5713-b971-a95ca6401d04.mp4
python shots/cow/finalize_integrated.py
python shots/cow/build_integrated_page.py
python shots/cow/audit_integrated.py
```

Optional `--mask-cache /path/to/cow-cache` imports the same pinned clip/track JSON. Renderer checks both source and snapshot hashes, uses a unique temporary directory, verifies all decoded frames before atomic movie installation, then generates paired boards after rendering completes. Rejected snapshots and review JSONs are not overwritten by this procedure. The review metadata must be re-evaluated if pixels change. No classifier inference, independent normal-speed playback approval, or training ran. Zero measured planted intervals is explicitly a failed foot-slide gate, not a no-contact pass. No accepted training pairs are exported.
