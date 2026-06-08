import argparse
import sys
from urllib.parse import urlparse

from .logger import get_tg_logger
from .monitor import run_forever


def _ensure_scheme(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"https://{url}"
    return url


def parse_target(s: str):
    parts = [p.strip() for p in s.split(',')]
    if len(parts) < 2:
        raise ValueError("expected format: URL,interval[,http_code]")

    host = parts[0]
    try:
        interval = int(parts[1])
    except Exception:
        raise ValueError("interval must be an integer")

    http_code = 200
    if len(parts) >= 3 and parts[2] != "":
        try:
            http_code = int(parts[2])
        except Exception:
            raise ValueError("http_code must be an integer")

    host = _ensure_scheme(host)

    if interval <= 0:
        raise ValueError("interval must be a positive integer")

    return {"host": host, "interval": interval, "http_code": http_code}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sitecheck", description="Site accessibility monitor (baby-step CLI)")
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-s', '--summary-interval', type=int, help='Summary interval in hours')
    parser.add_argument('targets', nargs='*', help='Targets in format URL,interval[,http_code]')

    args = parser.parse_args(argv)

    logger = get_tg_logger('sitecheck', verbose=args.verbose)

    parsed = []
    for t in args.targets:
        try:
            parsed.append(parse_target(t))
        except Exception as e:
            logger.error(f"Error parsing target '{t}': {e}")
            sys.exit(2)

    parsed_str = f"We will monitor {len(parsed)} targets (verbose={args.verbose}):\n"
    for t in parsed:
        parsed_str = parsed_str + f" - {t['host']} interval={t['interval']} seconds for http_code={t['http_code']}\n"
    logger.info(parsed_str)

    run_forever(parsed, verbose=args.verbose, summary_interval=args.summary_interval)
    return parsed
