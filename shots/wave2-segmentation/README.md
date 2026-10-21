# Source / mask / drawing inspector

Open `index.html`. Scrub 1,638 archived segmentation samples across 41 subjects. Source and overlay always show the same image; the drawing seeks to its nearest recorded source time. The 164 manually inspected samples have bookmarkable agent notes and a Next checked control. These checks distinguish subject masks, merged instances, wrong targets and shot boundaries; they do not approve drawings or motion.

The first 16 subjects retain binary RLE snapshots from pinned SAM 2.1 CI exports. The new 25 expose **filled contour proxies** from earlier SAM 2.1 polygon exports. Those exports simplified boundaries and discarded small components, so their original binary masks cannot be recovered. The proxy label stays visible in the inspector. Cellist and trumpet-player masks, for example, cannot measure instrument fit. Original polygon/meta hashes and source paths remain in each provenance record.

For 28 subjects, `alignment.json` compares sampled images with a retained raw video. Of 1,045 compared samples, 889 pass fixed low-error and uniqueness checks. Pairing uses those estimated appearance correspondences where usable and otherwise keeps nominal export times. This does not recover missing original segmentation input hashes or decode PTS, validate masks, or establish material motion. Each correspondence pins its sample image and track bytes. The remaining 13 subjects use approximate nominal clocks.

Known unusable samples are blocked from pairing, including the final fan cooking shot, carrier dissolve and speedboat sample before entry. A failed, invalid or unmeasured final drawing/mask gate stays distinct from model-reported IoU confidence. All review copies remain train-ineligible; no training ran.

Rebuild offline from checked-in data and current assemblies:

```sh
python tools/build_segmentation_review.py
```

To import a legacy polygon export (this does not rerun SAM):

```sh
python tools/prepare_legacy_masks.py frog
```

To reproduce an appearance comparison (raw video remains external):

```sh
python tools/align_sam_samples.py --source /path/raw.mp4 --cache shots/wave2-segmentation/data/frog --output shots/wave2-segmentation/data/frog/alignment.json
```

`tools/build_wave2_pages.py` also refreshes the inspector. `--cache` can import pinned binary snapshots after provenance checks. Mask arrays alternate zero and one runs in row-major order.
