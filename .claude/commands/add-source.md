Add a new content source to the Screen Time Saver configuration.

The user will describe what they want to follow. Parse their request and:

1. Read the current `config.yaml` (or `config.example.yaml` if no config.yaml exists).

2. Determine the platform and parameters:
   - **YouTube channel**: platform `youtube`, needs `channel_url` (e.g. `https://www.youtube.com/@ChannelName`)
   - **RSS feed**: platform `rss`, needs `feed_url`
   - **Twitter/X account**: platform `twitter`, needs `handle` (without the @)

3. Add the new source entry to the `sources` list in `config.yaml`.

4. Validate the updated config:
```bash
screen-time-saver validate --config config.yaml
```

5. Confirm what was added.

User's request: $ARGUMENTS
