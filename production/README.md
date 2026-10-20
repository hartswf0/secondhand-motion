# Production workbench

Open [index.html](index.html) directly or through GitHub Pages. Its catalog and 206 photographic/first-pass preview assets are embedded, so it works without a server. Repaired drawings, source keys and comparison clips link to the existing selected-drawings batch. Those canonical files are reused, not duplicated here.

The 100-clip pool covers 100 categories and 91 source films: 10 existing still-key sets, 79 thumbnail-curated candidates and 11 metadata candidates. This is a review pool, not a best-100 quality ranking. No continuous motion is approved by this workbench. The full-body giraffe motion study and the giraffe head-key set use different clip IDs and remain separate.

| Scope | Existing drawings | New pose keys planned | New breakdowns planned | Total target |
|---|---:|---:|---:|---:|
| Current 10 clips | 40 | 39 | 24 | 103 |
| 100 clips at the same complexity mix | 40 | 750 | 240 | 1,030 |

The 100-clip row is an extrapolation, not an individually measured budget for the provisional 90. The 66 new source-reference photographs represent 39 proposed pose keys, 24 proposed breakdowns and 3 procedural checks. They are photographs awaiting drawing. No additional cartoon drawings were authored by this integration.

## What runs

The viewer is a read-only snapshot. Copy agent job copies a review brief; it does not launch workers. `data/queue-snapshot.json` records two actual source-review completions, with no live-worker claim. It has no lease tokens.

The local SQLite coordinator uses seven coarse roles to organize work. The repository's [13 pipeline stages](../PIPELINE.md) and [agent quality gates](../AGENTS.md) remain the production contract. Completing a coordinator job does not independently verify those gates or supersede them. A supervisor must inspect evidence and preserve the existing thresholds. No training ran.

From this directory:

```sh
python3 scripts/queue.py init --db /tmp/secondhand-motion.sqlite
python3 scripts/queue.py seed --db /tmp/secondhand-motion.sqlite --manifest data/candidates-100.json
python3 scripts/queue.py claim --db /tmp/secondhand-motion.sqlite --worker source-01 --role source_reviewer
python3 scripts/test_queue.py
python3 tools/build_viewer.py
python3 tools/verify_integration.py
```

Queue operation requires only Python's standard library. Image verification additionally uses Pillow. See [agent contracts](docs/agent-contracts.txt) and [job schema](schema/job.schema.json) for roles, result formats, expiring leases, three attempts per stage and two repairs per candidate. Authors cannot approve their own drawing or motion outputs. A fresh queue starts every candidate unreviewed; historical reviews are not silently replayed.

## Records

- `data/catalog.json`: viewer metadata; `data/embedded-images.json`: source-photo and first-pass preview assets, keyed by logical asset name. The builder combines them into the offline page.
- `data/candidates-100.json`: source IDs, archive URLs, retrieval provenance and selection limits. Full videos for the 90 provisional candidates remain external.
- `data/frame-plan.json` and `docs/frame-budget.txt`: timing suggestions and authoring allowances.
- `data/source-reference-extractions.json`: target/decoded source-frame times. Logical source-image keys resolve through `embedded-images.json`.
- `reviews/` and `contact-sheets/source-worker-*-temporal.jpg`: actual limited still-sample source reviews. They do not assert playback inspection.
- `data/review-portability.json`: historical path mappings. Canonical prior art is now under `../batches/2026-10-20-selected-drawings/subjects/<category>/`.

The 100-clip pool supplements `../data/subject_queue.json`. It does not replace that category queue, change wave 2, or turn its `done` flag into motion approval. Preserve Quick, Draw! CC BY 4.0 attribution and the archive's reported rights/provenance; see [ATTRIBUTION.md](../ATTRIBUTION.md).
