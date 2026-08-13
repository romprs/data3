# redos-startup-notice

Механизм информирования пользователя при старте компьютера (РЕД ОС).

После входа пользователя в графическую сессию (MATE, KDE Plasma, GNOME — X11)
на экране появляется модальное окно с сообщением, текст и время блокировки
которого настраиваются в конфигурационном файле. В окне отображается
обратный отсчёт времени до разблокировки. Пока не истекло настроенное время,
окно нельзя закрыть, свернуть или переключиться на другое приложение. После
истечения времени в окне появляется кнопка закрытия.

## Требования

- РЕД ОС (или другой RPM-дистрибутив на базе systemd), графическая сессия X11.
- Пакеты: `python3-gobject`, `gtk3`, `systemd`.

## Структура проекта

```
packaging/redos-startup-notice.spec  - RPM-спека
src/startup_notice/                  - исходный код приложения (Python3 + PyGObject/GTK3)
data/startup-notice.desktop          - XDG autostart entry (/etc/xdg/autostart)
data/startup-notice.service          - systemd --user unit
data/config.ini.example              - пример конфигурации
tests/                                - модульные тесты
```

## Сборка и установка

```sh
# 1. Собрать источники в tar.gz с ожидаемым spec'ом именем каталога
VERSION=1.0.0
git archive --prefix=redos-startup-notice-$VERSION/ -o \
    ~/rpmbuild/SOURCES/redos-startup-notice-$VERSION.tar.gz HEAD

# 2. Собрать RPM
rpmbuild -ba packaging/redos-startup-notice.spec

# 3. Установить
sudo dnf install ~/rpmbuild/RPMS/noarch/redos-startup-notice-*.rpm
```

Пакет устанавливает:
- `/usr/libexec/startup-notice/` — код приложения;
- `/usr/bin/startup-notice` — точка входа;
- `/etc/xdg/autostart/startup-notice.desktop` — автозапуск при входе пользователя
  (работает единообразно на MATE/KDE Plasma/GNOME);
- `/usr/lib/systemd/user/startup-notice.service` — юнит, который фактически
  запускает приложение (даёт журналирование и единственный инстанс на сессию);
- `/etc/startup-notice/config.ini` — конфигурация (`%config(noreplace)`,
  обновление пакета не затирает изменения администратора).

Запуск после логина устроен так: XDG autostart entry делает
`systemctl --user start startup-notice.service`, а не `enable`, чтобы не зависеть
от состояния per-user enablement и не создавать гонку на старте сессии.

## Конфигурация

`/etc/startup-notice/config.ini`:

```ini
[message]
title = Уведомление
text = Текст сообщения администратора...
; text_file = /etc/startup-notice/message.txt  ; опционально, для длинных/многострочных текстов

[behavior]
lock_duration_seconds = 30
font_size = 16
```

Если файл отсутствует или повреждён, приложение всё равно показывает окно —
с встроенным сообщением по умолчанию, а ошибка парсинга пишется в журнал.
Так организационное уведомление не «теряется» из-за опечатки в конфиге.

## Логи

```sh
journalctl --user -u startup-notice
```

## Как устроена блокировка переключения

WM-хинты (`keep_above`, `skip_taskbar` и т.п.) по-разному соблюдаются разными
DE и сами по себе не гарантируют блокировку. Поэтому вдобавок к ним окно
захватывает клавиатуру и указатель на уровне X11 (`Gdk.Seat.grab`) — тот же
приём, которым пользуются экранные блокировщики (i3lock, light-locker). Пока
захват активен, Alt+Tab, Super, клики по панели задач и другим окнам не
доходят до остальной системы. Это и есть причина, по которой решение годится
только для X11: под Wayland композитор не выдаёт приложениям такие
полномочия по соображениям безопасности.

## Тесты

```sh
python3 -m pytest tests/
```
