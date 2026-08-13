"""Чтение и валидация конфигурации startup-notice."""

import configparser
import logging
import os
from dataclasses import dataclass

log = logging.getLogger("startup_notice")

DEFAULT_CONFIG_PATH = "/etc/startup-notice/config.ini"

DEFAULT_TITLE = "Уведомление"
DEFAULT_TEXT = (
    "Добро пожаловать в систему.\n"
    "Настройте текст сообщения в /etc/startup-notice/config.ini"
)
DEFAULT_LOCK_DURATION = 30
DEFAULT_FONT_SIZE = 16

MIN_LOCK_DURATION = 0
MAX_LOCK_DURATION = 24 * 60 * 60  # 24 часа — разумный верхний предел


@dataclass(frozen=True)
class Config:
    title: str
    text: str
    lock_duration_seconds: int
    font_size: int


def _default_config() -> Config:
    return Config(
        title=DEFAULT_TITLE,
        text=DEFAULT_TEXT,
        lock_duration_seconds=DEFAULT_LOCK_DURATION,
        font_size=DEFAULT_FONT_SIZE,
    )


def _read_text(parser: configparser.ConfigParser, config_dir: str) -> str:
    text_file = parser.get("message", "text_file", fallback=None)
    if text_file:
        path = text_file if os.path.isabs(text_file) else os.path.join(config_dir, text_file)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read().strip()
            if content:
                return content
            log.warning("text_file %s пуст, используется text/дефолт", path)
        except OSError as exc:
            log.warning("Не удалось прочитать text_file %s: %s", path, exc)

    return parser.get("message", "text", fallback=DEFAULT_TEXT).strip() or DEFAULT_TEXT


def _parse_int(parser: configparser.ConfigParser, section: str, option: str,
                default: int, min_value: int, max_value: int) -> int:
    raw = parser.get(section, option, fallback=str(default))
    try:
        value = int(raw)
    except ValueError:
        log.warning("Некорректное значение %s.%s=%r, используется дефолт %d",
                    section, option, raw, default)
        return default

    if value < min_value or value > max_value:
        log.warning("%s.%s=%d вне диапазона [%d, %d], используется дефолт %d",
                    section, option, value, min_value, max_value, default)
        return default
    return value


def load_config(path: str = DEFAULT_CONFIG_PATH) -> Config:
    """Читает конфиг; при отсутствии/ошибке возвращает безопасные дефолты,
    чтобы механизм информирования не переставал работать из-за опечатки."""

    if not os.path.isfile(path):
        log.warning("Конфиг %s не найден, используются значения по умолчанию", path)
        return _default_config()

    parser = configparser.ConfigParser()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            parser.read_file(fh)
    except (OSError, configparser.Error) as exc:
        log.error("Не удалось разобрать конфиг %s: %s. Используются значения по умолчанию", path, exc)
        return _default_config()

    config_dir = os.path.dirname(os.path.abspath(path))

    title = parser.get("message", "title", fallback=DEFAULT_TITLE).strip() or DEFAULT_TITLE
    text = _read_text(parser, config_dir)
    lock_duration = _parse_int(
        parser, "behavior", "lock_duration_seconds",
        DEFAULT_LOCK_DURATION, MIN_LOCK_DURATION, MAX_LOCK_DURATION,
    )
    font_size = _parse_int(parser, "behavior", "font_size", DEFAULT_FONT_SIZE, 6, 96)

    return Config(
        title=title,
        text=text,
        lock_duration_seconds=lock_duration,
        font_size=font_size,
    )
