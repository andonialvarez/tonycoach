from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from shorts.creators import Creator, match_creator, require_permission
from shorts.highlights import Highlight, PlatformCopy, clean_highlights
from shorts.metricool import export_csv
from shorts.render import build_ffmpeg_cmd, crop_x
from shorts.schedule import assign_slots, parse_days
from shorts.subtitles import ass_time, build_ass, group_words, words_in_range

import pytest

TZ = "Europe/Madrid"


def _transcript():
    segs = []
    t = 0.0
    for i in range(30):
        words = [{"start": t + j * 0.5, "end": t + j * 0.5 + 0.4, "word": f"w{i}_{j}"} for j in range(8)]
        words[-1]["word"] += "."
        segs.append({"start": t, "end": t + 4.0, "text": " ".join(w["word"] for w in words), "words": words})
        t += 4.0
    return {"segments": segs, "duration": t}


def _hl(start, end, score=5):
    c = PlatformCopy(title="t", caption="c", hashtags=["coach"])
    return Highlight(start=start, end=end, hook="h", reason="r", score=score, youtube=c, instagram=c, tiktok=c)


def test_parse_days():
    assert parse_days("mon-fri") == {0, 1, 2, 3, 4}
    assert parse_days("sat-sun") == {5, 6}
    assert parse_days("mon,wed") == {0, 2}
    assert parse_days("fri-mon") == {4, 5, 6, 0}


def test_assign_slots_uses_next_free_slots():
    cfg = {"lead_minutes": 30, "tiktok": {"mon-fri": ["13:30", "20:30"]}, "youtube": {"daily": ["18:30"]}}
    now = datetime(2026, 11, 2, 12, 0, tzinfo=ZoneInfo(TZ))  # lunes
    taken = {"tiktok": {datetime(2026, 11, 2, 13, 30, tzinfo=ZoneInfo(TZ)).isoformat()}}
    posts = assign_slots(["a", "b"], cfg, TZ, taken, now=now)
    tt = [p for p in posts if p["platform"] == "tiktok"]
    assert [p["when"][:16] for p in tt] == ["2026-11-02T20:30", "2026-11-03T13:30"]
    yt = [p for p in posts if p["platform"] == "youtube"]
    assert [p["when"][:16] for p in yt] == ["2026-11-02T18:30", "2026-11-03T18:30"]


def test_clean_highlights_snaps_and_drops_overlaps():
    tr = _transcript()
    clips = [_hl(1.0, 31.5, score=9), _hl(10.0, 40.0, score=8), _hl(60.0, 62.0), _hl(36.0, 116.0, score=6)]
    out = clean_highlights(clips, tr, min_s=20, max_s=59, n=4)
    # 2º solapa con el 1º, 3º es demasiado corto, 4º se recorta a 59 s en un final de frase
    assert [(c.start, c.end) for c in out] == [(0.0, 32.0), (36.0, 92.0)]


def test_subtitle_grouping_and_ass():
    words = words_in_range(_transcript(), 4.0, 12.0)
    assert words[0]["start"] == 0.0
    groups = group_words(words, per_line=3)
    assert all(len(g) <= 3 for g in groups)
    assert groups[0][-1]["word"] != groups[1][0]["word"]
    ass = build_ass(words, duration=8.0, style={"highlight_color": "00FFFF"}, hook="Gancho", credit="@coach")
    assert "Style: Sub" in ass and "GANCHO" in ass and "@coach" in ass
    assert "{\\c&H00FFFF&}" in ass
    assert ass_time(65.5) == "0:01:05.50"


def test_crop_follows_face_and_clamps():
    assert crop_x(1920, 1080, None) == (606, 657)
    assert crop_x(1920, 1080, 0.0) == (606, 0)
    assert crop_x(1920, 1080, 1.0) == (606, 1314)


def test_ffmpeg_cmd_vertical_source_is_padded():
    cmd = build_ffmpeg_cmd(Path("in.mp4"), Path("o.mp4"), Path("o.ass"), 1, 31, 1080, 1920, None)
    assert "pad=1080:1920" in cmd[cmd.index("-vf") + 1]


def test_creator_permission():
    cs = [Creator("Coach", "@coach", "https://www.youtube.com/@Coach", permission=False)]
    c = match_creator(cs, uploader_id="@coach")
    assert c is cs[0]
    with pytest.raises(PermissionError):
        require_permission(c, "x")
    with pytest.raises(PermissionError):
        require_permission(match_creator(cs, uploader_id="@other"), "x")


def test_metricool_csv(tmp_path):
    clip = {"file": "/x/a-01.mp4", "credit_text": "Créditos",
            "copy": {"youtube": {"title": "T", "caption": "C", "hashtags": ["coach"]}}}
    cfg = {"metricool": {"media_base_url": "https://cdn.example/clips/"}}
    path = export_csv([{"clip_id": "a", "platform": "youtube", "when": "2026-11-02T18:30:00+01:00"}],
                      {"a": clip}, cfg, tmp_path / "o.csv")
    text = path.read_text(encoding="utf-8-sig")
    assert "2026-11-02,18:30,YouTube,https://cdn.example/clips/a-01.mp4,T" in text
    assert "#shorts" in text
