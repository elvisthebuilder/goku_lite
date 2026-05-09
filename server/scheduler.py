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

async def get_system_report():
    """Fetch raw system metrics via /proc — no external binaries required."""
    ram = "Unknown"
    disk = "Unknown"
    try:
        # RAM via /proc/meminfo
        mem_info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    mem_info[parts[0].rstrip(":")] = int(parts[1])
        total_mb = mem_info.get("MemTotal", 0) // 1024
        avail_mb = mem_info.get("MemAvailable", 0) // 1024
        used_mb  = total_mb - avail_mb
        ram = f"{used_mb}MB used / {total_mb}MB total"

        # Disk via os.statvfs
        import os
        st = os.statvfs("/")
        total_gb = (st.f_blocks * st.f_frsize) / (1024 ** 3)
        free_gb  = (st.f_bavail * st.f_frsize) / (1024 ** 3)
        used_gb  = total_gb - free_gb
        pct = int((used_gb / total_gb) * 100) if total_gb else 0
        disk = f"{used_gb:.1f}GB used / {total_gb:.1f}GB total ({pct}%)"
    except Exception as e:
        logger.error(f"Failed to fetch metrics: {e}")
    return ram, disk

async def _morning_briefing():
    """Send a professional system briefing (Morning)."""
    from .config import config
    now = datetime.utcnow().strftime("%A, %B %d, %Y")
    ram, disk = await get_system_report()
    msg = (
        f"☀️ *Good Morning.* It is {now}.\n\n"
        f"*SYSTEM STATUS*\n"
        f"RAM: {ram}\n"
        f"Disk: {disk}\n\n"
        f"I'm awake and standing by for your morning tasks."
    )
    await _push_message(msg)

async def _afternoon_briefing():
    """Send a professional system briefing (Afternoon)."""
    now = datetime.utcnow().strftime("%H:%M UTC")
    msg = (
        f"🌤️ *Good Afternoon.* It is {now}.\n"
        "Just checking in to see if everything is on track. Do you need any help with your current tasks?"
    )
    await _push_message(msg)

async def _evening_briefing():
    """Send a professional system briefing (Evening)."""
    now = datetime.utcnow().strftime("%H:%M UTC")
    msg = (
        f"🌙 *Good Evening.* It is {now}.\n"
        "The day is winding down. Shall we recap your wins and blockers, or prepare for tomorrow?"
    )
    await _push_message(msg)

# Track last readings for spike detection
_last_ram_percent = None
_last_disk_percent = None

async def _health_check():
    """Check server health and alert if something is wrong or increasing rapidly."""
    import os
    global _last_ram_percent, _last_disk_percent

    try:
        # 1. Check RAM via /proc/meminfo
        mem_info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    mem_info[parts[0].rstrip(":")] = int(parts[1])
        total_ram = mem_info.get("MemTotal", 1)
        avail_ram = mem_info.get("MemAvailable", 0)
        used_ram  = total_ram - avail_ram
        ram_percent = (used_ram / total_ram) * 100

        # Detect RAM Spike
        if _last_ram_percent is not None:
            spike = ram_percent - _last_ram_percent
            if spike > 20:
                await _push_message(f"⚠️ *Rapid RAM Increase:* Memory usage just jumped by {spike:.0f}% in the last 10 minutes! Something might be leaking.")

        if ram_percent > 85:
            await _push_message(f"🚨 *High Memory Alert:* {ram_percent:.0f}% used. System is at risk of crashing.")

        _last_ram_percent = ram_percent

        # 2. Check Disk via os.statvfs
        st = os.statvfs("/")
        total_disk = st.f_blocks * st.f_frsize
        free_disk  = st.f_bavail * st.f_frsize
        disk_percent = int(((total_disk - free_disk) / total_disk) * 100) if total_disk else 0
        free_gb = free_disk / (1024 ** 3)

        if disk_percent > 90:
            await _push_message(f"🚨 *Critical Disk Alert:* {disk_percent}% used. Only {free_gb:.1f}GB left! I might stop being able to save logs soon.")

        _last_disk_percent = disk_percent

    except Exception as e:
        logger.error(f"Guardian health check failed: {e}")

async def schedule_one_time(delay_seconds: int, message: str):
    """Schedule a one-time reminder after a delay."""
    await asyncio.sleep(delay_seconds)
    await _push_message(f"⏰ *Reminder:* {message}")

def set_schedule_time(slot: str, hour: int, minute: int):
    """Update a specific briefing slot live."""
    job_id = f"{slot}_briefing"
    if scheduler.running:
        try:
            scheduler.reschedule_job(
                job_id,
                trigger=CronTrigger(hour=hour, minute=minute)
            )
            logger.info(f"📅 {slot.capitalize()} briefing rescheduled to {hour:02d}:{minute:02d} UTC.")
            return True
        except:
            return False
    return False

def start_scheduler(morning_time=(8, 0), afternoon_time=(14, 0), evening_time=(20, 0)):
    """Start the background scheduler for proactive tasks."""
    if scheduler.running:
        return

    # 1. Morning briefing
    scheduler.add_job(
        _morning_briefing,
        CronTrigger(hour=morning_time[0], minute=morning_time[1]),
        id="morning_briefing",
        replace_existing=True
    )

    # 2. Afternoon briefing
    scheduler.add_job(
        _afternoon_briefing,
        CronTrigger(hour=afternoon_time[0], minute=afternoon_time[1]),
        id="afternoon_briefing",
        replace_existing=True
    )

    # 3. Evening briefing
    scheduler.add_job(
        _evening_briefing,
        CronTrigger(hour=evening_time[0], minute=evening_time[1]),
        id="evening_briefing",
        replace_existing=True
    )

    # 4. Guardian check every 10 minutes
    scheduler.add_job(
        _health_check,
        IntervalTrigger(minutes=10),
        id="health_check",
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"🕐 Goku Guardian active. Morning: {morning_time[0]:02d}:{morning_time[1]:02d}, Afternoon: {afternoon_time[0]:02d}:{afternoon_time[1]:02d}, Evening: {evening_time[0]:02d}:{evening_time[1]:02d} (UTC)")
