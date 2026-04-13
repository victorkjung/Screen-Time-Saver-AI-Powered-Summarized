#!/usr/bin/env python3
"""
Screen Time Saver — optional convenience launcher.

This is an alternative way to run the full pipeline without remembering
CLI flags.  The primary (and recommended) entry point is the installed CLI:

    pip install -e .
    cp config.example.yaml config.yaml
    screen-time-saver validate
    screen-time-saver generate

This file does the same thing as `screen-time-saver generate` but with
friendlier pre-flight checks and step-by-step progress output.  Use it
if you prefer `python app.py` over the CLI.
"""

import asyncio
import logging
import sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────
CONFIG_FILE = Path("config.yaml")
OUTPUT_DIR = Path("./output")


def main() -> None:
    logging.basicConfig(
        format="%(levelname)s  %(message)s",
        level=logging.INFO,
    )
    log = logging.getLogger("screen_time_saver")

    # ── Pre-flight checks ─────────────────────────────────────────
    if not CONFIG_FILE.exists():
        print()
        print("  No config.yaml found!")
        print()
        print("  Quick setup:")
        print("    1. cp config.example.yaml config.yaml")
        print("    2. Open config.yaml and set your ANTHROPIC_API_KEY")
        print("    3. Pick the YouTube channels / RSS feeds / Twitter accounts you follow")
        print("    4. screen-time-saver validate")
        print("    5. screen-time-saver generate")
        print()
        sys.exit(1)

    from screen_time_saver.config import load_config

    try:
        cfg = load_config(CONFIG_FILE)
    except Exception as exc:
        print(f"\n  Config error: {exc}\n")
        sys.exit(1)

    if not cfg.anthropic_api_key or cfg.anthropic_api_key.startswith("${"):
        print()
        print("  API key not set!")
        print("  Either edit config.yaml or:  export ANTHROPIC_API_KEY=sk-ant-...")
        print()
        sys.exit(1)

    # ── Run the pipeline ──────────────────────────────────────────
    asyncio.run(_pipeline(cfg, log))


async def _pipeline(cfg, log) -> None:
    from screen_time_saver.audio import generate_audio
    from screen_time_saver.delivery import deliver_digest
    from screen_time_saver.fetchers import get_fetcher
    from screen_time_saver.models import ContentItem, TimestampedSegment
    from screen_time_saver.output import (
        generate_show_notes,
        generate_srt,
        generate_transcript,
    )
    from screen_time_saver.summarizer import summarize_content

    # 1. Fetch
    print("\n  [1/4]  Fetching content from your sources...\n")

    async def _fetch_one(src) -> list[ContentItem]:
        fetcher = get_fetcher(src.platform)
        try:
            items = await fetcher.fetch(src)
            print(f"    {src.name:30s}  {len(items)} items")
            return items
        except Exception:
            log.error("  Failed: %s", src.name, exc_info=True)
            return []

    batches = await asyncio.gather(*[_fetch_one(s) for s in cfg.sources])
    items: list[ContentItem] = [i for batch in batches for i in batch]

    if not items:
        print("\n  Nothing fetched. Check your sources in config.yaml.\n")
        sys.exit(1)

    print(f"\n    Total: {len(items)} items from {len(cfg.sources)} sources")

    # 2. Summarise
    print("\n  [2/4]  Summarising with Claude AI...\n")
    digest = await summarize_content(items, cfg.summarizer, cfg.anthropic_api_key)
    print(f'    "{digest.title}"')
    print(f"    ~{digest.estimated_read_minutes:.0f} minute read")

    # 3. Generate audio + output files
    print("\n  [3/4]  Generating podcast audio...\n")

    out = Path(cfg.output.directory)
    out.mkdir(parents=True, exist_ok=True)

    audio_path, segments = await generate_audio(digest.full_script, cfg.output)
    print(f"    Audio:      {audio_path}")

    if segments:
        srt_path = generate_srt(segments, out / "captions.srt")
        print(f"    Captions:   {srt_path}")

    transcript_path = generate_transcript(digest, segments, out / "transcript.txt")
    print(f"    Transcript: {transcript_path}")

    notes_path = generate_show_notes(digest, out / "show_notes.md")
    print(f"    Show notes: {notes_path}")

    # 4. Deliver (if configured)
    has_delivery = cfg.delivery and (
        (cfg.delivery.twilio and cfg.delivery.twilio.enabled)
        or (cfg.delivery.telegram and cfg.delivery.telegram.enabled)
    )

    if has_delivery:
        print("\n  [4/4]  Delivering digest...\n")
        statuses = await deliver_digest(digest, audio_path, cfg.delivery)
        for s in statuses:
            print(f"    {s}")
    else:
        print("\n  [4/4]  Delivery: not configured (edit config.yaml to enable)")

    # ── Done ──────────────────────────────────────────────────────
    print()
    print("  ========================================")
    print("  All done!  Your digest is in ./output/")
    print()
    print("  Listen:  open output/digest.mp3")
    print("  Read:    open output/transcript.txt")
    print("  ========================================")
    print()


if __name__ == "__main__":
    main()
