# Source / mask / drawing inspector

Open `index.html`. Choose a subject and scrub the 593 archived CI samples across thirteen subjects. The source and red SAM overlay show the same image; the drawing seeks to the nearest recorded source time. Use Next checked to jump among the 52 manually inspected mask samples. These notes distinguish plausible masks, merged instances and wrong targets, including high-confidence tree/building mistakes and a final fan sample from the next cooking shot. That sample is blocked from drawing pairing. Only those listed samples were reviewed. Each sample has a bookmarkable hash such as `#pig/11`.

The snapshots are pinned by commit and SHA-256 in each `data/<subject>/provenance.json`. RLE masks alternate zero and one runs in row-major order. `clip.json` records their 12 fps resampling and interval. Times are approximate: the CI did not retain decoded source PTS or the source video hash. The fan boundary check confirms why a timestamp alone is insufficient. Model IoU estimates are not drawing-fit scores. The see-saw mask combines multiple boards.

Rebuild offline from the checked-in snapshots and current assemblies:

```sh
python tools/build_segmentation_review.py
```

`tools/build_wave2_pages.py` also refreshes this inspector. `--cache` can import another complete snapshot after its branch and content hashes are checked. These review copies are not accepted training pairs. No training ran.
