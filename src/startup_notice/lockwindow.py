"""Окно уведомления, которое нельзя закрыть/свернуть/переключить,
пока не истечёт настроенное время (X11 keyboard+pointer grab)."""

import getpass
import logging
import pwd
from datetime import datetime

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

from startup_notice.config import Config  # noqa: E402

log = logging.getLogger("startup_notice")

# Периодичность проверки, что захват ввода всё ещё удерживается нашим окном.
GRAB_WATCHDOG_INTERVAL_MS = 1000

# Сколько задач показывать списком под заголовком «Задачи N».
MAX_VISIBLE_TASKS = 5

_MONTHS_RU = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)
_WEEKDAYS_RU = (
    "понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье",
)

_STYLE_CSS = b"""
.header-date {
    color: #ffffff;
    font-weight: 700;
    letter-spacing: 2px;
}
.countdown-badge {
    color: #ffffff;
    background-color: alpha(#ffffff, 0.18);
    border-radius: 14px;
    padding: 4px 14px;
}
.avatar {
    color: #ffffff;
    background-color: alpha(#ffffff, 0.25);
    border-radius: 999px;
    font-weight: 700;
}
.greeting {
    color: #ffffff;
    font-weight: 600;
}
.tasks-header {
    color: #ffffff;
    font-weight: 600;
    font-size: 20px;
}
.task-item {
    color: alpha(#ffffff, 0.85);
    font-size: 16px;
}
.quote-label {
    color: alpha(#ffffff, 0.75);
    font-style: italic;
}
.quote-text {
    color: #ffffff;
    font-style: italic;
}
.proceed-button {
    border-radius: 20px;
    padding: 10px 34px;
    font-weight: 700;
    background-image: none;
    background-color: #3b6ff2;
    color: #ffffff;
    border: none;
    box-shadow: none;
}
.proceed-button:hover {
    background-color: #4d7bf5;
}
.proceed-button label {
    color: #ffffff;
}
"""


def _current_date_header() -> str:
    now = datetime.now()
    return f"{now.day} {_MONTHS_RU[now.month - 1].upper()}, {_WEEKDAYS_RU[now.weekday()].upper()}"


def _time_of_day_greeting() -> str:
    hour = datetime.now().hour
    if 4 <= hour < 12:
        return "Доброе утро"
    if 12 <= hour < 18:
        return "Добрый день"
    if 18 <= hour < 23:
        return "Добрый вечер"
    return "Доброй ночи"


def _display_name() -> str:
    """Имя пользователя для приветствия: первое слово из GECOS (полное имя
    из учётной записи), а если его нет — системный логин."""
    login = getpass.getuser()
    try:
        gecos = pwd.getpwnam(login).pw_gecos or ""
        words = gecos.split(",")[0].strip().split()
        if words:
            return words[0]
    except KeyError:
        pass
    return login


_DEFAULT_SCRIM = (0.03, 0.07, 0.16)


def _load_background_pixbuf(path):
    if not path:
        return None
    try:
        return GdkPixbuf.Pixbuf.new_from_file(path)
    except GLib.Error as exc:
        log.warning("Не удалось загрузить фоновое изображение %s: %s", path, exc)
        return None


def _scrim_color(pixbuf):
    """Подбирает тёмный оттенок под тон конкретного фото: усредняет цвет
    его левой половины (там, где ложится текст) и затемняет — так градиент
    всегда сочетается с фото, а не выглядит чужеродной синей плашкой поверх
    любого изображения."""
    if pixbuf is None:
        return _DEFAULT_SCRIM
    try:
        small = pixbuf.scale_simple(40, 24, GdkPixbuf.InterpType.BILINEAR)
    except GLib.Error:
        return _DEFAULT_SCRIM
    if small is None:
        return _DEFAULT_SCRIM

    data = small.get_pixels()
    stride = small.get_rowstride()
    n_channels = small.get_n_channels()
    width, height = small.get_width(), small.get_height()
    sample_width = max(1, width // 2)

    r_sum = g_sum = b_sum = 0
    count = 0
    for y in range(height):
        row = y * stride
        for x in range(sample_width):
            offset = row + x * n_channels
            r_sum += data[offset]
            g_sum += data[offset + 1]
            b_sum += data[offset + 2]
            count += 1

    if count == 0:
        return _DEFAULT_SCRIM

    darken = 0.35
    cap = 0.22
    return (
        min(r_sum / count / 255 * darken, cap),
        min(g_sum / count / 255 * darken, cap),
        min(b_sum / count / 255 * darken, cap),
    )


class _BackgroundArea(Gtk.DrawingArea):
    """Рисует фоновое изображение с заполнением всей области (cover-fit)
    и тёмный градиент слева направо для читаемости текста поверх фото.
    Правая часть остаётся светлой, чтобы само изображение было хорошо видно."""

    def __init__(self, pixbuf):
        super().__init__()
        self._pixbuf = pixbuf
        self._scrim = _scrim_color(pixbuf)
        self.connect("draw", self._on_draw)

    def _on_draw(self, widget, cr):
        alloc = widget.get_allocation()
        width, height = alloc.width, alloc.height

        cr.set_source_rgb(*self._scrim)
        cr.paint()

        if self._pixbuf is not None:
            pw, ph = self._pixbuf.get_width(), self._pixbuf.get_height()
            scale = max(width / pw, height / ph)
            offset_x = (width - pw * scale) / 2
            offset_y = (height - ph * scale) / 2
            cr.save()
            cr.translate(offset_x, offset_y)
            cr.scale(scale, scale)
            Gdk.cairo_set_source_pixbuf(cr, self._pixbuf, 0, 0)
            cr.paint()
            cr.restore()

        r, g, b = self._scrim
        gradient = cairo.LinearGradient(0, 0, width * 0.6, 0)
        gradient.add_color_stop_rgba(0, r, g, b, 0.82)
        gradient.add_color_stop_rgba(1, r, g, b, 0.0)
        cr.set_source(gradient)
        cr.rectangle(0, 0, width, height)
        cr.fill()
        return False


class LockWindow(Gtk.Window):
    def __init__(self, config: Config):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self._config = config
        self._locked = False
        self._watchdog_id = None
        self._countdown_timer_id = None
        self._remaining_seconds = 0

        self._apply_css()
        self._build_ui()

        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.stick()
        self.fullscreen()

        self.connect("delete-event", self._on_delete_event)
        self.connect("focus-out-event", self._on_focus_out)
        self.connect("realize", self._on_realize)

    def _apply_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(_STYLE_CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self) -> None:
        pixbuf = _load_background_pixbuf(self._config.background_path)
        background = _BackgroundArea(pixbuf)

        overlay = Gtk.Overlay()
        overlay.add(background)
        overlay.add_overlay(self._build_content())
        overlay.add_overlay(self._build_countdown_badge())
        overlay.add_overlay(self._build_proceed_button())
        self.add(overlay)

    def _build_content(self) -> Gtk.Widget:
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=28)
        content.set_halign(Gtk.Align.START)
        content.set_valign(Gtk.Align.FILL)
        content.set_margin_start(56)
        content.set_margin_end(56)
        content.set_margin_top(40)
        content.set_margin_bottom(48)
        content.set_size_request(560, -1)

        content.pack_start(self._build_header_row(), False, False, 0)
        content.pack_start(self._build_greeting_row(), False, False, 0)

        tasks_widget = self._build_tasks_section()
        if tasks_widget is not None:
            content.pack_start(tasks_widget, False, False, 0)

        spacer = Gtk.Box()
        content.pack_start(spacer, True, True, 0)

        content.pack_start(self._build_quote_section(), False, False, 0)

        return content

    def _build_header_row(self) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        date_label = Gtk.Label(label=_current_date_header())
        date_label.get_style_context().add_class("header-date")
        date_label.set_halign(Gtk.Align.START)
        row.pack_start(date_label, True, True, 0)

        return row

    def _build_countdown_badge(self) -> Gtk.Widget:
        # Отдельный оверлей-виджет (не часть узкой текстовой колонки),
        # поэтому таймер всегда в правом верхнем углу всего экрана.
        self._countdown_label = Gtk.Label()
        self._countdown_label.get_style_context().add_class("countdown-badge")
        self._countdown_label.set_halign(Gtk.Align.END)
        self._countdown_label.set_valign(Gtk.Align.START)
        self._countdown_label.set_margin_top(40)
        self._countdown_label.set_margin_end(56)
        self._countdown_label.set_no_show_all(True)
        return self._countdown_label

    def _build_proceed_button(self) -> Gtk.Widget:
        # Отдельный оверлей-виджет, чтобы кнопка была по центру внизу
        # всего экрана, а не только центру узкой текстовой колонки.
        self._proceed_button = Gtk.Button(label="Вперёд!")
        self._proceed_button.get_style_context().add_class("proceed-button")
        self._proceed_button.set_halign(Gtk.Align.CENTER)
        self._proceed_button.set_valign(Gtk.Align.END)
        self._proceed_button.set_margin_bottom(64)
        self._proceed_button.set_no_show_all(True)
        self._proceed_button.connect("clicked", lambda *_: self._quit())
        return self._proceed_button

    def _build_greeting_row(self) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)

        name = _display_name()

        avatar = Gtk.Label(label=name[:1].upper())
        avatar.get_style_context().add_class("avatar")
        avatar.set_size_request(56, 56)
        avatar.set_halign(Gtk.Align.CENTER)
        avatar.set_valign(Gtk.Align.CENTER)
        row.pack_start(avatar, False, False, 0)

        greeting = Gtk.Label()
        greeting.get_style_context().add_class("greeting")
        greeting.set_halign(Gtk.Align.START)
        greeting.set_justify(Gtk.Justification.LEFT)
        greeting.set_markup(
            f"<span size='{self._config.font_size * 1300}'>"
            f"{GLib.markup_escape_text(_time_of_day_greeting())},\n"
            f"{GLib.markup_escape_text(name)}</span>"
        )
        row.pack_start(greeting, False, False, 0)

        return row

    def _build_tasks_section(self):
        tasks = self._config.tasks
        if not tasks:
            return None

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        header = Gtk.Label()
        header.get_style_context().add_class("tasks-header")
        header.set_halign(Gtk.Align.START)
        header.set_markup(f"☑ Задачи {len(tasks)}")
        box.pack_start(header, False, False, 0)

        for task in tasks[:MAX_VISIBLE_TASKS]:
            item = Gtk.Label(label=f"·  {task}")
            item.get_style_context().add_class("task-item")
            item.set_halign(Gtk.Align.START)
            item.set_line_wrap(True)
            box.pack_start(item, False, False, 0)

        remaining = len(tasks) - MAX_VISIBLE_TASKS
        if remaining > 0:
            more = Gtk.Label(label=f"…и ещё {remaining}")
            more.get_style_context().add_class("task-item")
            more.set_halign(Gtk.Align.START)
            box.pack_start(more, False, False, 0)

        return box

    def _build_quote_section(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_bottom(72)

        label = Gtk.Label(label="Мысль дня")
        label.get_style_context().add_class("quote-label")
        label.set_halign(Gtk.Align.START)
        box.pack_start(label, False, False, 0)

        quote = Gtk.Label(label=self._config.quote)
        quote.get_style_context().add_class("quote-text")
        quote.set_halign(Gtk.Align.START)
        quote.set_justify(Gtk.Justification.LEFT)
        quote.set_line_wrap(True)
        quote.set_markup(
            f"<span size='{self._config.font_size * 1150}'>"
            f"{GLib.markup_escape_text(self._config.quote)}</span>"
        )
        box.pack_start(quote, False, False, 0)

        return box

    # -- захват ввода -----------------------------------------------------

    def _on_realize(self, *_args) -> None:
        self._grab_input()

    def _grab_input(self) -> bool:
        """Пытается захватить клавиатуру и указатель на уровне X11.
        Возвращает True, если захват удался."""
        display = Gdk.Display.get_default()
        seat = display.get_default_seat()
        gdk_window = self.get_window()
        if gdk_window is None:
            return False

        status = seat.grab(
            gdk_window,
            Gdk.SeatCapabilities.ALL,
            False,  # owner_events: не пропускать события другим окнам
            None,
            None,
            None,
            None,
        )
        if status != Gdk.GrabStatus.SUCCESS:
            log.warning("Не удалось захватить ввод (status=%s), повтор позже", status)
            return False
        return True

    def _release_input(self) -> None:
        display = Gdk.Display.get_default()
        seat = display.get_default_seat()
        seat.ungrab()

    def _grab_watchdog(self) -> bool:
        if not self._locked:
            return False  # остановить таймер
        self._grab_input()
        return True  # продолжать проверять

    def _on_focus_out(self, *_args) -> bool:
        if self._locked:
            GLib.idle_add(self.present)
            GLib.idle_add(self._grab_input)
        return False

    def _on_delete_event(self, *_args) -> bool:
        # Пока заблокировано — игнорировать попытку закрыть окно.
        return self._locked

    # -- жизненный цикл блокировки ----------------------------------------

    def activate_lock(self) -> None:
        # В норме при lock_duration_seconds<=0 окно вообще не создаётся
        # (см. __main__.py); эта ветка — защитный fallback на случай
        # прямого вызова activate_lock() в обход точки входа.
        duration = self._config.lock_duration_seconds
        if duration <= 0:
            log.info("lock_duration_seconds=0, окно сразу разблокировано")
            self._unlock()
            return

        self._locked = True
        self._remaining_seconds = duration
        self._update_countdown_label()
        self._countdown_label.set_no_show_all(False)
        self._countdown_label.show()

        self._watchdog_id = GLib.timeout_add(GRAB_WATCHDOG_INTERVAL_MS, self._grab_watchdog)
        self._countdown_timer_id = GLib.timeout_add_seconds(1, self._on_countdown_tick)
        log.info("Блокировка активна на %d сек.", duration)

    def _update_countdown_label(self) -> None:
        minutes, seconds = divmod(max(self._remaining_seconds, 0), 60)
        self._countdown_label.set_markup(f"{minutes:d}:{seconds:02d}")

    def _on_countdown_tick(self) -> bool:
        self._remaining_seconds -= 1
        if self._remaining_seconds <= 0:
            self._unlock()
            return False  # не повторять таймер
        self._update_countdown_label()
        return True

    def _unlock(self) -> bool:
        self._locked = False
        if self._countdown_timer_id is not None:
            GLib.source_remove(self._countdown_timer_id)
            self._countdown_timer_id = None
        self._countdown_label.hide()
        self._release_input()
        self._proceed_button.set_no_show_all(False)
        self._proceed_button.show()
        log.info("Блокировка снята, доступна кнопка «Вперёд!»")
        return False  # не повторять таймер

    def _quit(self) -> None:
        self._release_input()
        Gtk.main_quit()
