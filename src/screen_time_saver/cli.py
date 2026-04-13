"""Typer CLI — the main entry point for Screen Time Saver."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

import typer

from screen_time_saver.config import load_config

app = typer.Typer(
    name="screen-time-saver",
    help="AI-powered social media summariser — "
    "turn hours of scrolling into a 10-minute podcast.",
    add_completion=False,
)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(levelname)s  %(name)s  %(message)s",
        level=level,
    )


# ── generate ──────────────────────────────────────────────────────


async def _run_generate(
    config_path: Path,
    output_dir: Optional[str],
    no_audio: bool,
    style: Optional[str],
    verbose: bool,
) -> None:
    _setup_logging(verbose)
    log = logging.getLogger("screen_time_saver")

    # 1. Load config.
    cfg = load_config(config_path)
    if output_dir:
        cfg.output.directory = output_dir
    if style:
        cfg.summarizer.style = style  # type: ignore[assignment]

    # 2. Fetch content from all sources concurrently.
    from screen_time_saver.fetchers import get_fetcher
    from screen_time_saver.models import ContentItem

    async def _fetch_one(src) -> list[ContentItem]:
        fetcher = get_fetcher(src.platform)
        try:
            return await fetcher.fetch(src)
        except Exception:
            log.error("Fetcher failed for %s", src.name, exc_info=True)
            return []

    tasks = [_fetch_one(src) for src in cfg.sources]
    results = await asyncio.gather(*tasks)
    items: list[ContentItem] = [item for batch in results for item in batch]

    log.info("Fetched %d content items from %d sources", len(items), len(cfg.sources))

    if not items:
        typer.echo("No content fetched — nothing to summarise.")
        raise typer.Exit(1)

    # 3. Summarise with Claude.
    from screen_time_saver.summarizer import summarize_content

    typer.echo("Summarising content with Claude…")
    digest = await summarize_content(items, cfg.summarizer, cfg.anthropic_api_key)
    typer.echo(f"Digest: {digest.title}  ({digest.estimated_read_minutes:.1f} min read)")

    out = Path(cfg.output.directory)
    out.mkdir(parents=True, exist_ok=True)

    # 4. Generate audio (unless --no-audio).
    from screen_time_saver.models import TimestampedSegment

    segments: list[TimestampedSegment] = []
    if no_audio:
        typer.echo("Skipping audio generation (--no-audio).")
    else:
        from screen_time_saver.audio import generate_audio

        typer.echo("Generating audio…")
        audio_path, segments = await generate_audio(digest.full_script, cfg.output)
        typer.echo(f"Audio saved to {audio_path}")

    # 5. Write output files.
    from screen_time_saver.output import (
        generate_show_notes,
        generate_srt,
        generate_transcript,
    )

    if segments:
        srt_path = generate_srt(segments, out / "captions.srt")
        typer.echo(f"Captions saved to {srt_path}")

    transcript_path = generate_transcript(digest, segments, out / "transcript.txt")
    typer.echo(f"Transcript saved to {transcript_path}")

    notes_path = generate_show_notes(digest, out / "show_notes.md")
    typer.echo(f"Show notes saved to {notes_path}")

    typer.echo("\nDone!  Your screen-time-saving digest is ready.")


@app.command()
def generate(
    config: Path = typer.Option(
        Path("config.yaml"),
        "--config",
        "-c",
        help="Path to YAML configuration file.",
    ),
    output_dir: Optional[str] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Override the output directory from config.",
    ),
    no_audio: bool = typer.Option(
        False,
        "--no-audio",
        help="Skip TTS audio generation (text outputs only).",
    ),
    style: Optional[str] = typer.Option(
        None,
        "--style",
        "-s",
        help="Override summarisation style: podcast, newsletter, or briefing.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
) -> None:
    """Fetch, summarise, and narrate your social media feeds."""
    asyncio.run(_run_generate(config, output_dir, no_audio, style, verbose))


# ── list-voices ───────────────────────────────────────────────────


@app.command("list-voices")
def list_voices_cmd(
    language: str = typer.Option("en", "--lang", "-l", help="Language prefix filter."),
) -> None:
    """List available TTS voices for edge-tts."""

    async def _list() -> None:
        from screen_time_saver.audio import list_voices

        voices = await list_voices(language)
        for v in voices:
            typer.echo(f"  {v['ShortName']:40s}  {v.get('Gender', '')}")

    typer.echo(f"Available '{language}' voices:\n")
    asyncio.run(_list())


# ── validate ──────────────────────────────────────────────────────


@app.command()
def validate(
    config: Path = typer.Option(
        Path("config.yaml"),
        "--config",
        "-c",
        help="Path to YAML configuration file.",
    ),
) -> None:
    """Validate the configuration file without running anything."""
    try:
        cfg = load_config(config)
    except Exception as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo("Configuration is valid.\n")
    typer.echo(f"  API key: {'*' * 8}…{cfg.anthropic_api_key[-4:]}")
    typer.echo(f"  Sources: {len(cfg.sources)}")
    for src in cfg.sources:
        typer.echo(f"    - {src.name} ({src.platform}, max {src.max_items} items)")
    typer.echo(f"  Model:   {cfg.summarizer.model}")
    typer.echo(f"  Style:   {cfg.summarizer.style}")
    typer.echo(f"  Voice:   {cfg.output.voice}")
    typer.echo(f"  Output:  {cfg.output.directory}")


if __name__ == "__main__":
    app()
