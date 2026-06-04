import os
import logging
from typing import Dict, List
from tglogging import configure_logger, LoggingConfig

def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


_LEVEL_CHAT_ENV: Dict[int, str] = {
    logging.DEBUG:          'TELEGRAM_CHAT_IDS_DEBUG',
    logging.INFO:           'TELEGRAM_CHAT_IDS_INFO',
    logging.WARNING:        'TELEGRAM_CHAT_IDS_WARNING',
    logging.ERROR:          'TELEGRAM_CHAT_IDS_ERROR',
    logging.CRITICAL:       'TELEGRAM_CHAT_IDS_CRITICAL',
}


def _build_level_chat_ids() -> Dict[int, List[str]]:
    result: Dict[int, List[str]] = {}
    for level, env_var in _LEVEL_CHAT_ENV.items():
        value = _env(env_var, "").strip()
        if value:
            result[level] = [chat_id.strip() for chat_id in value.split(",")]
    return result


def get_tg_logger(name: str = 'sitecheck', verbose: bool = False):
    """Return a logger configured with `tglogging`.
    The first call's `verbose` flag determines the logger level.
    """
    # Cache loggers by name to avoid reconfiguring on repeated calls.
    # The first call determines the logger level (verbose vs not).
    if not hasattr(get_tg_logger, "_cache"):
        get_tg_logger._cache = {}
    cache = get_tg_logger._cache
    if name in cache:
        return cache[name]

    cfg = LoggingConfig(
        log_file_path=_env('LOG_FILE') or None,
        telegram_bot_token=_env('TELEGRAM_BOT_TOKEN') or None,
        level_chat_ids=_build_level_chat_ids(),
    )
    logger = configure_logger(name, cfg, verbose=verbose)
    cache[name] = logger
    return logger
