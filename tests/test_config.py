from startup_notice.config import (
    DEFAULT_FONT_SIZE,
    DEFAULT_LOCK_DURATION,
    DEFAULT_TEXT,
    DEFAULT_TITLE,
    load_config,
)


def test_missing_file_returns_defaults(tmp_path):
    config = load_config(str(tmp_path / "does-not-exist.ini"))
    assert config.title == DEFAULT_TITLE
    assert config.text == DEFAULT_TEXT
    assert config.lock_duration_seconds == DEFAULT_LOCK_DURATION
    assert config.font_size == DEFAULT_FONT_SIZE


def test_valid_config_is_parsed(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text(
        "[message]\n"
        "title = Важно\n"
        "text = Проверьте расписание работ\n"
        "[behavior]\n"
        "lock_duration_seconds = 45\n"
        "font_size = 20\n",
        encoding="utf-8",
    )
    config = load_config(str(path))
    assert config.title == "Важно"
    assert config.text == "Проверьте расписание работ"
    assert config.lock_duration_seconds == 45
    assert config.font_size == 20


def test_text_file_option_is_used(tmp_path):
    message_path = tmp_path / "message.txt"
    message_path.write_text("Многострочный\nтекст сообщения", encoding="utf-8")

    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[message]\n"
        "title = Уведомление\n"
        f"text_file = {message_path.name}\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.text == "Многострочный\nтекст сообщения"


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
    assert config.title == DEFAULT_TITLE
    assert config.lock_duration_seconds == DEFAULT_LOCK_DURATION
