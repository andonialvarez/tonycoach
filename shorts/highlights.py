from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PlatformCopy(BaseModel):
    title: str
    caption: str
    hashtags: list[str]


class Highlight(BaseModel):
    start: float
    end: float
    hook: str          # texto corto en pantalla los primeros segundos
    reason: str        # por qué funciona (para tu revisión)
    score: int         # 1-10, potencial viral estimado
    youtube: PlatformCopy
    instagram: PlatformCopy
    tiktok: PlatformCopy


class HighlightList(BaseModel):
    clips: list[Highlight]


SYSTEM = """You are a senior short-form video editor for a Spanish-language coaching/motivation \
channel that publishes authorized clips of long-form coaching videos.

You receive a timestamped transcript. Pick the best self-contained moments for TikTok, \
Instagram Reels and YouTube Shorts.

What makes a good clip:
- The first 2 seconds hook the viewer (a bold claim, a question, a surprising statement). \
Start exactly where that hook begins, not on filler.
- One complete idea with a clear payoff; it must make sense with no prior context.
- It ends on a strong line, never mid-sentence.
- Prefer concrete advice, stories, and quotable lines over generic talk.

Rules:
- Use only segment boundaries from the transcript for start and end (in seconds).
- Clips must not overlap.
- Write all titles, captions, hooks and hashtags in {language}.
- hook: max 7 words, punchy, shown on screen.
- Titles: max 70 characters. Captions: 1-3 short sentences that add your own angle or takeaway. \
Do not credit the creator yourself; credits are added automatically.
- Hashtags: 3-6 per platform, without the '#' character, relevant and not spammy.
- score: honest 1-10 estimate of viral potential."""


def format_transcript(transcript: dict[str, Any]) -> str:
    return "\n".join(f"[{s['start']:.2f}-{s['end']:.2f}] {s['text']}" for s in transcript["segments"])


def select_highlights(transcript: dict[str, Any], *, title: str, n: int, min_s: float, max_s: float,
                      language: str = "es", model: str = "claude-opus-5-5",
                      effort: str = "medium") -> list[Highlight]:
    import anthropic

    client = anthropic.Anthropic()
    user = (f"Video title: {title}\n"
            f"Pick up to {n} clips, each between {min_s:.0f} and {max_s:.0f} seconds long.\n\n"
            f"Transcript:\n{format_transcript(transcript)}")
    response = client.messages.parse(
        model=model,
        max_tokens=16000,
        output_config={"effort": effort},
        system=SYSTEM.format(language=language),
        messages=[{"role": "user", "content": user}],
        output_format=HighlightList,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"El modelo rechazó la petición: {response.stop_details}")
    return clean_highlights(response.parsed_output.clips, transcript, min_s=min_s, max_s=max_s, n=n)


def _snap(t: float, bounds: list[float]) -> float:
    return min(bounds, key=lambda b: abs(b - t)) if bounds else t


def clean_highlights(clips: list[Highlight], transcript: dict[str, Any], *, min_s: float, max_s: float,
                     n: int) -> list[Highlight]:
    """Ajusta a los límites de frase, descarta duraciones fuera de rango y solapes."""
    segs = transcript["segments"]
    starts = [s["start"] for s in segs]
    ends = [s["end"] for s in segs]
    tolerance = 3.0
    kept: list[Highlight] = []
    for c in sorted(clips, key=lambda c: -c.score):
        start, end = _snap(c.start, starts), _snap(c.end, ends)
        dur = end - start
        if dur < min_s - tolerance:
            continue
        if dur > max_s:  # recorta al último final de frase que quepa
            fitting = [e for e in ends if start + min_s <= e <= start + max_s]
            if not fitting:
                continue
            end = max(fitting)
        if any(start < k.end and end > k.start for k in kept):
            continue
        kept.append(c.model_copy(update={"start": start, "end": end}))
        if len(kept) >= n:
            break
    return sorted(kept, key=lambda c: c.start)
