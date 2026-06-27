# Sagi

Sagi is a Discord moderation bot focused on scam detection, OCR scanning, honeypot traps, and quick admin tooling.

## Requirements

- Python 3.10 or newer
- A Discord bot token
- Tesseract OCR installed on the system

## Install

Create and activate a virtual environment, then install the Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install Tesseract if you want OCR features to work:

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

## Configure

Create a `.env` file in the project root with at least:

```env
DISCORD_TOKEN=your-bot-token-here
```

Optional environment variables:

```env
SHARD_COUNT=auto-or-an-integer
FEEDBACK_CHANNEL_ID=123456789012345678
```

## Run

Start the bot with:

```bash
python main.py
```

On startup, the bot will:

- load every cog in `./cogs`
- sync slash commands
- create `data/server_config.json` if it does not exist

## Systemd

There is also a sample service file at `sagi.service`. It assumes:

- the project lives at `/home/kylomask/bots/sagi`
- the virtual environment lives at `/home/kylomask/bots/sagi/.venv`
- secrets are stored in `/home/kylomask/bots/sagi/.env`

If you use a different path, update the service file before enabling it.

## Commands

Useful admin commands include:

- `/status` to view uptime and moderation stats
- `/feedback` to send feedback to the dev channel
- `/config view` to inspect server settings
- `/config ocr_enabled`, `/config stage_mode`, `/config spam_threshold`, `/config log_channel`, `/config softban`, `/config mercy`, `/config silly_mode`, `/config reset`
- `/honeypot activate` and `/honeypot deactivate`

## Notes

- OCR depends on `pytesseract`, which needs the `tesseract` binary installed on the host.
- The bot expects the `message_content` intent to be enabled in the Discord developer portal.
