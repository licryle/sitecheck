# sitecheck — Host accessibility monitor

sitecheck is a small Python utility that monitors HTTP endpoints and reports accessibility via `tglogging` (Telegram) or the console.

Key features
- Accepts short positional target arguments: `URL,interval[,http_code[,retry]]` (e.g. `google.com,30` — `http_code` defaults to `200`, and `retry` defaults to `0` and is recommended to keep at `1` or `2` max).
- Continuous monitor: the CLI starts a long-running loop that checks each host on its configured interval in seconds.
- Docker-friendly: the container accepts a `TARGETS` JSON environment variable to declare targets.
- Notifications: integrates with `tglogging` to send messages to Telegram when configured; falls back to console logging otherwise.

## Install

```bash
direnv allow
```

## Run locally

```bash
PYTHONPATH=src python -m sitecheck -v google.com,30 httpbin.org/status/204,60,204 -s 1

# or with .env
PYTHONPATH=src env $(cat .env) python -m sitecheck
```

- `-v` / `--verbose` enables more verbose output.
- `-s` / `--summary_interval` to provide every X hours a summary of availability.
- Each positional target must be `URL,interval[,http_code[,retry]]`. `retry` is the number of additional checks after a failure. A recovery is logged as a warning; failures after all retries are logged as errors.
- If the URL does not include a scheme, `https://` is added automatically.

## Tests
```bash
pytest
```


## Docker usage

Build the image:

```bash
docker build -t sitecheck .
```

Run with `TARGETS` JSON:

```bash
docker run --rm -e TARGETS='[
  {"host":"https://google.com","interval":30},
  {"host":"https://example.com/health","interval":60,"http_code":200}
]' -e SUMMARY_INTERVAL='24' sitecheck
```

The container entrypoint is `src/docker_entry.py`, which validates `TARGETS` and then executes `python -m sitecheck`.

## TARGETS JSON format

`TARGETS` should be a JSON list of objects:

- `host` (string) — URL to check.
- `interval` (integer seconds) — how often to check this endpoint.
- `http_code` (optional integer) — expected HTTP status code. Defaults to `200`.
- `retry` (optional non-negative integer) — additional checks after a failed request. Defaults to `0`.

Example:

```json
[
  {"host":"https://google.com","interval":30},
  {"host":"https://example.com/health","interval":60,"http_code":200,"retry":1}
]
```

## Environment variables

- `TARGETS` — JSON list used by the Docker entrypoint.
- `SUMMARY_INTERVAL` — An int to present the number of hours between 2 availability summaries. Do not provide, or 0 to disable.
- `TELEGRAM_BOT_TOKEN` — Telegram bot token for notifications.
- `TELEGRAM_CHAT_IDS_DEBUG` — comma-separated chat IDs for debug messages.
- `TELEGRAM_CHAT_IDS_INFO` — comma-separated chat IDs for info messages.
- `TELEGRAM_CHAT_IDS_WARNING` — comma-separated chat IDs for warning messages.
- `TELEGRAM_CHAT_IDS_ERROR` — comma-separated chat IDs for error messages.
- `TELEGRAM_CHAT_IDS_CRITICAL` — comma-separated chat IDs for critical messages.
- `LOG_FILE` — optional local log file path.

If `tglogging` is unavailable or no Telegram config is set, output is logged to the console.

## Files of interest

- `src/sitecheck/cli.py` — CLI entrypoint, parses positional targets and starts the monitor.
- `src/sitecheck/monitor.py` — core check functions and monitoring loop.
- `src/sitecheck/logger.py` — helper that configures `tglogging` or falls back to standard logging.
- `src/docker_entry.py` — container-compatible entrypoint that validates `TARGETS` and launches the monitor.

## Notes

- The CLI is intentionally minimal: positional target args immediately start the monitor loop.
- `requests` is required for network checks and is installed from `requirements.txt`.
- `tglogging` is optional at runtime; if missing, the logger helper falls back to standard console logging.

## License

MIT

