from __future__ import annotations

from typing import Any

PUNCT_BREAK = (".", "?", "!", ",", ";", ":")


def words_in_range(transcript: dict[str, Any], start: float, end: float) -> list[dict[str, Any]]:
    """Palabras del clip con tiempos relativos al inicio del clip."""
    out = []
    for seg in transcript["segments"]:
        for w in seg.get("words", []):
            if w["start"] >= start - 0.05 and w["end"] <= end + 0.3:
                out.append({"start": max(0.0, w["start"] - start), "end": min(end, w["end"]) - start,
                            "word": w["word"]})
    return out


def group_words(words: list[dict[str, Any]], per_line: int, max_gap: float = 0.6) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = []
    for w in words:
        if cur and (len(cur) >= per_line or w["start"] - cur[-1]["end"] > max_gap
                    or cur[-1]["word"].endswith(PUNCT_BREAK)):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", " ")


def build_ass(words: list[dict[str, Any]], *, duration: float, style: dict[str, Any], hook: str = "",
              credit: str = "") -> str:
    font = style.get("font", "Arial")
    size = int(style.get("font_size", 80))
    per_line = int(style.get("words_per_line", 3))
    upper = bool(style.get("uppercase", True))
    hl = style.get("highlight_color", "00FFFF")
    margin = int(style.get("margin_bottom", 520))
    hook_s = float(style.get("hook_seconds", 3))

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,2,60,60,{margin},1
Style: Hook,{font},{int(size * 0.85)},&H00FFFFFF,&H00FFFFFF,&H00000000,&HB4000000,-1,0,0,0,100,100,0,0,3,18,0,8,80,80,260,1
Style: Credit,{font},{int(size * 0.45)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,3,1,8,60,60,140,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    if credit:
        lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(duration)},Credit,,0,0,0,,{_esc(credit)}")
    if hook:
        hook_text = hook.upper() if upper else hook
        lines.append(f"Dialogue: 2,{ass_time(0)},{ass_time(min(hook_s, duration))},Hook,,0,0,0,,{_esc(hook_text)}")

    for group in group_words(words, per_line):
        texts = [(w["word"].upper() if upper else w["word"]) for w in group]
        for i, w in enumerate(group):
            start = w["start"]
            end = group[i + 1]["start"] if i + 1 < len(group) else max(w["end"], start + 0.2)
            parts = [f"{{\\c&H{hl}&}}{_esc(t)}{{\\c&HFFFFFF&}}" if j == i else _esc(t)
                     for j, t in enumerate(texts)]
            lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Sub,,0,0,0,,{' '.join(parts)}")
    return header + "\n".join(lines) + "\n"
