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


def check_host(target: Dict[str, Any], timeout: int = 10) -> Tuple[bool, Any]:
    """Check a single host.

    Returns (success, status_or_exception).
    """
    url = target.get("host")
    expected = target.get("http_code", 200)

    try:
        if requests is None:
            raise RuntimeError("requests library not installed")

        resp = requests.get(url, timeout=timeout)
        if resp.status_code == expected:
            return True, resp.status_code
        else:
            return False, resp.status_code
    except Exception as e:
        return False, e


def _send_summary(target: Dict[str, Any], stats: TargetStats, logger) -> None:
    """Generate and log a summary for a target."""
    if stats.total_checks == 0:
        return

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

    # Calculate trailing failures
    consecutive_failures = 0
    for _, success in reversed(stats.history):
        if not success:
            consecutive_failures += 1
        else:
            break
    
    failure_msg = ""
    if consecutive_failures > 0:
        failure_msg = f"\n⚠️ Consecutive failures: {consecutive_failures}"

    summary_msg = (
        f"{icon} **Summary for {target['host']}**\n"
        f"Success Rate: {success_rate:.2f}%\n"
        f"Total Checks: {stats.total_checks}"
        f"{failure_msg}"
    )
    
    # Using info level as requested for "priority_info"
    logger.info(f"📊 {summary_msg}")


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
    last_summary_timestamps = {idx: datetime.now() for idx in range(len(targets))}

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
                    def _wrapped_check(target_idx, target_dict, logger_obj, stats_obj, timeout_val):
                        success, info = check_host(target_dict, timeout=timeout_val)
                        
                        # Update stats
                        stats_obj.total_checks += 1
                        if success:
                            stats_obj.success_count += 1
                        stats_obj.history.append((datetime.now(), success))
                        
                        # Keep history manageable (e.g., last 1000 checks)
                        if len(stats_obj.history) > 1000:
                            stats_obj.history.popleft()

                        if success:
                            logger_obj.info(f"✅ {target_dict['host']} OK (status={info}) ✅")
                        else:
                            logger_obj.error(f"❌ {target_dict['host']} FAILED (status={info}, expected={target_dict['http_code']}) ❌")

                    threading.Thread(
                        target=_wrapped_check, 
                        args=(idx, t, logger, stats, timeout),
                        daemon=True
                    ).start()

                # Check if it's time for a summary
                if summary_interval and (now - last_summary_timestamps[idx]).total_seconds() >= summary_interval * 3600:
                    _send_summary(t, stats, logger)
                    last_summary_timestamps[idx] = now

            tick += 1
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down monitor...")


__all__ = ["check_host", "run_forever"]