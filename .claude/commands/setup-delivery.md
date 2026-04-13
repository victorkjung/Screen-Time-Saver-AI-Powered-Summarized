Set up a delivery backend for Screen Time Saver so digests are automatically sent to you.

Ask the user which backend they want to configure:

## Twilio (phone call)
If the user wants phone call delivery:
1. They need: Twilio Account SID, Auth Token, a Twilio phone number, and their personal phone number
2. They also need a way to serve the MP3 publicly (ngrok, S3 bucket, or static host)
3. Update the `delivery.twilio` section in `config.yaml`:
   - Set `enabled: true`
   - Set `account_sid`, `auth_token`, `from_phone`, `to_phone`
   - Set `audio_base_url` if they have a public host
4. Recommend they set secrets as environment variables: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`

## Telegram (audio message)
If the user wants Telegram delivery:
1. They need to create a bot via @BotFather and get the bot token
2. They need their chat ID (can get it by messaging @userinfobot)
3. Update the `delivery.telegram` section in `config.yaml`:
   - Set `enabled: true`
   - Set `bot_token` and `chat_id`
4. Recommend they set the token as `TELEGRAM_BOT_TOKEN` env var

After configuration, validate:
```bash
screen-time-saver validate --config config.yaml
```

User's request: $ARGUMENTS
