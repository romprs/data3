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


def test_malformed_ini_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text("this is not valid ini [[[", encoding="utf-8")
    config = load_config(str(path))
    assert config.tasks == []
    assert config.quote == DEFAULT_QUOTE
    assert config.lock_duration_seconds == DEFAULT_LOCK_DURATION
