from startup_notice.config import (
    DEFAULT_FONT_SIZE,
    DEFAULT_LOCK_DURATION,
    DEFAULT_QUOTE,
    load_config,
)


def test_missing_file_returns_defaults(tmp_path):
    config = load_config(str(tmp_path / "does-not-exist.ini"))
    assert config.tasks == []
    assert config.quote == DEFAULT_QUOTE
    assert config.background_path is None
    assert config.lock_duration_seconds == DEFAULT_LOCK_DURATION
    assert config.font_size == DEFAULT_FONT_SIZE


def test_valid_config_is_parsed(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text(
        "[behavior]\n"
        "lock_duration_seconds = 45\n"
        "[appearance]\n"
        "font_size = 20\n",
        encoding="utf-8",
    )
    config = load_config(str(path))
    assert config.lock_duration_seconds == 45
    assert config.font_size == 20


def test_tasks_file_option_is_used(tmp_path):
    tasks_path = tmp_path / "tasks.txt"
    tasks_path.write_text("Первая задача\n\nВторая задача\n", encoding="utf-8")

    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[message]\n"
        f"tasks_file = {tasks_path.name}\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.tasks == ["Первая задача", "Вторая задача"]


def test_missing_tasks_file_gives_empty_list(tmp_path):
    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[message]\n"
        "tasks_file = does-not-exist.txt\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.tasks == []


def test_phrases_file_option_picks_a_line(tmp_path):
    phrases_path = tmp_path / "phrases.txt"
    phrases_path.write_text("Только одна фраза\n", encoding="utf-8")

    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[message]\n"
        f"phrases_file = {phrases_path.name}\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.quote == "Только одна фраза"


def test_phrases_file_with_multiple_lines_picks_one_of_them(tmp_path):
    phrases = ["Фраза раз", "Фраза два", "Фраза три"]
    phrases_path = tmp_path / "phrases.txt"
    phrases_path.write_text("\n".join(phrases) + "\n", encoding="utf-8")

    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[message]\n"
        f"phrases_file = {phrases_path.name}\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.quote in phrases


def test_background_dir_picks_an_image(tmp_path):
    backgrounds_dir = tmp_path / "backgrounds"
    backgrounds_dir.mkdir()
    (backgrounds_dir / "sunset.jpg").write_bytes(b"fake-jpeg-data")
    (backgrounds_dir / "readme.txt").write_text("не изображение", encoding="utf-8")

    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[appearance]\n"
        "background_dir = backgrounds\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.background_path == str(backgrounds_dir / "sunset.jpg")


def test_background_dir_without_images_gives_none(tmp_path):
    backgrounds_dir = tmp_path / "backgrounds"
    backgrounds_dir.mkdir()
    (backgrounds_dir / "readme.txt").write_text("не изображение", encoding="utf-8")

    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[appearance]\n"
        "background_dir = backgrounds\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.background_path is None


def test_invalid_lock_duration_falls_back_to_default(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text(
        "[behavior]\n"
        "lock_duration_seconds = not-a-number\n",
        encoding="utf-8",
    )
    config = load_config(str(path))
    assert config.lock_duration_seconds == DEFAULT_LOCK_DURATION


def test_out_of_range_lock_duration_falls_back_to_default(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text(
        "[behavior]\n"
        "lock_duration_seconds = -5\n",
        encoding="utf-8",
    )
    config = load_config(str(path))
    assert config.lock_duration_seconds == DEFAULT_LOCK_DURATION


def test_missing_keys_fall_back_to_default_filenames(tmp_path):
    """Старый config.ini (до появления tasks_file/phrases_file/background_dir
    в 1.0.0-5) переживает обновление пакета как %config(noreplace) и не
    содержит этих ключей вовсе — при обновлении пакет всё равно кладёт
    tasks.txt/phrases.txt/backgrounds рядом с config.ini, и ими нужно
    пользоваться, а не молча отключать задачи/фразы/фон."""
    (tmp_path / "tasks.txt").write_text("Задача\n", encoding="utf-8")
    (tmp_path / "phrases.txt").write_text("Фраза\n", encoding="utf-8")
    backgrounds_dir = tmp_path / "backgrounds"
    backgrounds_dir.mkdir()
    (backgrounds_dir / "sunset.jpg").write_bytes(b"fake-jpeg-data")

    config_path = tmp_path / "config.ini"
    config_path.write_text("[behavior]\nlock_duration_seconds = 45\n", encoding="utf-8")

    config = load_config(str(config_path))
    assert config.tasks == ["Задача"]
    assert config.quote == "Фраза"
    assert config.background_path == str(backgrounds_dir / "sunset.jpg")


def test_explicitly_empty_keys_still_disable_the_block(tmp_path):
    (tmp_path / "tasks.txt").write_text("Задача\n", encoding="utf-8")

    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[message]\n"
        "tasks_file =\n"
        "phrases_file =\n"
        "[appearance]\n"
        "background_dir =\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.tasks == []
    assert config.quote == DEFAULT_QUOTE
    assert config.background_path is None


def test_lock_duration_is_computed_from_task_count_by_default(tmp_path):
    tasks_path = tmp_path / "tasks.txt"
    tasks_path.write_text("Раз\nДва\nТри\n", encoding="utf-8")

    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[message]\n"
        f"tasks_file = {tasks_path.name}\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.lock_duration_seconds == 15  # 3 задачи * 5 секунд
    assert config.disabled is False


def test_lock_duration_is_zero_but_not_disabled_when_there_are_no_tasks(tmp_path):
    config_path = tmp_path / "config.ini"
    config_path.write_text("[message]\n", encoding="utf-8")

    config = load_config(str(config_path))
    assert config.tasks == []
    assert config.lock_duration_seconds == 0
    assert config.disabled is False


def test_seconds_per_task_option_overrides_the_default_rate(tmp_path):
    tasks_path = tmp_path / "tasks.txt"
    tasks_path.write_text("Раз\nДва\n", encoding="utf-8")

    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[message]\n"
        f"tasks_file = {tasks_path.name}\n"
        "[behavior]\n"
        "seconds_per_task = 10\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.lock_duration_seconds == 20  # 2 задачи * 10 секунд


def test_explicit_zero_lock_duration_disables_the_window(tmp_path):
    tasks_path = tmp_path / "tasks.txt"
    tasks_path.write_text("Задача\n", encoding="utf-8")

    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[message]\n"
        f"tasks_file = {tasks_path.name}\n"
        "[behavior]\n"
        "lock_duration_seconds = 0\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.lock_duration_seconds == 0
    assert config.disabled is True


def test_explicit_lock_duration_is_used_as_is_and_ignores_task_count(tmp_path):
    tasks_path = tmp_path / "tasks.txt"
    tasks_path.write_text("Раз\nДва\nТри\n", encoding="utf-8")

    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[message]\n"
        f"tasks_file = {tasks_path.name}\n"
        "[behavior]\n"
        "lock_duration_seconds = 45\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.lock_duration_seconds == 45
    assert config.disabled is False


def test_malformed_ini_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text("this is not valid ini [[[", encoding="utf-8")
    config = load_config(str(path))
    assert config.tasks == []
    assert config.quote == DEFAULT_QUOTE
    assert config.lock_duration_seconds == DEFAULT_LOCK_DURATION
