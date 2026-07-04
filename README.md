# Castaneda Quotes Telegram Bot

Python bot that posts the next quote from `quotes.txt` with the next media file from `images/` to a Telegram channel. Quotes and media move in order and loop back to the beginning after the last item.

## Local Setup

1. Create a bot with BotFather and add it as an admin to your Telegram channel.
2. Copy `.env.example` to `.env`.
3. Fill in your real values in `.env`:
   - `BOT_TOKEN`
   - `CHANNEL_ID`
   - `ADMIN_USER_ID`
   - `DATA_DIR=data`
4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run the bot:

```bash
python bot.py
```

## Files

- `quotes.txt` stores quote blocks separated by `---`.
- `images/` stores photos, gifs, and videos.
- `books/` can hold local source books for quote extraction. Book files are ignored by Git.
- `data/` stores local runtime progress and settings. It is ignored by Git.
- `.env` stores secrets and is ignored by Git.
- `.env.example` is safe to commit.

## Telegram Admin Commands

Only the Telegram user from `ADMIN_USER_ID` can use admin commands. The bot also clears the default command menu, so ordinary users should not see these commands in Telegram.

- `/status`
- `/post_on_start`
- `/daily`
- `/every3days`
- `/pause`
- `/resume`
- `/post_now`
- `/test`

## Render Deployment

Use a Render Background Worker.

Recommended environment variables:

```text
BOT_TOKEN=your_real_bot_token
CHANNEL_ID=-1001234567890
ADMIN_USER_ID=123456789
DATA_DIR=/opt/render/project/src/data
```

Add a Persistent Disk and mount it to the same path as `DATA_DIR` if you want progress and settings to survive redeploys and service restarts.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python bot.py
```

## Notes

Do not commit `.env`, `data/*.json`, `state*.json`, `settings*.json`, source book files, or backup files. They may contain private tokens, channel IDs, admin IDs, copyrighted text, or live posting progress.
