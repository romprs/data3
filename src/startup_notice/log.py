"""Настройка логирования: в journal при наличии systemd, иначе в stderr."""

import logging


def setup_logging() -> logging.Logger:
    log = logging.getLogger("startup_notice")
    log.setLevel(logging.INFO)

    handler = None
    try:
        from systemd.journal import JournalHandler
        handler = JournalHandler(SYSLOG_IDENTIFIER="startup-notice")
    except ImportError:
        pass

    if handler is None:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s startup-notice: %(message)s"))

    log.addHandler(handler)
    return log
