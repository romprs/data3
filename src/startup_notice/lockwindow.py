"""Окно уведомления, которое нельзя закрыть/свернуть/переключить,
пока не истечёт настроенное время (X11 keyboard+pointer grab)."""

import logging

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from startup_notice.config import Config  # noqa: E402

log = logging.getLogger("startup_notice")

# Периодичность проверки, что захват ввода всё ещё удерживается нашим окном.
GRAB_WATCHDOG_INTERVAL_MS = 1000


class LockWindow(Gtk.Window):
    def __init__(self, config: Config):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self._config = config
        self._locked = False
        self._watchdog_id = None
        self._countdown_timer_id = None
        self._remaining_seconds = 0

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

    def _build_ui(self) -> None:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_margin_start(48)
        outer.set_margin_end(48)

        title_label = Gtk.Label(label=self._config.title)
        title_label.set_line_wrap(True)
        title_label.get_style_context().add_class("title")
        title_label.set_markup(
            f"<span size='xx-large' weight='bold'>{GLib.markup_escape_text(self._config.title)}</span>"
        )

        text_label = Gtk.Label(label=self._config.text)
        text_label.set_line_wrap(True)
        text_label.set_justify(Gtk.Justification.CENTER)
        text_label.set_markup(
            f"<span size='{self._config.font_size * 1000}'>"
            f"{GLib.markup_escape_text(self._config.text)}</span>"
        )

        self._countdown_label = Gtk.Label()
        self._countdown_label.set_halign(Gtk.Align.CENTER)
        self._countdown_label.set_no_show_all(True)

        self._close_button = Gtk.Button(label="Закрыть")
        self._close_button.set_no_show_all(True)
        self._close_button.set_halign(Gtk.Align.CENTER)
        self._close_button.connect("clicked", lambda *_: self._quit())

        outer.pack_start(title_label, False, False, 0)
        outer.pack_start(text_label, False, False, 0)
        outer.pack_start(self._countdown_label, False, False, 0)
        outer.pack_start(self._close_button, False, False, 0)

        self.add(outer)

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
        self._countdown_label.set_markup(
            f"<span size='large'>Окно можно будет закрыть через {minutes:d}:{seconds:02d}</span>"
        )

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
        self._close_button.set_no_show_all(False)
        self._close_button.show()
        log.info("Блокировка снята, доступна кнопка закрытия")
        return False  # не повторять таймер

    def _quit(self) -> None:
        self._release_input()
        Gtk.main_quit()
