# Oracle Operations

This file is a quick reminder for maintaining the bot on the Oracle Always Free VM.

## Server

```text
Host: 141.253.112.50
SSH user: opc
SSH key: secrets/oracle-drea.key
Project path: /opt/castaneda_drea_bot
Service: castaneda-drea-bot
```

## Update Bot Code On Oracle

First commit and push changes from the local project to GitHub:

```bash
git status
git add .
git commit -m "Describe your change"
git push
```

Then deploy the latest GitHub code to Oracle:

```bash
ssh -i secrets/oracle-drea.key opc@141.253.112.50 'cd /opt/castaneda_drea_bot && git pull && .venv/bin/pip install -r requirements.txt && sudo systemctl restart castaneda-drea-bot && sudo systemctl status castaneda-drea-bot --no-pager'
```

## Useful Server Commands

Open an SSH session:

```bash
ssh -i secrets/oracle-drea.key opc@141.253.112.50
```

Check bot status:

```bash
sudo systemctl status castaneda-drea-bot --no-pager
```

Restart bot:

```bash
sudo systemctl restart castaneda-drea-bot
```

Watch live logs:

```bash
sudo journalctl -u castaneda-drea-bot -f
```

Show recent logs:

```bash
sudo journalctl -u castaneda-drea-bot -n 100 --no-pager
```

## Add New Cloudflare R2 Images

1. Upload new files to the R2 bucket.
2. Keep object names simple and ordered, for example:

```text
castaneda_drea_bot/0001.png
castaneda_drea_bot/0002.png
castaneda_drea_bot/0003.jpg
```

3. Add public URLs to `media_urls.txt`, one URL per line:

```text
https://pub-f92c01de6856429eb1c05fbd6e81dd15.r2.dev/castaneda_drea_bot/0001.png
https://pub-f92c01de6856429eb1c05fbd6e81dd15.r2.dev/castaneda_drea_bot/0002.png
https://pub-f92c01de6856429eb1c05fbd6e81dd15.r2.dev/castaneda_drea_bot/0003.jpg
```

4. Commit and push `media_urls.txt`.
5. Run the Oracle update command above.

The bot posts media in the exact order of `media_urls.txt` and loops back to the first URL after the last one.

## Public URL Formula

```text
PUBLIC_R2_DOMAIN + "/" + OBJECT_KEY
```

Current public R2 domain:

```text
https://pub-f92c01de6856429eb1c05fbd6e81dd15.r2.dev
```

Example object key:

```text
castaneda_drea_bot/0001.png
```

Final URL:

```text
https://pub-f92c01de6856429eb1c05fbd6e81dd15.r2.dev/castaneda_drea_bot/0001.png
```

## Important

Do not commit:

```text
.env
secrets/*
data/*.json
```

These files contain secrets or live bot progress.
