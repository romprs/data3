"""Точка входа startup-notice."""

import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from startup_notice.config import DEFAULT_CONFIG_PATH, load_config  # noqa: E402
from startup_notice.log import setup_logging  # noqa: E402
from startup_notice.lockwindow import LockWindow  # noqa: E402


def main() -> int:
    log = setup_logging()
    log.info("startup-notice запускается")

    config = load_config(DEFAULT_CONFIG_PATH)
    log.info(
        "Конфигурация: lock_duration=%ds, задач=%d, фон=%s",
        config.lock_duration_seconds,
        len(config.tasks),
        config.background_path or "нет",
    )

    if config.lock_duration_seconds <= 0:
        log.info("lock_duration_seconds=0, показ окна отключён администратором")
        return 0

    window = LockWindow(config)
    window.show_all()
    window.activate_lock()

    Gtk.main()
    log.info("startup-notice завершается")
    return 0


if __name__ == "__main__":
    sys.exit(main())
