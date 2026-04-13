"""Text-to-speech generation using edge-tts (free Microsoft TTS).

Produces an MP3 audio file **and** sentence-level timing metadata that
feeds directly into SRT caption generation.
"""

from __future__ import annotations

import logging
from pathlib import Path

import edge_tts

from screen_time_saver.config import OutputConfig
from screen_time_saver.models import TimestampedSegment

log = logging.getLogger(__name__)

# edge-tts reports timing in 100-nanosecond units.
_TICKS_PER_MS = 10_000


async def generate_audio(
    script: str,
    config: OutputConfig,
) -> tuple[Path, list[TimestampedSegment]]:
    """Generate an MP3 from *script* and return ``(audio_path, segments)``.

    *segments* contains sentence-level timing information suitable for
    building SRT captions.
    """
    out_dir = Path(config.directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_path = out_dir / f"digest.{config.audio_format}"

    communicate = edge_tts.Communicate(
        text=script,
        voice=config.voice,
        rate=config.speech_rate,
    )

    segments: list[TimestampedSegment] = []
    audio_chunks: list[bytes] = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            # Collect word boundaries; we'll merge them into sentence-level
            # segments below.
            offset_ms = chunk["offset"] // _TICKS_PER_MS
            duration_ms = chunk["duration"] // _TICKS_PER_MS
            segments.append(
                TimestampedSegment(
                    start_ms=offset_ms,
                    end_ms=offset_ms + duration_ms,
                    text=chunk["text"],
                )
            )

    # Write audio.
    audio_path.write_bytes(b"".join(audio_chunks))
    log.info("Audio written to %s", audio_path)

    # Merge word-level segments into sentence-level blocks (~10-15 words each).
    merged = _merge_segments(segments, max_words=12)

    # Rough duration check.
    if audio_chunks:
        approx_seconds = len(b"".join(audio_chunks)) / 32_000  # ~256 kbps mp3
        approx_minutes = approx_seconds / 60
        if approx_minutes > config.max_audio_minutes:
            log.warning(
                "Generated audio is ~%.1f min (limit %d min). "
                "Consider reducing content in config.",
                approx_minutes,
                config.max_audio_minutes,
            )

    return audio_path, merged


def _merge_segments(
    segments: list[TimestampedSegment],
    max_words: int = 12,
) -> list[TimestampedSegment]:
    """Group word-level segments into subtitle-friendly blocks."""
    if not segments:
        return []

    merged: list[TimestampedSegment] = []
    buf_start = segments[0].start_ms
    buf_words: list[str] = []
    buf_end = segments[0].end_ms

    for seg in segments:
        buf_words.append(seg.text)
        buf_end = seg.end_ms

        # Split on sentence-ending punctuation or when we hit max_words.
        if (
            seg.text.endswith((".", "!", "?", ":", ";"))
            or len(buf_words) >= max_words
        ):
            merged.append(
                TimestampedSegment(
                    start_ms=buf_start,
                    end_ms=buf_end,
                    text=" ".join(buf_words),
                )
            )
            buf_words = []
            buf_start = buf_end

    # Flush remaining words.
    if buf_words:
        merged.append(
            TimestampedSegment(
                start_ms=buf_start,
                end_ms=buf_end,
                text=" ".join(buf_words),
            )
        )

    return merged


async def list_voices(language: str = "en") -> list[dict]:
    """Return available edge-tts voices filtered by *language* prefix."""
    voices = await edge_tts.list_voices()
    return [v for v in voices if v.get("Locale", "").startswith(language)]
