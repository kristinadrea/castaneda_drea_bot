# Castaneda Quotes Telegram Bot

Python bot that posts the next quote from `quotes.txt` with the next media item to a Telegram channel. Quotes and media move in order and loop back to the beginning after the last item.

## Local Setup

1. Create a bot with BotFather and add it as an admin to your Telegram channel.
2. Copy `.env.example` to `.env`.
3. Fill in your real values in `.env`:
   - `BOT_TOKEN`
   - `CHANNEL_ID`
   - `ADMIN_USER_ID`
   - `DATA_DIR=data`
   - `MEDIA_URLS_FILE=media_urls.txt`
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
- `media_urls.txt` can store public Cloudflare R2 media URLs, one URL per line. If this file exists and contains URLs, the bot uses it instead of `images/`.
- `media_urls.example.txt` shows the expected format.
- `books/` can hold local source books for quote extraction. Book files are ignored by Git.
- `data/` stores local runtime progress and settings. It is ignored by Git.
- `.env` stores secrets and is ignored by Git.
- `.env.example` is safe to commit.

## Cloudflare R2 Media

Recommended setup for large media collections:

1. Create an R2 bucket in Cloudflare, for example `castaneda-images`.
2. Upload generated images, gifs, or videos to the bucket.
3. Enable public access for the bucket, or connect a public custom domain.
4. Create `media_urls.txt` in this project.
5. Add one public media URL per line, in the exact order you want the bot to use.

Example:

```text
https://pub-example.r2.dev/0001.png
https://pub-example.r2.dev/0002.png
https://pub-example.r2.dev/0003.png
```

Supported URL extensions:

```text
.jpg .jpeg .png .webp .gif .mp4 .mov .m4v .webm
```

If `media_urls.txt` is missing or empty, the bot falls back to local files from `images/`.

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
MEDIA_URLS_FILE=media_urls.txt
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
