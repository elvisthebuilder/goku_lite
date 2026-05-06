import logging
import asyncio
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def _push_message(message: str):
    """Push a proactive message to the owner."""
    from .telegram_handler import send_proactive_message
    owner_id = os.getenv("GOKU_OWNER_ID")
    if not owner_id:
        logger.warning("⚠️ GOKU_OWNER_ID not set. Cannot send proactive message.")
        return
    await send_proactive_message(chat_id=owner_id, text=message)

async def _morning_briefing():
    """Send a daily morning briefing."""
    from .config import config
    now = datetime.utcnow().strftime("%A, %B %d, %Y")
    db_status = "✅ Connected" if config.DATABASE_URL else "⚠️ Local"
    mem_status = "✅ Active" if config.QDRANT_API_KEY else "⚠️ Disabled"
    model = config.GOKU_MODEL or "Unknown"

    msg = (
        f"🌅 *Good morning!* It's {now} and I'm up and running.\n\n"
        f"Here's a quick look at how things are doing:\n"
        f"• *Brain:* {model}\n"
        f"• *Database:* {db_status}\n"
        f"• *Memory Cloud:* {mem_status}\n\n"
        f"I'm ready when you are! Just say the word. 🐉"
    )
    logger.info("📤 Sending morning briefing...")
    await _push_message(msg)

async def _health_check():
    """Check server health and alert if something is wrong."""
    import subprocess
    try:
        # Check memory usage
        result = subprocess.run(
            ["free", "-m"], capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split("\n")
        mem_line = lines[1].split()
        total = int(mem_line[1])
        used = int(mem_line[2])
        percent = (used / total) * 100

        if percent > 85:
            msg = (
                f"🚨 *Memory Alert!*\n"
                f"I'm using {percent:.0f}% of RAM right now ({used}MB / {total}MB). "
                f"Things might slow down. You may want to restart me with `goku-lite-restart`."
            )
            logger.warning(f"⚠️ High memory usage: {percent:.0f}%")
            await _push_message(msg)
    except Exception as e:
        logger.error(f"Health check failed: {e}")

async def schedule_one_time(delay_seconds: int, message: str):
    """Schedule a one-time reminder after a delay."""
    await asyncio.sleep(delay_seconds)
    await _push_message(f"⏰ *Reminder:* {message}")

def start_scheduler(briefing_hour: int = 8, briefing_minute: int = 0):
    """Start the background scheduler for proactive tasks."""
    if scheduler.running:
        return

    # Daily morning briefing (default: 8:00 AM UTC)
    scheduler.add_job(
        _morning_briefing,
        CronTrigger(hour=briefing_hour, minute=briefing_minute),
        id="morning_briefing",
        replace_existing=True
    )

    # Health check every 30 minutes
    scheduler.add_job(
        _health_check,
        IntervalTrigger(minutes=30),
        id="health_check",
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"🕐 Goku Scheduler started. Briefing at {briefing_hour:02d}:{briefing_minute:02d} UTC daily.")
