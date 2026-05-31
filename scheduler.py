"""
GMB HUNTER — AUTO SCHEDULER (Phase 4)
Runs scraping jobs automatically every day at a set time.
No manual intervention needed.

Usage:
    scheduler.py                    <- start scheduler (runs forever)
    scheduler.py --add              <- add a new daily job
    scheduler.py --list             <- list all scheduled jobs
    scheduler.py --remove           <- remove a job
    scheduler.py --run-now         <- run all jobs immediately
"""

import sys
import os
import json
import time
import subprocess
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import log_info, log_success, log_warning, log_error, print_banner

JOBS_FILE = "config/scheduled_jobs.json"


# ── Job Management ─────────────────────────────────────────────────────────────

def load_jobs() -> list:
    """Load all scheduled jobs from config file"""
    os.makedirs("config", exist_ok=True)
    if not os.path.exists(JOBS_FILE):
        return []
    try:
        with open(JOBS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_jobs(jobs: list):
    """Save jobs to config file"""
    os.makedirs("config", exist_ok=True)
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


def add_job():
    """Interactive: add a new scheduled job"""
    print("\n" + "="*50)
    print("  ADD NEW SCHEDULED JOB")
    print("="*50)

    business_type = input("\n  Business type (e.g. restaurants, hotels, dentists): ").strip()
    city          = input("  City (e.g. Lahore, London, Dubai): ").strip()
    run_time      = input("  Run time daily (24hr format, e.g. 08:00): ").strip()
    target        = input("  How many records per day? (default 100): ").strip()

    if not business_type or not city or not run_time:
        print("  ❌ All fields required!")
        return

    try:
        hour, minute = run_time.split(":")
        int(hour); int(minute)
    except:
        print("  ❌ Invalid time format. Use HH:MM (e.g. 08:00)")
        return

    target = int(target) if target.isdigit() else 100

    job = {
        "id":            f"{business_type}_{city}_{run_time}".replace(" ", "_").lower(),
        "business_type": business_type,
        "city":          city,
        "run_time":      run_time,
        "target":        target,
        "active":        True,
        "created_at":    str(datetime.now()),
        "last_run":      None,
        "total_runs":    0,
        "total_records": 0,
    }

    jobs = load_jobs()

    # Check for duplicate
    for existing in jobs:
        if existing["id"] == job["id"]:
            print(f"  ⚠️  Job already exists: {job['id']}")
            return

    jobs.append(job)
    save_jobs(jobs)

    print(f"\n  ✅ Job added successfully!")
    print(f"  📋 Business : {business_type}")
    print(f"  🏙️  City     : {city}")
    print(f"  ⏰ Time     : {run_time} daily")
    print(f"  🎯 Target   : {target} records/day")


def list_jobs():
    """Display all scheduled jobs"""
    jobs = load_jobs()

    print("\n" + "="*60)
    print("  SCHEDULED JOBS")
    print("="*60)

    if not jobs:
        print("  No jobs scheduled yet.")
        print("  Run: scheduler.py --add")
        return

    for i, job in enumerate(jobs, 1):
        status    = "✅ Active" if job.get("active") else "⏸️  Paused"
        last_run  = job.get("last_run") or "Never"
        print(f"\n  [{i}] {job['business_type'].upper()} in {job['city']}")
        print(f"      Status   : {status}")
        print(f"      Time     : {job['run_time']} daily")
        print(f"      Target   : {job['target']} records/day")
        print(f"      Last Run : {last_run}")
        print(f"      Total    : {job.get('total_records', 0)} records collected")

    print()


def remove_job():
    """Interactive: remove a scheduled job"""
    jobs = load_jobs()
    if not jobs:
        print("  No jobs to remove.")
        return

    list_jobs()
    choice = input("  Enter job number to remove (or 0 to cancel): ").strip()

    try:
        idx = int(choice) - 1
        if idx < 0:
            return
        removed = jobs.pop(idx)
        save_jobs(jobs)
        print(f"  ✅ Removed: {removed['business_type']} in {removed['city']}")
    except:
        print("  ❌ Invalid choice")


# ── Job Runner ─────────────────────────────────────────────────────────────────

def run_job(job: dict):
    """Execute a single scraping job"""
    business_type = job["business_type"]
    city          = job["city"]
    target        = job.get("target", 100)

    log_info(f"Running job: {business_type} in {city} ({target} records)")

    try:
        result = subprocess.run(
            [
                sys.executable, "main.py",
                "--type", business_type,
                "--city", city,
            ],
            capture_output = False,
            text           = True,
        )

        # Update job stats
        jobs = load_jobs()
        for j in jobs:
            if j["id"] == job["id"]:
                j["last_run"]      = str(datetime.now())
                j["total_runs"]    = j.get("total_runs", 0) + 1
                j["total_records"] = j.get("total_records", 0) + target
                break
        save_jobs(jobs)

        if result.returncode == 0:
            log_success(f"Job completed: {business_type} in {city}")
        else:
            log_error(f"Job failed: {business_type} in {city}")

    except Exception as e:
        log_error(f"Job execution error: {e}")


def run_all_now():
    """Run all active jobs immediately (for testing)"""
    jobs = load_jobs()
    active = [j for j in jobs if j.get("active")]

    if not active:
        print("  No active jobs found.")
        return

    print(f"\n  Running {len(active)} jobs now...")
    for job in active:
        run_job(job)


# ── Scheduler Loop ─────────────────────────────────────────────────────────────

def should_run_now(job: dict) -> bool:
    """Check if a job should run at current time"""
    try:
        now          = datetime.now()
        run_time     = job.get("run_time", "08:00")
        hour, minute = map(int, run_time.split(":"))

        # Check if current time matches job time (within 1 minute window)
        if now.hour == hour and now.minute == minute:
            # Check if already ran today
            last_run = job.get("last_run")
            if last_run:
                last_run_date = datetime.fromisoformat(last_run).date()
                if last_run_date == date.today():
                    return False  # Already ran today
            return True

        return False
    except:
        return False


def start_scheduler():
    """
    Main scheduler loop.
    Checks every minute if any job needs to run.
    Runs forever until Ctrl+C.
    """
    print_banner()
    print("="*52)
    print("  AUTO SCHEDULER STARTED")
    print("  Press Ctrl+C to stop")
    print("="*52)

    jobs = load_jobs()
    if not jobs:
        print("\n  ⚠️  No jobs scheduled!")
        print("  Add jobs first: scheduler.py --add")
        return

    print(f"\n  Monitoring {len(jobs)} job(s):")
    for job in jobs:
        if job.get("active"):
            print(f"    • {job['business_type']} in {job['city']} → runs at {job['run_time']} daily")

    print(f"\n  Current time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("  Checking every minute...\n")

    try:
        while True:
            jobs = load_jobs()  # Reload in case jobs were added/removed
            now  = datetime.now().strftime("%H:%M")

            for job in jobs:
                if job.get("active") and should_run_now(job):
                    log_info(f"⏰ Scheduled time reached: {job['business_type']} in {job['city']}")
                    run_job(job)

            # Show heartbeat every hour
            if datetime.now().minute == 0:
                log_info(f"Scheduler running... Next check in 1 min | Time: {now}")

            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        print("\n\n  ⏹️  Scheduler stopped by user.")


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--add" in args:
        add_job()
    elif "--list" in args:
        list_jobs()
    elif "--remove" in args:
        remove_job()
    elif "--run-now" in args:
        run_all_now()
    else:
        start_scheduler()