from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

NETWORK_NAMES = {"tiktok": "TikTok", "instagram": "Instagram", "youtube": "YouTube"}


def post_text(clip: dict[str, Any], platform: str) -> tuple[str, str]:
    copy = clip["copy"][platform]
    tags = " ".join(f"#{h.lstrip('#')}" for h in copy["hashtags"])
    text = f"{copy['caption']}\n\n{clip['credit_text']}\n\n{tags}".strip()
    if platform == "youtube" and "#shorts" not in tags.lower():
        text += " #shorts"
    return copy["title"], text


def export_csv(posts: list[dict[str, Any]], clips: dict[str, dict[str, Any]], cfg: dict[str, Any],
               out_path: Path) -> Path:
    mcfg = cfg.get("metricool", {})
    cols = mcfg.get("columns", {})
    base = (mcfg.get("media_base_url") or "").rstrip("/")
    names = [cols.get(k, k) for k in ("text", "date", "time", "network", "media", "title")]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(names)
        for p in posts:
            clip = clips[p["clip_id"]]
            title, text = post_text(clip, p["platform"])
            when = datetime.fromisoformat(p["when"])
            media = f"{base}/{Path(clip['file']).name}" if base else str(Path(clip["file"]).resolve())
            w.writerow([text, when.strftime("%Y-%m-%d"), when.strftime("%H:%M"),
                        NETWORK_NAMES[p["platform"]], media, title])
    return out_path
