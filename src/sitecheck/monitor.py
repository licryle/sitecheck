from typing import Dict, List, Tuple, Any
import threading
import time

# Optional dependency: requests. If not installed, checks will report failure
# rather than causing an import-time error so the package can be imported for
# non-network operations or testing.
try:
    import requests
except Exception:
    requests = None

from .logger import get_tg_logger


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


def run_once(targets: List[Dict[str, Any]], verbose: bool = False) -> None:
    """Run a single check pass for all targets. Prints results to stdout.

    This intentionally avoids configuring Python `logging` so the caller can
    manage logging behavior. Output is simple and intended for review.
    """
    logger = get_tg_logger('sitecheck', verbose=verbose)

    for t in targets:
        success, info = check_host(t)
        if success:
            logger.info(f"{t['host']} OK (status={info})")
        else:
            logger.error(f"{t['host']} FAILED ({info})")


def _start_check_thread(target: Dict[str, Any], logger, timeout: int = 10):
    """Start a daemon thread to run a single check for `target` and log result."""

    def _runner():
        success, info = check_host(target, timeout=timeout)
        if success:
            logger.info(f"{target['host']} OK (status={info})")
        else:
            logger.error(f"{target['host']} FAILED ({info})")

    th = threading.Thread(target=_runner, daemon=True)
    th.start()
    return th


def run_forever(targets: List[Dict[str, Any]], verbose: bool = False, timeout: int = 10) -> None:
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

    tick = 0
    threads = []
    try:
        while True:
            for idx, t in enumerate(targets):
                interval = intervals[idx]
                # Run immediately on tick 0, then every `interval` seconds
                if tick % interval == 0:
                    threads.append(_start_check_thread(t, logger, timeout=timeout))

            tick += 1
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down monitor...")


__all__ = ["check_host", "run_once", "run_forever"]
