from __future__ import annotations

from datetime import datetime, timedelta, time
from typing import Any, Iterator
from zoneinfo import ZoneInfo

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
PLATFORMS = ("tiktok", "instagram", "youtube")


def parse_days(spec: str) -> set[int]:
    spec = spec.strip().lower()
    if spec in ("daily", "all", "*"):
        return set(range(7))
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = (DAYS.index(x.strip()) for x in part.split("-"))
            out.update(range(a, b + 1) if a <= b else [*range(a, 7), *range(0, b + 1)])
        else:
            out.add(DAYS.index(part))
    return out


def iter_slots(platform_cfg: dict[str, list[str]], after: datetime, tz: ZoneInfo,
               horizon_days: int = 60) -> Iterator[datetime]:
    rules = [(parse_days(days), sorted(times)) for days, times in platform_cfg.items()]
    day = after.astimezone(tz).date()
    for _ in range(horizon_days):
        wd = day.weekday()
        times = sorted({t for days, ts in rules if wd in days for t in ts})
        for t in times:
            hh, mm = (int(x) for x in t.split(":"))
            slot = datetime.combine(day, time(hh, mm), tzinfo=tz)
            if slot > after:
                yield slot
        day += timedelta(days=1)


def assign_slots(clip_ids: list[str], schedule_cfg: dict[str, Any], tz_name: str,
                 taken: dict[str, set[str]], now: datetime | None = None,
                 platforms: tuple[str, ...] = PLATFORMS) -> list[dict[str, str]]:
    """Asigna a cada clip la siguiente franja libre de cada plataforma, en orden."""
    tz = ZoneInfo(tz_name)
    now = now or datetime.now(tz)
    after = now + timedelta(minutes=int(schedule_cfg.get("lead_minutes", 30)))
    posts: list[dict[str, str]] = []
    for platform in platforms:
        if platform not in schedule_cfg:
            continue
        used = set(taken.get(platform, set()))
        slots = iter_slots(schedule_cfg[platform], after, tz)
        for clip_id in clip_ids:
            for slot in slots:
                iso = slot.isoformat()
                if iso not in used:
                    used.add(iso)
                    posts.append({"clip_id": clip_id, "platform": platform, "when": iso})
                    break
    return sorted(posts, key=lambda p: (p["when"], p["platform"]))
