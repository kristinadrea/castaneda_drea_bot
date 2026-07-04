import asyncio
import html
import json
import os
import random
import re
import shutil
from datetime import datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from telegram import (
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

POST_TIMEZONE = "US/Eastern"
WINDOW_START = time(7, 7)
WINDOW_END = time(9, 19)
TEST_INTERVAL_SECONDS = 30

QUOTES_FILE = BASE_DIR / "quotes.txt"
IMAGES_DIR = BASE_DIR / "images"
MEDIA_URLS_FILE = Path(os.getenv("MEDIA_URLS_FILE", BASE_DIR / "media_urls.txt"))
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "state.json"
STATE_BACKUP_FILE = DATA_DIR / "state.backup.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
SETTINGS_BACKUP_FILE = DATA_DIR / "settings.backup.json"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ANIMATION_EXTENSIONS = {".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | ANIMATION_EXTENSIONS | VIDEO_EXTENSIONS

MAX_CAPTION_LENGTH = 1024
MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_ANIMATION_BYTES = 50 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024

if not TOKEN:
    raise RuntimeError("Add BOT_TOKEN to .env")

if not CHANNEL_ID:
    raise RuntimeError("Add CHANNEL_ID to .env")

if not ADMIN_USER_ID:
    raise RuntimeError("Add ADMIN_USER_ID to .env")

tz = pytz.timezone(POST_TIMEZONE)
scheduler = AsyncIOScheduler(timezone=tz)
post_lock = asyncio.Lock()


def default_settings():
    return {
        "post_on_start": False,
        "daily_enabled": False,
        "three_day_enabled": True,
        "paused": False,
        "test_mode_enabled": False,
        "test_mode_previous": {
            "daily_enabled": False,
            "three_day_enabled": True,
        },
        "schedules": {
            "daily": {"next_run": None},
            "three_day": {"next_run": None},
        },
    }


def load_json(path, fallback):
    if not path.exists():
        return fallback

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, backup_path, data):
    if path.exists():
        shutil.copy2(path, backup_path)

    temp_file = path.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    temp_file.replace(path)


def load_settings():
    settings = load_json(SETTINGS_FILE, default_settings())
    defaults = default_settings()

    for key, value in defaults.items():
        settings.setdefault(key, value)

    settings.setdefault("test_mode_previous", defaults["test_mode_previous"])
    settings.setdefault("schedules", defaults["schedules"])
    settings["schedules"].setdefault("daily", {"next_run": None})
    settings["schedules"].setdefault("three_day", {"next_run": None})

    return settings


def save_settings():
    save_json(SETTINGS_FILE, SETTINGS_BACKUP_FILE, settings)


def load_quotes(path=QUOTES_FILE):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    parts = [part.strip() for part in raw.split("\n---\n")]
    empty_count = sum(1 for part in parts if not part)
    return [part for part in parts if part], empty_count


def validate_quotes(quotes, empty_count):
    if empty_count:
        print(f"Ignored empty quote blocks: {empty_count}")

    too_long = [
        (index, visible_caption_length(quote))
        for index, quote in enumerate(quotes, start=1)
        if visible_caption_length(quote) > MAX_CAPTION_LENGTH
    ]

    if too_long:
        details = ", ".join(
            f"#{index} ({length} chars)"
            for index, length in too_long[:10]
        )
        raise RuntimeError(
            "Some quotes are longer than Telegram caption limit "
            f"({MAX_CAPTION_LENGTH} chars): {details}"
        )

    print(f"Loaded quotes: {len(quotes)}")


def visible_caption_length(caption):
    caption = re.sub(r"</?i>", "", caption)
    return len(caption)


def prepare_caption(caption):
    source_match = re.search(r"\n\n<i>([^<]+)</i>\s*$", caption)

    if not source_match:
        return html.escape(caption)

    body = caption[:source_match.start()].strip()
    source = source_match.group(1).strip()

    return f"{html.escape(body)}\n\n<i>{html.escape(source)}</i>"


def natural_sort_key(value):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", value)
    ]


def load_media_files(path=IMAGES_DIR):
    if not path.exists():
        return []

    media_names = [
        item.name
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in MEDIA_EXTENSIONS
    ]

    return [
        {
            "type": "local",
            "name": name,
            "value": name,
            "extension": Path(name).suffix.lower(),
        }
        for name in sorted(media_names, key=natural_sort_key)
    ]


def media_extension_from_url(url):
    return Path(urlparse(url).path).suffix.lower()


def load_media_urls(path=MEDIA_URLS_FILE):
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        urls = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    media_urls = []
    for url in urls:
        extension = media_extension_from_url(url)
        if extension not in MEDIA_EXTENSIONS:
            raise RuntimeError(
                f"Unsupported media URL extension in {path.name}: {url}"
            )
        media_urls.append(
            {
                "type": "url",
                "name": url,
                "value": url,
                "extension": extension,
            }
        )

    return media_urls


def load_media():
    media_urls = load_media_urls()
    if media_urls:
        print(f"Using media URLs from {MEDIA_URLS_FILE.name}")
        return media_urls

    print(f"Using local media files from {IMAGES_DIR.name}/")
    return load_media_files()


quotes, empty_quote_count = load_quotes()
images = load_media()

if not quotes:
    raise RuntimeError("quotes.txt does not contain any quotes")

if not images:
    raise RuntimeError("images folder does not contain any supported media files")

validate_quotes(quotes, empty_quote_count)
print(f"Loaded media files: {len(images)}")

state = load_json(STATE_FILE, {"quote_index": 0, "image_index": 0})
state.setdefault("quote_index", 0)
state.setdefault("image_index", 0)

settings = load_settings()


def save_state():
    save_json(STATE_FILE, STATE_BACKUP_FILE, state)


def current_image():
    image_index = state.get("image_index", 0)

    if image_index >= len(images):
        image_index = 0

    state["image_index"] = image_index
    image_name = images[image_index]

    return image_name, image_index + 1


def current_quote():
    quote_index = state.get("quote_index", 0)

    if quote_index >= len(quotes):
        quote_index = 0

    state["quote_index"] = quote_index
    quote = quotes[quote_index]

    return quote, quote_index + 1


def advance_quote():
    state["quote_index"] = (state.get("quote_index", 0) + 1) % len(quotes)


def advance_image():
    state["image_index"] = (state.get("image_index", 0) + 1) % len(images)


def media_size_limit(extension):
    if extension in IMAGE_EXTENSIONS:
        return MAX_PHOTO_BYTES
    if extension in ANIMATION_EXTENSIONS:
        return MAX_ANIMATION_BYTES
    if extension in VIDEO_EXTENSIONS:
        return MAX_VIDEO_BYTES

    return 0


def format_bytes(size):
    return f"{size / 1024 / 1024:.1f} MB"


def pick_allowed_media():
    checked_count = 0

    while checked_count < len(images):
        media_item, image_number = current_image()

        if media_item["type"] == "url":
            return media_item, image_number

        media_path = IMAGES_DIR / media_item["value"]
        size = media_path.stat().st_size
        limit = media_size_limit(media_item["extension"])

        if size <= limit:
            return media_item, image_number

        print(
            f"Skipped media {image_number}/{len(images)} ({media_item['name']}): "
            f"{format_bytes(size)} is larger than limit {format_bytes(limit)}"
        )
        advance_image()
        save_state()
        checked_count += 1

    raise RuntimeError("All media files are larger than Telegram limits")


async def send_media(media_item, caption):
    extension = media_item["extension"]
    media_value = media_item["value"]

    if media_item["type"] == "local":
        media_path = IMAGES_DIR / media_value
        with open(media_path, "rb") as media:
            return await send_media_value(media, extension, caption)

    return await send_media_value(media_value, extension, caption)


async def send_media_value(media, extension, caption):
    if extension in ANIMATION_EXTENSIONS:
        return await application.bot.send_animation(
            chat_id=CHANNEL_ID,
            animation=media,
            caption=caption,
            parse_mode=ParseMode.HTML,
        )
    if extension in VIDEO_EXTENSIONS:
        return await application.bot.send_video(
            chat_id=CHANNEL_ID,
            video=media,
            caption=caption,
            parse_mode=ParseMode.HTML,
        )

    return await application.bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=media,
        caption=caption,
        parse_mode=ParseMode.HTML,
    )


async def post_quote():
    async with post_lock:
        quote, quote_number = current_quote()
        caption = prepare_caption(quote)
        media_item, image_number = pick_allowed_media()
        message = await send_media(media_item, caption)

        print(
            f"Posted quote {quote_number}/{len(quotes)} "
            f"with media {image_number}/{len(images)} ({media_item['name']}) "
            f"at {datetime.now(tz).isoformat()} "
            f"to chat id {message.chat.id}"
        )

        advance_quote()
        advance_image()
        save_state()

        return quote_number, image_number, media_item["name"]


def parse_run_date(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return tz.localize(parsed)

    return parsed.astimezone(tz)


def window_datetime(day):
    start = tz.localize(datetime.combine(day, WINDOW_START))
    end = tz.localize(datetime.combine(day, WINDOW_END))
    return start, end


def random_time_in_window(day, not_before=None):
    start, end = window_datetime(day)

    if not_before and not_before > start:
        start = not_before + timedelta(minutes=1)

    if start >= end:
        return None

    window_seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randrange(window_seconds + 1))


def new_run_date(recurrence_days, previous_run=None):
    now = datetime.now(tz)

    if previous_run:
        day = (previous_run + timedelta(days=recurrence_days)).date()
        return random_time_in_window(day)

    if recurrence_days == 1:
        today_run = random_time_in_window(now.date(), not_before=now)
        if today_run:
            return today_run
        return random_time_in_window((now + timedelta(days=1)).date())

    return random_time_in_window((now + timedelta(days=recurrence_days)).date())


def ensure_next_run(name, recurrence_days):
    schedule = settings["schedules"][name]
    next_run = parse_run_date(schedule.get("next_run"))
    now = datetime.now(tz)

    while not next_run or next_run <= now:
        next_run = new_run_date(recurrence_days, previous_run=next_run)

    schedule["next_run"] = next_run.isoformat()
    save_settings()
    return next_run


async def run_scheduled_post(name):
    try:
        await post_quote()
    except Exception as error:
        print(f"{name} post failed: {error}")
    finally:
        if name == "daily":
            previous = parse_run_date(settings["schedules"]["daily"].get("next_run"))
            settings["schedules"]["daily"]["next_run"] = new_run_date(1, previous).isoformat()
            save_settings()
        elif name == "three_day":
            previous = parse_run_date(settings["schedules"]["three_day"].get("next_run"))
            settings["schedules"]["three_day"]["next_run"] = new_run_date(3, previous).isoformat()
            save_settings()

        schedule_all_jobs()


async def run_test_post():
    if settings.get("paused"):
        return

    try:
        await post_quote()
    except Exception as error:
        print(f"Test post failed: {error}")


def schedule_all_jobs():
    scheduler.remove_all_jobs()

    if settings.get("paused"):
        print("Posting is paused. No jobs scheduled.")
        return

    if settings.get("test_mode_enabled"):
        scheduler.add_job(
            run_test_post,
            IntervalTrigger(seconds=TEST_INTERVAL_SECONDS),
            id="test_mode",
            max_instances=1,
            coalesce=True,
        )
        print(f"Test mode scheduled every {TEST_INTERVAL_SECONDS} seconds.")
        return

    if settings.get("daily_enabled"):
        run_date = ensure_next_run("daily", 1)
        scheduler.add_job(
            run_scheduled_post,
            DateTrigger(run_date=run_date),
            args=["daily"],
            id="daily",
            misfire_grace_time=3600,
        )
        print("Next daily post:", run_date)

    if settings.get("three_day_enabled"):
        run_date = ensure_next_run("three_day", 3)
        scheduler.add_job(
            run_scheduled_post,
            DateTrigger(run_date=run_date),
            args=["three_day"],
            id="three_day",
            misfire_grace_time=3600,
        )
        print("Next three-day post:", run_date)


def is_admin(update):
    user = update.effective_user
    return bool(user and user.id == ADMIN_USER_ID)


async def admin_only(update):
    if is_admin(update):
        return True

    user = update.effective_user
    user_id = user.id if user else "unknown"
    print(f"Unauthorized command attempt from {user_id}")
    return False


def on_off(value):
    return "ON" if value else "OFF"


def format_run(value):
    run_date = parse_run_date(value)
    if not run_date:
        return "not scheduled"
    return run_date.strftime("%Y-%m-%d %H:%M %Z")


def status_text():
    return (
        "Bot settings:\n"
        f"Post on start: {on_off(settings['post_on_start'])}\n"
        f"Daily 07:07-09:19 US/Eastern: {on_off(settings['daily_enabled'])}\n"
        f"Every 3 days 07:07-09:19 US/Eastern: {on_off(settings['three_day_enabled'])}\n"
        f"Paused: {on_off(settings['paused'])}\n"
        f"Test mode: {on_off(settings['test_mode_enabled'])}\n"
        f"Next daily: {format_run(settings['schedules']['daily'].get('next_run'))}\n"
        f"Next 3-day: {format_run(settings['schedules']['three_day'].get('next_run'))}\n"
        f"Next quote: {state.get('quote_index', 0) + 1}/{len(quotes)}\n"
        f"Next media: {state.get('image_index', 0) + 1}/{len(images)}"
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    await update.message.reply_text(
        "Admin panel is ready.\n\n"
        "/status - show settings\n"
        "/post_on_start - toggle post on start\n"
        "/daily - toggle daily schedule\n"
        "/every3days - toggle 3-day schedule\n"
        "/pause - pause all posting\n"
        "/resume - resume active schedules\n"
        "/post_now - publish next post now\n"
        "/test - toggle 30-second test mode"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    await update.message.reply_text(status_text())


async def cmd_post_on_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    settings["post_on_start"] = not settings["post_on_start"]
    save_settings()
    await update.message.reply_text(f"Post on start: {on_off(settings['post_on_start'])}")


async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    settings["daily_enabled"] = not settings["daily_enabled"]
    if settings["daily_enabled"]:
        settings["schedules"]["daily"]["next_run"] = None
    save_settings()
    schedule_all_jobs()
    await update.message.reply_text(f"Daily schedule: {on_off(settings['daily_enabled'])}")


async def cmd_every3days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    settings["three_day_enabled"] = not settings["three_day_enabled"]
    if settings["three_day_enabled"]:
        settings["schedules"]["three_day"]["next_run"] = None
    save_settings()
    schedule_all_jobs()
    await update.message.reply_text(
        f"Every 3 days schedule: {on_off(settings['three_day_enabled'])}"
    )


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    settings["paused"] = True
    save_settings()
    schedule_all_jobs()
    await update.message.reply_text("Posting paused.")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    settings["paused"] = False
    save_settings()
    schedule_all_jobs()
    await update.message.reply_text("Posting resumed.")


async def cmd_post_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    await update.message.reply_text("Posting now...")
    try:
        quote_number, image_number, image_name = await post_quote()
    except Exception as error:
        await update.message.reply_text(f"Post failed: {error}")
        return

    await update.message.reply_text(
        f"Posted quote {quote_number}/{len(quotes)} "
        f"with media {image_number}/{len(images)} ({image_name})."
    )


async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    if settings["test_mode_enabled"]:
        previous = settings.get("test_mode_previous", {})
        settings["test_mode_enabled"] = False
        settings["daily_enabled"] = previous.get("daily_enabled", settings["daily_enabled"])
        settings["three_day_enabled"] = previous.get(
            "three_day_enabled",
            settings["three_day_enabled"],
        )
        message = "Test mode OFF. Previous schedules restored."
    else:
        settings["test_mode_previous"] = {
            "daily_enabled": settings["daily_enabled"],
            "three_day_enabled": settings["three_day_enabled"],
        }
        settings["daily_enabled"] = False
        settings["three_day_enabled"] = False
        settings["test_mode_enabled"] = True
        settings["paused"] = False
        message = "Test mode ON. Ordinary schedules paused; posting every 30 seconds."

    save_settings()
    schedule_all_jobs()
    await update.message.reply_text(message)


async def setup_command_menu(app):
    await app.bot.set_my_commands([], scope=BotCommandScopeDefault())
    await app.bot.set_my_commands(
        [
            BotCommand("status", "show current settings"),
            BotCommand("post_on_start", "toggle post on bot start"),
            BotCommand("daily", "toggle daily 07:07-09:19 US/Eastern posts"),
            BotCommand("every3days", "toggle every 3 days 07:07-09:19 US/Eastern posts"),
            BotCommand("pause", "pause all posting"),
            BotCommand("resume", "resume active schedules"),
            BotCommand("post_now", "publish next post now"),
            BotCommand("test", "toggle 30-second test mode"),
        ],
        scope=BotCommandScopeChat(chat_id=ADMIN_USER_ID),
    )


async def post_init(app):
    await setup_command_menu(app)

    if settings.get("post_on_start") and not settings.get("paused"):
        try:
            await post_quote()
        except Exception as error:
            print(f"Post on start failed: {error}")

    schedule_all_jobs()
    scheduler.start()


async def post_shutdown(app):
    scheduler.shutdown(wait=False)


application = (
    Application.builder()
    .token(TOKEN)
    .post_init(post_init)
    .post_shutdown(post_shutdown)
    .build()
)

application.add_handler(CommandHandler("start", cmd_start))
application.add_handler(CommandHandler("help", cmd_start))
application.add_handler(CommandHandler("status", cmd_status))
application.add_handler(CommandHandler("post_on_start", cmd_post_on_start))
application.add_handler(CommandHandler("daily", cmd_daily))
application.add_handler(CommandHandler("every3days", cmd_every3days))
application.add_handler(CommandHandler("pause", cmd_pause))
application.add_handler(CommandHandler("resume", cmd_resume))
application.add_handler(CommandHandler("post_now", cmd_post_now))
application.add_handler(CommandHandler("test", cmd_test))


if __name__ == "__main__":
    application.run_polling(allowed_updates=Update.ALL_TYPES)
