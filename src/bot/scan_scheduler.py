"""Schedules scans on the bot's job queue."""

from telegram.ext import JobQueue

from bot.scanner import Scanner
from storage.models import Scan

FIRST_SCAN_DELAY_IN_SECONDS = 2
RESTORE_GAP_IN_SECONDS = 30


def schedule_scan(
    job_queue: JobQueue,
    scanner: Scanner,
    scan: Scan,
    delay_seconds: float = FIRST_SCAN_DELAY_IN_SECONDS,
) -> None:
    """Run a scan after a delay, and then at its interval unless it is a one-time scan."""
    options = {"chat_id": scan.chat_id, "name": _get_job_name(scan.id), "data": scan.id}
    if scan.is_one_time:
        job_queue.run_once(scanner.scan_job, when=delay_seconds, **options)
        return
    job_queue.run_repeating(
        scanner.scan_job, interval=scan.interval_minutes * 60, first=delay_seconds, **options
    )


def unschedule_scan(job_queue: JobQueue, scan_id: int) -> None:
    """Cancel the next runs of a scan."""
    for job in job_queue.get_jobs_by_name(_get_job_name(scan_id)):
        job.schedule_removal()


def restore_scans(job_queue: JobQueue, scanner: Scanner, scans: list[Scan]) -> None:
    """Schedule stored scans after a restart, spread out so they do not all start at once."""
    for index, scan in enumerate(scans):
        delay = FIRST_SCAN_DELAY_IN_SECONDS + index * RESTORE_GAP_IN_SECONDS
        schedule_scan(job_queue, scanner, scan, delay)


def _get_job_name(scan_id: int) -> str:
    return f"scan_{scan_id}"
