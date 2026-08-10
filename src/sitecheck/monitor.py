from typing import Dict, List, Tuple, Any
import threading
import time
from collections import deque
from datetime import datetime, timedelta

# Optional dependency: requests. If not installed, checks will report failure
# rather than causing an import-time error so the package can be imported for
# non-network operations or testing.
try:
    import requests
except Exception:
    requests = None

from .logger import get_tg_logger


class TargetStats:
    def __init__(self):
        self.total_checks = 0
        self.success_count = 0
        self.history = deque()  # Stores (timestamp, success_bool)
        self.last_summary_time = None


class RetryStatus(int):
    """HTTP status code for a check that succeeded after a retry."""

    recovered = True


def check_host(target: Dict[str, Any], timeout: int = 10, retry: int = 0) -> Tuple[bool, Any]:
    """Check a single host.

    Returns (success, status_or_exception).
    """
    url = target.get("host")
    expected = target.get("http_code", 200)
    retries = int(target.get("retry", retry))
    if retries < 0:
        raise ValueError("retry must be a non-negative integer")

    for attempt in range(retries + 1):
        try:
            if requests is None:
                raise RuntimeError("requests library not installed")

            resp = requests.get(url, timeout=timeout)
            if resp.status_code == expected:
                status = RetryStatus(resp.status_code) if attempt else resp.status_code
                return True, status
            last_result = resp.status_code
        except Exception as exc:
            last_result = exc

    return False, last_result


def _compile_summary(target: Dict[str, Any], stats: TargetStats, logger) -> str:
    """Generate and log a summary for a target."""
    if stats.total_checks == 0:
        return ""

    success_rate = (stats.success_count / stats.total_checks) * 100
    
    # Determine icon
    if success_rate == 100:
        icon = "✅"
    elif success_rate >= 99:
        icon = "🟢"
    elif success_rate >= 90:
        icon = "🟠"
    else:
        icon = "🔴"

    # Find all failure intervals and flukes using precise transition rules.
    # A single failure followed by a success is a fluke.
    # A failure followed by another failure is downtime. Including "ongoing ones" at summary time.
    failure_intervals = []
    hist = sorted(stats.history, key=lambda entry: entry[0])
    now = datetime.now()
    
    downtime_str = ""
    fluke_count = 0
    downtime_parts = []

    i = 0
    while i < len(hist):
        if hist[i][1]:
            i += 1
            continue

        start_time = hist[i][0]
        failure_count = 1
        j = i + 1
        while j < len(hist) and not hist[j][1]:
            failure_count += 1
            j += 1

        next_is_success = j < len(hist) and hist[j][1]
        ongoing = j == len(hist)

        if failure_count == 1:
            if next_is_success:
                fluke_count += 1
        else:
            end_time = hist[j - 1][0] if next_is_success else now
            duration = end_time - start_time
            failure_intervals.append({
                'start': start_time,
                'end': end_time,
                'duration': duration,
                'count': failure_count,
                'ongoing': ongoing,
            })

        i = j

    for interval in failure_intervals:
        total_seconds = int(interval['duration'].total_seconds())
        if total_seconds < 60:
            dur_str = f"{total_seconds}s"
        elif total_seconds < 3600:
            dur_str = f"{total_seconds // 60}m"
        else:
            dur_str = f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"
        
        start_str = interval['start'].strftime("%H:%M")
        end_str = interval['end'].strftime("%H:%M")
        downtime_parts.append(f"{dur_str} {start_str}-{end_str}")

    summary_parts = []
    if fluke_count:
        summary_parts.append(f"{fluke_count} fluke{'s' if fluke_count != 1 else ''}")
    if downtime_parts:
        summary_parts.append(f"Down for {', '.join(downtime_parts)}")
    if summary_parts:
        downtime_str = f" - {' - '.join(summary_parts)}"

    return f"{icon} {success_rate:.0f}% {target['host']}{downtime_str}"


def run_forever(targets: List[Dict[str, Any]], verbose: bool = False, timeout: int = 10, summary_interval: int = None) -> None:
    """Run the monitor forever.

    This implementation uses a simple 1-second tick and launches a short-lived
    daemon thread to perform each check when the target's interval elapses.
    """
    if not targets:
        logger = get_tg_logger('sitecheck', verbose=verbose)
        logger.warning("No targets to monitor.")
        return

    logger = get_tg_logger('sitecheck', verbose=verbose)

    # Validate intervals and coerce to ints
    intervals = [int(t.get("interval", 60)) for t in targets]

    # Initialize stats for each target
    stats_map: Dict[int, TargetStats] = {idx: TargetStats() for idx in range(len(targets))}
    
    # Track last summary time for each target
    last_summary_timestamps = datetime.now()

    tick = 0
    try:
        while True:
            now = datetime.now()
            for idx, t in enumerate(targets):
                interval = intervals[idx]
                stats = stats_map[idx]

                # Run immediately on tick 0, then every `interval` seconds
                if tick % interval == 0:
                    # We use a wrapper to update stats
                    def _wrapped_check(target_idx, target_dict, logger_obj, stats_obj, max_stats, timeout_val):
                        success, info = check_host(
                            target_dict,
                            timeout=timeout_val,
                            retry=target_dict.get("retry", 0),
                        )
                        
                        # Update stats
                        stats_obj.total_checks += 1
                        if success:
                            stats_obj.success_count += 1
                        if success and getattr(info, "recovered", False):
                            recovery_time = datetime.now()
                            stats_obj.history.append((recovery_time, False))
                            stats_obj.history.append((recovery_time, True))
                        else:
                            stats_obj.history.append((datetime.now(), success))
                        
                        # Keep history manageable
                        if len(stats_obj.history) > max_stats:
                            stats_obj.history.popleft()

                        if success and getattr(info, "recovered", False):
                            logger_obj.warning(
                                f"⚠️ {target_dict['host']} recovered after retry (status={info}) ⚠️"
                            )
                        elif success:
                            logger_obj.info(f"✅ {target_dict['host']} OK (status={info}) ✅")
                        else:
                            logger_obj.error(f"❌ {target_dict['host']} FAILED (status={info}, expected={target_dict['http_code']}) ❌")

                    threading.Thread(
                        target=_wrapped_check, 
                        args=(idx, t, logger, stats, summary_interval * 3600 if summary_interval else 0, timeout),
                        daemon=True
                    ).start()

            # Check if it's time for a summary
            if summary_interval and (now - last_summary_timestamps).total_seconds() >= summary_interval * 3600:
                summary = f"📊 Last {summary_interval} hours summary:\n"
                for idx, t in enumerate(targets):
                    summary += _compile_summary(t, stats_map[idx], logger) + "\n"
                logger.priority_info(summary[:-1])
                last_summary_timestamps = now

                # Reset stats after the summary so the next report counts only
                # checks that happened since this summary.
                for stats in stats_map.values():
                    stats.total_checks = 0
                    stats.success_count = 0
                    stats.history.clear()

            tick += 1
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down monitor...")


__all__ = ["check_host", "run_forever"]