import json
import os
import sys


def _validate_target(item, index):
    if not isinstance(item, dict):
        raise ValueError(f"TARGETS[{index}] must be an object")

    host = item.get("host")
    interval = item.get("interval")
    http_code = item.get("http_code")

    if not host or interval is None:
        raise ValueError(f"TARGETS[{index}] missing required host or interval")

    if not isinstance(interval, int):
        raise ValueError(f"TARGETS[{index}] interval must be an integer")

    parts = [host, str(interval)]
    if http_code is not None:
        parts.append(str(http_code))
    return ",".join(parts)


def main():
    raw = os.getenv("TARGETS", "")
    if not raw:
        print("TARGETS environment variable is required", file=sys.stderr)
        return 1

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid TARGETS JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(data, list):
        print("TARGETS must be a JSON list", file=sys.stderr)
        return 1

    args = []
    for idx, item in enumerate(data):
        try:
            args.append(_validate_target(item, idx))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    summary = os.getenv("SUMMARY_INTERVAL", "0")
    if summary.isdigit() and int(summary) > 0:
        args.append(f"--summary-interval={summary}")

    os.execvp(sys.executable, [sys.executable, "-m", "sitecheck"] + args)


if __name__ == "__main__":
    raise SystemExit(main())
