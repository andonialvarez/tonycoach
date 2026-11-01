"""CSV para "Importar CSV" del Planificador de Metricool (formato de Mtr_plantilla_calendario.csv)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

HEADER = (
    "Text;Date;Time;Draft;Facebook;Twitter/X;LinkedIn;GBP;Instagram;Pinterest;TikTok;Youtube;Threads;Bluesky;"
    "Picture Url 1;Picture Url 2;Picture Url 3;Picture Url 4;Picture Url 5;Picture Url 6;Picture Url 7;"
    "Picture Url 8;Picture Url 9;Picture Url 10;Alt text picture 1;Alt text picture 2;Alt text picture 3;"
    "Alt text picture 4;Alt text picture 5;Alt text picture 6;Alt text picture 7;Alt text picture 8;"
    "Alt text picture 9;Alt text picture 10;Document title;Shortener;Video Thumbnail Url;Video Cover Frame;"
    "Twitter/X Can reply;Twitter/X Type;Twitter/X Poll Duration minutes;Twitter/X Poll Option 1;"
    "Twitter/X Poll Option 2;Twitter/X Poll Option 3;Twitter/X Poll Option 4;Pinterest Board;Pinterest Pin Title;"
    "Pinterest Pin Link;Pinterest Pin New Format;Pinterest AI generated content;Pinterest AI generated person;"
    "Instagram Post Type;Instagram Show Reel On Feed;Instagram Trial Reel Share Automatically;Youtube Video Title;"
    "Youtube Video Type;Youtube Video Privacy;Youtube video for kids;Youtube AI generated content;"
    "Youtube notify subscribers;Youtube Video Category;Youtube Video Tags;Youtube playlist;GBP Post Type;"
    "Facebook Post Type;Facebook Title;First Comment Text;TikTok Title;TikTok disable comments;TikTok disable duet;"
    "TikTok disable stitch;TikTok Post Privacy;TikTok Branded Content;TikTok Your Brand;TikTok Auto Add Music;"
    "TikTok Photo Cover Index;TikTok musicId;TikTok music title;TikTok music author;TikTok music previewUrl;"
    "TikTok music thumbnailUrl;TikTok music soundVolume;TikTok music originalVolume;TikTok music startMillis;"
    "TikTok music endMillis;TikTok Ai generated content;LinkedIn Type;LinkedIn Poll Question;LinkedIn Poll Option 1;"
    "LinkedIn Poll Option 2;LinkedIn Poll Option 3;LinkedIn Poll Option 4;LinkedIn Poll Duration;"
    "LinkedIn Show link preview;LinkedIn Images as Carousel;Threads Reply Control;Threads Is Spoiler;"
    "Threads Post Type;Brand name"
).split(";")

NETWORK_COLUMN = {"tiktok": "TikTok", "instagram": "Instagram", "youtube": "Youtube"}
FLAG_COLUMNS = ["Facebook", "Twitter/X", "LinkedIn", "GBP", "Instagram", "Pinterest", "TikTok", "Youtube",
                "Threads", "Bluesky"]


def post_text(clip: dict[str, Any], platform: str) -> tuple[str, str]:
    copy = clip["copy"][platform]
    tags = " ".join(f"#{h.lstrip('#')}" for h in copy["hashtags"])
    if platform == "youtube" and "#shorts" not in tags.lower():
        tags = (tags + " #shorts").strip()
    text = f"{copy['caption']}\n\n{clip['credit_text']}\n\n{tags}".strip()
    return copy["title"], text


def build_row(clip: dict[str, Any], platform: str, when: datetime, *, media_url: str, draft: bool,
              brand: str = "") -> dict[str, Any]:
    title, text = post_text(clip, platform)
    row: dict[str, Any] = {col: "" for col in HEADER}
    row.update({"Text": text, "Date": when.strftime("%Y-%m-%d"), "Time": when.strftime("%H:%M:%S"),
                "Draft": draft, "Picture Url 1": media_url, "Brand name": brand})
    for col in FLAG_COLUMNS:
        row[col] = col == NETWORK_COLUMN[platform]
    if platform == "instagram":
        row.update({"Instagram Post Type": "REEL", "Instagram Show Reel On Feed": True,
                    "Instagram Trial Reel Share Automatically": False})
    elif platform == "tiktok":
        row.update({"TikTok disable comments": False, "TikTok disable duet": False,
                    "TikTok disable stitch": False, "TikTok Post Privacy": "PUBLIC_TO_EVERYONE",
                    "TikTok Branded Content": False, "TikTok Your Brand": False,
                    "TikTok Auto Add Music": False, "TikTok Ai generated content": False})
    elif platform == "youtube":
        row.update({"Youtube Video Title": title[:100], "Youtube Video Type": "SHORT",
                    "Youtube Video Privacy": "PUBLIC", "Youtube video for kids": False,
                    "Youtube AI generated content": False, "Youtube notify subscribers": True,
                    "Youtube Video Category": "PEOPLE_BLOGS",
                    "Youtube Video Tags": ",".join(clip["copy"][platform]["hashtags"])})
    return row


def _cell(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value == "":
        return ""
    return '"' + str(value).replace('"', '""') + '"'


def export_csv(posts: list[dict[str, Any]], clips: dict[str, dict[str, Any]], cfg: dict[str, Any],
               out_path: Path) -> Path:
    """Una fila por publicación (clip + red), separador ';', UTF-8 con BOM, como la plantilla de Metricool."""
    mcfg = cfg.get("metricool", {})
    base = (mcfg.get("media_base_url") or "").rstrip("/")
    draft = bool(mcfg.get("draft", False))
    brand = mcfg.get("brand_name") or ""
    lines = [";".join(HEADER)]
    for p in posts:
        clip = clips[p["clip_id"]]
        media = f"{base}/{Path(clip['file']).name}" if base else ""
        row = build_row(clip, p["platform"], datetime.fromisoformat(p["when"]), media_url=media, draft=draft,
                        brand=brand)
        lines.append(";".join(_cell(row[c]) for c in HEADER))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8-sig", newline="")
    return out_path
