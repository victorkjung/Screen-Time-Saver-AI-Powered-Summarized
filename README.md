# Screen Time Saver

**AI-powered social media summariser** — turn 90 minutes of doomscrolling into a 10-minute podcast.

Define the creators and platforms you care about. Screen Time Saver fetches their latest content, sends it through Claude for an intelligent summary, and produces:

- An **MP3 audio digest** you can listen to while walking, driving, or doing chores
- **SRT captions** ready for video highlights or podcast clips
- A **timestamped transcript** for quick scanning
- **Markdown show notes** for podcast descriptions or YouTube uploads

## How it works

```
config.yaml
    |
    v
Fetch content          (YouTube transcripts, RSS feeds, Twitter/X posts)
    |
    v
Claude AI summary      (one coherent narrative, not disjointed bullet points)
    |
    v
edge-tts audio         (free, high-quality text-to-speech)
    |
    v
Output files           (MP3 + SRT captions + transcript + show notes)
```

## Quick start

### 1. Install

```bash
pip install -e .
```

### 2. Configure

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml`:
- Set your `anthropic_api_key` (or export `ANTHROPIC_API_KEY` as an env var)
- Add the YouTube channels, RSS feeds, and Twitter accounts you follow

### 3. Run

```bash
# Generate a full podcast-style audio digest
screen-time-saver generate

# Text-only (skip audio generation)
screen-time-saver generate --no-audio

# Use a different summarisation style
screen-time-saver generate --style briefing

# Validate your config without running
screen-time-saver validate

# List available TTS voices
screen-time-saver list-voices
```

## Configuration

See [`config.example.yaml`](config.example.yaml) for the full annotated config.

### Supported platforms

| Platform | How it works | Requirements |
|----------|-------------|--------------|
| **YouTube** | Extracts video transcripts via yt-dlp | None (no API key needed) |
| **RSS** | Parses any standard RSS/Atom feed | Feed URL |
| **Twitter/X** | Uses Nitter RSS bridge for public profiles | None (no login needed) |

### Summarisation styles

| Style | Description |
|-------|-------------|
| `podcast` | Conversational, engaging narration with transitions and sign-offs |
| `newsletter` | Clean, scannable text with bullet points and headlines |
| `briefing` | Ultra-concise executive summary — just the signal |

### Output files

All files are written to the configured `output.directory` (default: `./output/`):

| File | Description |
|------|-------------|
| `digest.mp3` | Audio narration of the full digest |
| `captions.srt` | Subtitle file for video editing |
| `transcript.txt` | Timestamped plain-text transcript |
| `show_notes.md` | Markdown show notes with source links |

## Use cases

- **Doctor-ordered screen time reduction**: Get the essence of your feed without opening any apps
- **Podcast creation**: Use the MP3 + show notes as a ready-to-publish podcast episode
- **Video highlights**: Import the MP3 and SRT into a video editor for captioned highlight reels
- **Commute listening**: Listen to your daily digest via text-to-speech while driving
- **Creator support**: The show notes link back to original content so you can engage with the posts that matter

## Tech stack

- **[Claude API](https://docs.anthropic.com/)** — intelligent, context-aware summarisation
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — YouTube transcript extraction
- **[edge-tts](https://github.com/rany2/edge-tts)** — free, high-quality text-to-speech with word-level timing
- **[feedparser](https://github.com/kurtmckee/feedparser)** — RSS/Atom feed parsing
- **[Typer](https://typer.tiangolo.com/)** — CLI framework
- **[Pydantic](https://docs.pydantic.dev/)** — configuration validation

## License

Apache 2.0 — see [LICENSE](LICENSE).
