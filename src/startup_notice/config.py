"""Чтение и валидация конфигурации startup-notice."""

import configparser
import logging
import os
import random
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger("startup_notice")

DEFAULT_CONFIG_PATH = "/etc/startup-notice/config.ini"

DEFAULT_QUOTE = "Настройте фразы дня в файле, указанном в phrases_file."
DEFAULT_LOCK_DURATION = 30
DEFAULT_SECONDS_PER_TASK = 5
DEFAULT_FONT_SIZE = 16

MIN_LOCK_DURATION = 0
MAX_LOCK_DURATION = 24 * 60 * 60  # 24 часа — разумный верхний предел

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")

DEFAULT_TASKS_FILENAME = "tasks.txt"
DEFAULT_PHRASES_FILENAME = "phrases.txt"
DEFAULT_BACKGROUND_DIRNAME = "backgrounds"


@dataclass(frozen=True)
class Config:
    lock_duration_seconds: int
    font_size: int
    tasks: List[str] = field(default_factory=list)
    quote: str = DEFAULT_QUOTE
    background_path: Optional[str] = None
    # True только когда администратор явно прописал lock_duration_seconds
    # в конфиге (в т.ч. <= 0, чтобы полностью отключить показ окна). Когда
    # длительность вместо этого вычисляется по числу задач и получается 0
    # (задач нет), это НЕ отключение — окно всё равно показывается, просто
    # сразу разблокированным (см. __main__.py).
    disabled: bool = False


def _default_config() -> Config:
    return Config(
        lock_duration_seconds=DEFAULT_LOCK_DURATION,
        font_size=DEFAULT_FONT_SIZE,
        tasks=[],
        quote=DEFAULT_QUOTE,
        background_path=None,
        disabled=False,
    )


def _resolve_path(config_dir: str, raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    return raw if os.path.isabs(raw) else os.path.join(config_dir, raw)


def _read_lines(path: Optional[str]) -> List[str]:
    if not path:
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip()]
    except OSError as exc:
        log.warning("Не удалось прочитать файл %s: %s", path, exc)
        return []


def _pick_background(background_dir: Optional[str]) -> Optional[str]:
    if not background_dir:
        return None
    try:
        names = os.listdir(background_dir)
    except OSError as exc:
        log.warning("Не удалось прочитать каталог фонов %s: %s", background_dir, exc)
        return None

    candidates = [
        os.path.join(background_dir, name)
        for name in names
        if name.lower().endswith(IMAGE_EXTENSIONS)
    ]
    if not candidates:
        log.warning("В каталоге фонов %s нет изображений", background_dir)
        return None
    return random.choice(candidates)


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

    # fallback — не None, а имя файла/каталога, которые ставит пакет рядом
    # с config.ini: старые конфиги (до появления этих ключей в 1.0.0-5)
    # сохраняются при обновлении пакета как %config(noreplace) и не содержат
    # этих опций вовсе — без дефолта по умолчанию задачи/фразы/фон молча
    # переставали бы работать после обновления. Пустое значение, наоборот,
    # означает осознанный отказ администратора от блока и по-прежнему
    # отключает его (см. _resolve_path).
    tasks_file = _resolve_path(
        config_dir, parser.get("message", "tasks_file", fallback=DEFAULT_TASKS_FILENAME)
    )
    phrases_file = _resolve_path(
        config_dir, parser.get("message", "phrases_file", fallback=DEFAULT_PHRASES_FILENAME)
    )
    background_dir = _resolve_path(
        config_dir, parser.get("appearance", "background_dir", fallback=DEFAULT_BACKGROUND_DIRNAME)
    )

    tasks = _read_lines(tasks_file)

    phrases = _read_lines(phrases_file)
    quote = random.choice(phrases) if phrases else DEFAULT_QUOTE

    background_path = _pick_background(background_dir)

    # Если lock_duration_seconds явно прописан в конфиге — это осознанный
    # выбор администратора (в т.ч. 0, чтобы полностью отключить показ окна),
    # он и используется как есть. Если ключа нет вовсе — время блокировки
    # автоматически считается по числу задач (по умолчанию 5 секунд на
    # задачу; нет задач — 0, окно сразу разблокировано, но не скрыто).
    if parser.has_section("behavior") and parser.has_option("behavior", "lock_duration_seconds"):
        lock_duration = _parse_int(
            parser, "behavior", "lock_duration_seconds",
            DEFAULT_LOCK_DURATION, MIN_LOCK_DURATION, MAX_LOCK_DURATION,
        )
        disabled = lock_duration <= 0
    else:
        seconds_per_task = _parse_int(
            parser, "behavior", "seconds_per_task",
            DEFAULT_SECONDS_PER_TASK, 0, MAX_LOCK_DURATION,
        )
        lock_duration = min(seconds_per_task * len(tasks), MAX_LOCK_DURATION)
        disabled = False

    font_size = _parse_int(parser, "appearance", "font_size", DEFAULT_FONT_SIZE, 6, 96)

    return Config(
        lock_duration_seconds=lock_duration,
        font_size=font_size,
        tasks=tasks,
        quote=quote,
        background_path=background_path,
        disabled=disabled,
    )
