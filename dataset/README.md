# Quick, Draw! categories × Moving Image Archive

Archival film shots matched to the 345 Quick, Draw! categories, collected from
movingimagearchive.com on 2026-10-20. The archive describes its holdings as
public-domain footage, free to reuse.

## How it was collected

Each category name was sent to the archive's own shot search (`POST /api/search`),
which ranks individual shots with an OpenCLIP image-text model. The first two
result pages were kept: up to 48 shots per category, ranked by the archive's
similarity score. No filters on color or aspect ratio.

Eight categories returned a degenerate result for the bare word: every top hit
had the same score and the images were unrelated. They were re-run with a short
descriptive phrase, recorded in `query_used`:

| category | query used |
|---|---|
| picture frame | a framed picture hanging on a wall |
| pillow | a pillow on a bed |
| pineapple | a pineapple fruit |
| pool | people swimming in a swimming pool |
| rainbow | a rainbow in the sky |
| shoe | a shoe |
| soccer ball | kicking a soccer ball |
| squiggle | a wavy squiggly line |

## Files

- `clips.csv` / `clips.jsonl`: one row per (category, shot), 16,042 rows. The same shot can
  appear under more than one category (10,757 unique shots from 1,459 source films).
- `categories.csv`: one row per category with clip count, top and mean score,
  number of distinct source films, and `top10_score_spread`.

### clips columns

| column | meaning |
|---|---|
| category | Quick, Draw! category |
| query_used | text sent to the search |
| rank | 1 = best match within the category |
| score | archive's OpenCLIP similarity (higher = closer) |
| clip_id | archive shot id |
| source_title, source_year, source_slug | the film the shot comes from (year missing for ~15%) |
| start_seconds, end_seconds, duration_seconds | shot position within the source film |
| match_timestamp_seconds | frame inside the shot that matched best |
| color_mode, aspect_ratio | as reported by the archive |
| video_url | direct MP4 of the shot |
| thumbnail_url | JPG still |
| page_url | the shot's page on the site |
| download_url | the site's own download endpoint for the shot |

## Quality notes

- Concrete, photographable things (animals, vehicles, buildings, tools) match well.
  Shapes, body parts and rare objects are weaker; check thumbnails before use.
- Scores are only comparable within a category, not across categories.
- A `top10_score_spread` near zero means the search returned near-identical scores,
  which in this archive signals noise. After the eight re-runs above, no category is flagged.
- Videos were not downloaded; `video_url` points at the archive's file host.

## Rebuilding

`build.py` (in the source folder) turns the raw search responses into these files.
