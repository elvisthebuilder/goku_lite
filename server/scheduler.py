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
    """Send a daily morning briefing with system stats."""
    from .config import config
    import subprocess
    
    now = datetime.utcnow().strftime("%A, %B %d, %Y")
    db_status = "✅ Connected" if config.DATABASE_URL else "⚠️ Local"
    mem_status = "✅ Active" if config.QDRANT_API_KEY else "⚠️ Disabled"
    model = config.GOKU_MODEL or "Unknown"

    # Fetch System Stats
    ram_info = "Unknown"
    disk_info = "Unknown"
    try:
        # RAM
        free = subprocess.check_output(["free", "-m"]).decode().split("\n")[1].split()
        ram_info = f"{free[2]}MB / {free[1]}MB used"
        # Disk
        df = subprocess.check_output(["df", "-h", "/"]).decode().split("\n")[1].split()
        disk_info = f"{df[2]} / {df[1]} used ({df[4]})"
    except Exception:
        pass

    msg = (
        f"🌅 *Good morning!* It's {now}.\n\n"
        f"🛡️ *System Health:*\n"
        f"• *RAM:* {ram_info}\n"
        f"• *Disk:* {disk_info}\n\n"
        f"🧠 *Brain Status:*\n"
        f"• *Model:* {model}\n"
        f"• *Database:* {db_status}\n"
        f"• *Memory Cloud:* {mem_status}\n\n"
        f"Everything is looking sharp. I'm ready for orders! 🐉"
    )
    logger.info("📤 Sending morning briefing with system metrics...")
    await _push_message(msg)

# Track last readings for spike detection
_last_ram_percent = None
_last_disk_percent = None

async def _health_check():
    """Check server health and alert if something is wrong or increasing rapidly."""
    import subprocess
    global _last_ram_percent, _last_disk_percent
    
    try:
        # 1. Check RAM
        free = subprocess.check_output(["free", "-m"]).decode().split("\n")[1].split()
        total_ram = int(free[1])
        used_ram = int(free[2])
        ram_percent = (used_ram / total_ram) * 100

        # Detect RAM Spike
        if _last_ram_percent is not None:
            spike = ram_percent - _last_ram_percent
            if spike > 20: # 20% jump in 10 mins
                await _push_message(f"⚠️ *Rapid RAM Increase:* Memory usage just jumped by {spike:.0f}% in the last 10 minutes! Something might be leaking.")

        if ram_percent > 85:
            await _push_message(f"🚨 *High Memory Alert:* {ram_percent:.0f}% used. System is at risk of crashing.")
        
        _last_ram_percent = ram_percent

        # 2. Check Disk
        df = subprocess.check_output(["df", "-h", "/"]).decode().split("\n")[1].split()
        disk_percent = int(df[4].replace("%", ""))

        if disk_percent > 90:
            await _push_message(f"🚨 *Critical Disk Alert:* {disk_percent}% used. Only {df[3]} left! I might stop being able to save logs soon.")
        
        _last_disk_percent = disk_percent

    except Exception as e:
        logger.error(f"Guardian health check failed: {e}")

async def schedule_one_time(delay_seconds: int, message: str):
    """Schedule a one-time reminder after a delay."""
    await asyncio.sleep(delay_seconds)
    await _push_message(f"⏰ *Reminder:* {message}")

def set_briefing_time(hour: int, minute: int):
    """Update the morning briefing schedule live."""
    if scheduler.running:
        scheduler.reschedule_job(
            "morning_briefing",
            trigger=CronTrigger(hour=hour, minute=minute)
        )
        logger.info(f"📅 Morning briefing rescheduled to {hour:02d}:{minute:02d} UTC.")
        return True
    return False

def start_scheduler(briefing_hour: int = 8, briefing_minute: int = 0):
    """Start the background scheduler for proactive tasks."""
    if scheduler.running:
        return

    # Daily morning briefing
    scheduler.add_job(
        _morning_briefing,
        CronTrigger(hour=briefing_hour, minute=briefing_minute),
        id="morning_briefing",
        replace_existing=True
    )

    # Guardian check every 10 minutes
    scheduler.add_job(
        _health_check,
        IntervalTrigger(minutes=10),
        id="health_check",
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"🕐 Goku Guardian active. Checking system every 10 minutes.")
