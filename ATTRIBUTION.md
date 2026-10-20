# Attribution and rights

**Quick, Draw! dataset**: Google Creative Lab and the people who drew, licensed
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
<https://github.com/googlecreativelab/quickdraw-dataset>. Drawings derived from a specific
Quick, Draw! record name its `key_id`. New drawings (agent-drawn or image-model keys) are
adaptations and are labelled as such; they are not Quick, Draw! observations.

**Moving Image Archive**: <https://www.movingimagearchive.com/>. The archive describes its holdings
as public-domain footage. Each clip keeps its source id, interval, archive URL and reported rights
(`dataset/clips.csv`, and `source.json` in each subject folder). Reported rights are source metadata,
not an independent rights determination; some collections are mixed. Check the source record before
reuse.

**Models run** (no weights are included): SAM 2.1 (`onnx-community/sam2.1-hiera-small-ONNX`),
Grounding DINO (`onnx-community/grounding-dino-tiny-ONNX`), CLIP, and the Quick, Draw! classifier
`Xenova/quickdraw-mobilevit-small`, each under its own license.

The look-lane batch has its own README with full provenance:
`batches/2026-10-20-selected-drawings/README.txt`.
