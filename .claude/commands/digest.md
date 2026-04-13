Generate an AI-powered social media digest using Screen Time Saver.

Run the following steps:

1. Check that `config.yaml` exists in the project root. If not, copy `config.example.yaml` to `config.yaml` and ask the user to configure their API key and sources.

2. Validate the configuration:
```bash
screen-time-saver validate
```

3. Generate the digest with the user's preferred options. Use the arguments provided by the user to determine flags:
   - Default: `screen-time-saver generate`
   - If the user says "no audio" or "text only": add `--no-audio`
   - If the user specifies a style (podcast/newsletter/briefing): add `--style <style>`
   - If the user says "deliver", "send", "call me", or "telegram": add `--deliver`
   - For a first-time smoke test, recommend: `screen-time-saver generate --no-audio`

```bash
screen-time-saver generate $USER_FLAGS
```

4. Report what was generated:
   - List the output files in `./output/`
   - If audio was generated, mention the MP3 file and its approximate duration
   - If delivery was requested, report the delivery status
   - Show a brief preview of the digest title and section headlines

User's request: $ARGUMENTS
