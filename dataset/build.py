"""Assemble the Quick-Draw x Moving Image Archive dataset from exported browser chunks.

Usage: python3 build.py OUTDIR chunk1.txt [chunk2.txt ...]
Each chunk file is a tool-result dump: JSON list of {type,text}; text holds a
JSON string literal of [[category, [clip,...]], ...] followed by a footer.
"""
import csv, json, sys, statistics
from pathlib import Path

SITE = "https://www.movingimagearchive.com"


def load_chunk(path):
    blob = json.load(open(path))
    if blob and isinstance(blob[0], list):
        return blob
    text = "".join(b["text"] for b in blob if b.get("type") == "text").lstrip()
    inner, _ = json.JSONDecoder().raw_decode(text)
    return json.loads(inner) if isinstance(inner, str) else inner


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    order = [c.strip() for c in open(Path(__file__).with_name("categories.txt")) if c.strip()]
    data = {}
    for p in sys.argv[2:]:
        for cat, clips in load_chunk(p):
            data[cat] = clips
    queries = {c: c for c in order}
    alt_path = Path(__file__).with_name("alt_results.json")
    if alt_path.exists():
        for cat, v in json.load(open(alt_path)).items():
            data[cat] = v["clips"]; queries[cat] = v["q"]

    fields = ["category", "query_used", "rank", "score", "clip_id", "source_title", "source_year",
              "source_slug", "start_seconds", "end_seconds", "duration_seconds",
              "match_timestamp_seconds", "color_mode", "aspect_ratio",
              "video_url", "thumbnail_url", "page_url", "download_url"]
    rows, summary = [], []
    for cat in order:
        clips = data.get(cat, [])
        seen = set()
        kept = []
        for c in clips:
            if c["id"] in seen:
                continue
            seen.add(c["id"]); kept.append(c)
        for i, c in enumerate(kept, 1):
            rows.append({
                "category": cat, "query_used": queries[cat], "rank": i, "score": c.get("score"),
                "clip_id": c["id"], "source_title": c.get("sourceTitle"),
                "source_year": c.get("sourceYear"), "source_slug": c.get("sourceSlug"),
                "start_seconds": round(c.get("startSeconds") or 0, 3),
                "end_seconds": round(c.get("endSeconds") or 0, 3),
                "duration_seconds": round(c.get("durationSeconds") or 0, 3),
                "match_timestamp_seconds": c.get("matchTimestampSeconds"),
                "color_mode": c.get("colorMode"), "aspect_ratio": c.get("aspectRatio"),
                "video_url": c.get("videoUrl"), "thumbnail_url": c.get("thumbnailUrl"),
                "page_url": f"{SITE}/sources/{c.get('sourceSlug')}?clip={c['id']}",
                "download_url": f"{SITE}/api/clips/{c['id']}/download",
            })
        scores = [c.get("score") or 0 for c in kept]
        top10 = scores[:10]
        summary.append({"category": cat, "query_used": queries[cat], "clips": len(kept),
                        "top_score": max(scores) if scores else None,
                        "mean_score": round(statistics.mean(scores), 4) if scores else None,
                        "sources": len({c.get("sourceId") for c in kept}),
                        "top10_score_spread": round(max(top10) - min(top10), 4) if top10 else None})

    with open(out / "clips.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    with open(out / "clips.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out / "categories.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)

    missing = [s["category"] for s in summary if s["clips"] == 0]
    uniq = len({r["clip_id"] for r in rows})
    print(json.dumps({"categories": len(order), "with_clips": len(order) - len(missing),
                      "missing": missing, "rows": len(rows), "unique_clips": uniq}, indent=1))


if __name__ == "__main__":
    main()
