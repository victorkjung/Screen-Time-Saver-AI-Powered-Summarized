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
    |
    v
Deliver (optional)     (Twilio phone call or Telegram audio message)
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

### 3. Validate your config

```bash
screen-time-saver validate
```

Expected output:

```
Configuration is valid.

  API key: ********…abc1
  Sources: 5
    - 3Blue1Brown (youtube, max 3 items)
    - Fireship (youtube, max 5 items)
    - TechCrunch (rss, max 10 items)
    - Hacker News – Best (rss, max 10 items)
    - Elon Musk (twitter, max 5 items)
  Model:   claude-sonnet-4-20250514
  Style:   podcast
  Voice:   en-US-AndrewMultilingualNeural
  Output:  ./output
```

### 4. Generate your digest

```bash
# First run — text only (skips TTS, fastest way to verify everything works)
screen-time-saver generate --no-audio

# Full run — generates podcast MP3 + captions + transcript + show notes
screen-time-saver generate
```

### All CLI commands

```bash
# Generate a full podcast-style audio digest
screen-time-saver generate

# Text-only (skip audio — good for first-time smoke test)
screen-time-saver generate --no-audio

# Use a different summarisation style
screen-time-saver generate --style briefing

# Generate and deliver via Twilio call + Telegram
screen-time-saver generate --deliver

# Validate your config without running anything
screen-time-saver validate

# List available TTS voices
screen-time-saver list-voices
```

You can also run the CLI directly with Python if you prefer:

```bash
python -m screen_time_saver.cli validate
python -m screen_time_saver.cli generate --no-audio
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

## Delivery backends

Get your digest pushed to you instead of pulling it.

### Twilio — phone call

Your digest calls *you*. Twilio places an outbound call to your phone and plays the MP3 audio.

```bash
pip install -e ".[twilio]"
```

**Setup:**
1. Get a [Twilio account](https://www.twilio.com/) + phone number
2. Set `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` as environment variables
3. Host the MP3 somewhere Twilio can reach (S3, ngrok, or any public URL)
4. Enable in `config.yaml` under `delivery.twilio`

### Telegram — audio message

Receive the digest as a playable audio message in any Telegram chat or channel.

**Setup:**
1. Create a bot via [@BotFather](https://t.me/BotFather) and copy the token
2. Get your chat ID via [@userinfobot](https://t.me/userinfobot)
3. Set `TELEGRAM_BOT_TOKEN` as an environment variable
4. Enable in `config.yaml` under `delivery.telegram`

No extra pip install needed — Telegram delivery uses `aiohttp` (already a dependency).

## Claude Code skills

If you use [Claude Code](https://docs.anthropic.com/en/docs/claude-code), this project includes custom slash commands:

| Command | What it does |
|---------|-------------|
| `/digest` | Generate a full digest (with options for style, audio, delivery) |
| `/add-source` | Add a new YouTube/RSS/Twitter source to your config |
| `/setup-delivery` | Interactive Twilio or Telegram delivery setup |

These live in `.claude/commands/` and work automatically when Claude Code is run from the project root.

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
- **[Twilio](https://www.twilio.com/docs/voice)** — outbound phone calls (optional)
- **Telegram Bot API** — audio message delivery via aiohttp (no extra SDK)

## License

Apache 2.0 — see [LICENSE](LICENSE).
