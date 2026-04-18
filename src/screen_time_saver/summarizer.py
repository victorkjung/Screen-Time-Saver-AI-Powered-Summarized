"""Claude-powered content summarisation.

Makes a single API call with all fetched content so the AI can produce
a coherent, well-transitioned narrative rather than disjointed per-item
summaries.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import anthropic
import os

try:
    import openai as _openai_mod
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

from screen_time_saver.config import SummarizerConfig
from screen_time_saver.models import ContentItem, Digest, DigestSection

log = logging.getLogger(__name__)

# ── Style-specific system prompts ────────────────────────────────

_PODCAST_SYSTEM = """\
You are an expert podcast host producing a daily audio digest called \
"Screen Time Saver".  Your job is to turn raw social-media content into \
a natural, engaging, conversational script that a listener can enjoy \
while walking, driving, or doing chores.

Rules:
- Open with a brief, energetic intro ("Hey, welcome back to Screen Time Saver…").
- Transition smoothly between sources / topics.
- Close with a short sign-off.
- Keep the total script readable aloud in under {max_minutes} minutes \
  (roughly {max_words} words).
- Be informative but casual — not robotic, not overly hype.
"""

_NEWSLETTER_SYSTEM = """\
You are a skilled editor producing a concise daily newsletter called \
"Screen Time Saver".  Summarise the provided social-media content \
into a clean, scannable text digest.

Rules:
- Use short paragraphs and bullet points.
- One section per source, with a clear headline.
- Keep total length under {max_words} words.
"""

_BRIEFING_SYSTEM = """\
You are an executive assistant producing a crisp daily briefing called \
"Screen Time Saver".  Distil the provided social-media content into \
the most essential takeaways.

Rules:
- Maximum {max_words} words total.
- One section per source with a one-line headline and 2-3 bullet points.
- No filler, no pleasantries — just the signal.
"""

_STYLE_MAP = {
    "podcast": _PODCAST_SYSTEM,
    "newsletter": _NEWSLETTER_SYSTEM,
    "briefing": _BRIEFING_SYSTEM,
}

# ── JSON output schema (described in the prompt) ─────────────────

_JSON_SCHEMA_INSTRUCTIONS = """
Respond with a single JSON object matching this schema (no markdown fences):
{
  "title": "string — catchy digest title for today",
  "sections": [
    {
      "source_name": "string",
      "headline": "string — short punchy headline",
      "summary": "string — 2-4 sentence summary",
      "key_points": ["string", "..."],
      "source_url": "string — most relevant URL for this section"
    }
  ],
  "full_script": "string — the complete narration script for TTS",
  "estimated_read_minutes": number
}
"""

# ── Helpers ───────────────────────────────────────────────────────

_APPROX_CHARS_PER_TOKEN = 4
_MAX_CONTENT_TOKENS = 90_000  # leave room for system prompt + response


def _estimate_tokens(text: str) -> int:
    return len(text) // _APPROX_CHARS_PER_TOKEN


def _format_content(items: list[ContentItem]) -> str:
    """Build the user-message payload grouping items by source."""
    by_source: dict[str, list[ContentItem]] = {}
    for item in items:
        by_source.setdefault(item.source_name, []).append(item)

    parts: list[str] = []
    for source_name, source_items in by_source.items():
        parts.append(f"=== Source: {source_name} ===")
        for item in source_items:
            duration = ""
            if item.duration_seconds:
                m, s = divmod(item.duration_seconds, 60)
                duration = f" ({m}:{s:02d})"
            parts.append(f'--- {item.title}{duration} ---')
            parts.append(item.content_text or "(no text available)")
            parts.append("")  # blank line separator

    return "\n".join(parts)


def _truncate_items(items: list[ContentItem], max_tokens: int) -> list[ContentItem]:
    """Proportionally truncate the longest items to fit within *max_tokens*."""
    total = sum(_estimate_tokens(i.content_text) for i in items)
    if total <= max_tokens:
        return items

    ratio = max_tokens / total
    truncated: list[ContentItem] = []
    for item in items:
        max_chars = int(len(item.content_text) * ratio)
        new_text = item.content_text[:max_chars]
        if max_chars < len(item.content_text):
            new_text += "\n[… transcript truncated]"
        truncated.append(item.model_copy(update={"content_text": new_text}))
    return truncated


# ── Public API ────────────────────────────────────────────────────


async def summarize_content(
    items: list[ContentItem],
    config: SummarizerConfig,
    api_key: str,
) -> Digest:
    """Summarise all *items* into a single :class:`Digest` via Claude."""

    if not items:
        return Digest(
            title="No content today",
            sections=[],
            full_script="There was no new content to summarise today.",
            estimated_read_minutes=0,
        )

    items = _truncate_items(items, _MAX_CONTENT_TOKENS)
    user_content = _format_content(items)

    max_minutes = 10  # sensible default
    max_words = max_minutes * 150
    system_template = _STYLE_MAP.get(config.style, _PODCAST_SYSTEM)
    system_prompt = system_template.format(max_minutes=max_minutes, max_words=max_words)
    system_prompt += "\n\n" + _JSON_SCHEMA_INSTRUCTIONS

    log.info(
        "Sending %d items (~%d tokens) to Claude %s",
        len(items),
        _estimate_tokens(user_content),
        config.model,
    )

    # Use OpenAI if model starts with "gpt" or "o", otherwise Anthropic.
    _use_openai = config.model.startswith(("gpt", "o1", "o3", "o4"))

    if _use_openai and _HAS_OPENAI:
        oai_key = os.environ.get("OPENAI_API_KEY", "")
        oai_client = _openai_mod.OpenAI(api_key=oai_key)
        log.info("Using OpenAI model: %s", config.model)
        oai_resp = oai_client.chat.completions.create(
            model=config.model,
            max_tokens=config.max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        raw_text = oai_resp.choices[0].message.content
    else:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        raw_text = message.content[0].text

    # Strip markdown code fences if the model wrapped them.
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    data = json.loads(cleaned)

    sections = [DigestSection(**s) for s in data.get("sections", [])]
    return Digest(
        title=data.get("title", "Daily Digest"),
        generated_at=datetime.now(),
        sections=sections,
        full_script=data.get("full_script", ""),
        estimated_read_minutes=data.get("estimated_read_minutes", 0),
    )
