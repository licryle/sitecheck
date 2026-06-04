import argparse
import sys
from urllib.parse import urlparse


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
    parser.add_argument('targets', nargs='*', help='Targets in format URL,interval[,http_code]')

    args = parser.parse_args(argv)

    parsed = []
    for t in args.targets:
        try:
            parsed.append(parse_target(t))
        except Exception as e:
            print(f"Error parsing target '{t}': {e}", file=sys.stderr)
            sys.exit(2)

    print(f"Parsed {len(parsed)} targets (verbose={args.verbose}):")
    for t in parsed:
        print(f" - {t['host']} interval={t['interval']} http_code={t['http_code']}")

    return parsed
