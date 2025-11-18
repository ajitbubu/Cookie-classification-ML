"""
Dynamic Cookie Scanning Scheduler

This module uses APScheduler to periodically fetch domain scan schedules
from an API and execute them using the `scan_domain` function from
`cookie_scanner.py`.

Features:
- Fetch schedules from API at regular intervals.
- Add/update jobs dynamically into APScheduler.
- Support for hourly, daily, weekly, and monthly cron triggers.
- Thread pool execution to allow multiple scans concurrently.
"""

import os
import time
import logging
from typing import Any, Dict, List

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.executors.pool import ThreadPoolExecutor

from config import (
    API_URL,
    REQUEST_TIMEOUT,
    REFRESH_INTERVAL,
    MAX_WORKERS,
    JOB_REPLACE_EXISTING_INSTANCE,
    JOB_MAX_INSTANCES,
    JOB_COALESCE,
    JOB_MISFIRE_GRACE_TIME,
    DEFAULT_BUTTON_SELECTOR
)
from cookie_scanner import scan_domain

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# APScheduler setup with thread pool executor
# ---------------------------------------------------------------------------
executors = {"default": ThreadPoolExecutor(max_workers=MAX_WORKERS)}
scheduler = BackgroundScheduler(executors=executors)


# ---------------------------------------------------------------------------
# Job Listener
# ---------------------------------------------------------------------------
def job_listener(event: Any) -> None:
    """
    Listen to job events and log results.

    Args:
        event: APScheduler job event (success or error).
    """
    if event.exception:
        logger.error(f"Job {event.job_id} failed: {event.exception}")
    else:
        logger.info(f"Job {event.job_id} executed successfully")


# Attach listener to scheduler
scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)


# ---------------------------------------------------------------------------
# API Fetching
# ---------------------------------------------------------------------------
def fetch_schedules() -> List[Dict[str, Any]]:
    """
    Fetch schedules from the API.

    Returns:
        A list of schedule dictionaries from the API,
        or an empty list on failure.
    """
    try:
        response = requests.get(API_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        return payload.get("data", [])
    except Exception as e:
        logger.error(f"Failed to fetch schedules: {e}")
        return []


# ---------------------------------------------------------------------------
# Job Management
# ---------------------------------------------------------------------------
def add_jobs() -> None:
    """
    Sync schedules from API into APScheduler.

    Clears existing jobs to avoid duplicates, then adds jobs based on
    frequency (hourly, daily, weekly, monthly).
    """
    DAY_NAME_MAP = {
        "sunday": "sun",
        "monday": "mon",
        "tuesday": "tue",
        "wednesday": "wed",
        "thursday": "thu",
        "friday": "fri",
        "saturday": "sat",
    }
    schedules = fetch_schedules()

    # Clear existing jobs before re-adding
    for job in scheduler.get_jobs():
        scheduler.remove_job(job.id)

    for schedule_item in schedules:
        try:
            #domain_id = schedule_item.get("_id")
            domain_config_id = schedule_item.get("domain_config_id")
            domain_data = schedule_item.get("data", {})
            domain = domain_data.get("domain", "")
            description = domain_data.get("description", "")
            schedule_cfg = domain_data.get("schedule", {})
            freq = schedule_cfg.get("frequency", "").lower()
            t = schedule_cfg.get("time", {})
            
            raw_allow = domain_data.get("allow_deep_scan", True)
            if isinstance(raw_allow, bool):
                allow_deep_scan = raw_allow
            else:
                allow_deep_scan = str(raw_allow).strip().lower() == "true"

            if not allow_deep_scan:
                logger.info(f"Skipping {domain} [{domain_config_id}] because allow_deep_scan={raw_allow}")
                continue

            # Determine trigger based on frequency
            if freq == "hourly":
                trigger = CronTrigger(minute=t.get("minute", 0))
            elif freq == "daily":
                trigger = CronTrigger(hour=t.get("hour", 0), minute=t.get("minute", 0))
            elif freq == "weekly":
                raw_day = t.get("day", 0)

                # Normalize day_of_week
                if isinstance(raw_day, str):
                    day_str = raw_day.strip().lower()
                    day_of_week = DAY_NAME_MAP.get(day_str, day_str)  # fallback: pass as-is
                else:
                    day_of_week = raw_day  # assume integer 0–6 works

                trigger = CronTrigger(
                    day_of_week=day_of_week,
                    hour=t.get("hour", 0),
                    minute=t.get("minute", 0),
                )
            elif freq == "monthly":
                day = t.get("day", 1)
                # Handle cases like 30th and 31st
                if day >= 28:  # Feb can have 28 or 29 days only
                    day = "last"
                trigger = CronTrigger(
                    day=day,
                    hour=t.get("hour", 0),
                    minute=t.get("minute", 0),
                )
            else:
                logger.warning(f"Unknown frequency '{freq}' for {domain}, skipping")
                continue

            # Add job to scheduler
            scheduler.add_job(
                scan_domain,
                trigger,
                args=[
                    {
                        "domain_config_id": domain_config_id,
                        "domain": domain,
                        "domainUrl": domain,
                        "description": description,
                        "maxPages": domain_data.get("maxPages"),
                        "scanDepth": domain_data.get("scanDepth"),
                        "maxRetries": domain_data.get("maxRetries"),
                        "customPages": domain_data.get("customPages", []),
                        "accept_selector": domain_data.get("accept_selector", DEFAULT_BUTTON_SELECTOR),
                    }
                ],
                id=domain,  # unique per domain
                replace_existing=JOB_REPLACE_EXISTING_INSTANCE,  # Replace if job already exists
                max_instances=JOB_MAX_INSTANCES,  # Prevent overlap
                coalesce=JOB_COALESCE,  # Run missed jobs only once
                misfire_grace_time=JOB_MISFIRE_GRACE_TIME,  # Grace period for delayed jobs
            )
            logger.info(f"Scheduled {domain} ({freq}) [{domain_config_id}]")

        except Exception as e:
            logger.error(f"Failed to schedule {domain} [{domain_config_id}]: {e}")


# ---------------------------------------------------------------------------
# Scheduler Execution
# ---------------------------------------------------------------------------
def run_scheduler() -> None:
    """
    Main scheduler loop.

    Starts APScheduler, loads jobs initially, and refreshes schedules
    at the configured refresh interval until terminated.
    """
    logger.info("Starting scheduler...")
    scheduler.start()

    # Initial delay before adding jobs
    time.sleep(20)
    add_jobs()

    try:
        while True:
            time.sleep(REFRESH_INTERVAL)
            logger.info("Refreshing schedules from API...")
            add_jobs()
    except (KeyboardInterrupt, SystemExit):
        logger.info
