# sitecheck — Host accessibility monitor

sitecheck is a small Python utility that monitors HTTP endpoints and reports accessibility via `tglogging` (Telegram) or the console.

Key features
- Accepts short positional target arguments: `URL,interval[,http_code]` (e.g. `google.com,30` — `http_code` defaults to `200`).
- Continuous monitor: the CLI starts a long-running loop that checks each host on its configured interval.
- Docker-friendly: the container accepts a `TARGETS` JSON environment variable to declare targets.
- Notifications: integrates with `tglogging` to send messages to Telegram when configured; falls back to console logging otherwise.

## Install

```bash
python -m venv env
source env/bin/activate  # on Windows: env\Scripts\activate
pip install -r requirements.txt
```

## Run locally

```bash
python -m sitecheck -v google.com,30 httpbin.org/status/204,60,204
```

- `-v` / `--verbose` enables more verbose output.
- Each positional target must be `URL,interval[,http_code]`.
- If the URL does not include a scheme, `https://` is added automatically.

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
]' sitecheck
```

The container entrypoint is `src/docker_entry.py`, which validates `TARGETS` and then executes `python -m sitecheck`.

## TARGETS JSON format

`TARGETS` should be a JSON list of objects:

- `host` (string) — URL to check.
- `interval` (integer seconds) — how often to check this endpoint.
- `http_code` (optional integer) — expected HTTP status code. Defaults to `200`.

Example:

```json
[
  {"host":"https://google.com","interval":30},
  {"host":"https://example.com/health","interval":60,"http_code":200}
]
```

## Environment variables

- `TARGETS` — JSON list used by the Docker entrypoint.
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

