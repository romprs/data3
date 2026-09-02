Name:           redos-startup-notice
Version:        1.0.0
Release:        8%{?dist}
Summary:        Информационное окно при входе пользователя в систему

License:        MIT
URL:            https://github.com/romprs/data3
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
Requires:       python3-gobject
Requires:       python3-cairo
Requires:       gtk3
Requires:       systemd

%description
Механизм информирования пользователя при старте компьютера. После входа
пользователя в графическую сессию (X11) показывает модальное окно с
персональным приветствием, списком задач, фразой дня и фоновым
изображением, которое нельзя закрыть, свернуть или переключить в другое
приложение в течение настраиваемого времени. По истечении этого времени
в окне появляется кнопка «Вперёд!». Задачи, фразы, фон и время блокировки
задаются в /etc/startup-notice/config.ini.

%prep
%setup -q

%build
# чистый Python, сборка не требуется

%install
rm -rf %{buildroot}

install -Dm755 bin/startup-notice %{buildroot}%{_bindir}/startup-notice

install -d %{buildroot}%{python3_sitelib}/startup_notice
install -pm644 src/startup_notice/*.py %{buildroot}%{python3_sitelib}/startup_notice/

install -Dm644 data/startup-notice.desktop \
    %{buildroot}%{_sysconfdir}/xdg/autostart/startup-notice.desktop
install -Dm644 data/startup-notice.service \
    %{buildroot}%{_prefix}/lib/systemd/user/startup-notice.service
install -Dm644 data/config.ini.example \
    %{buildroot}%{_sysconfdir}/startup-notice/config.ini
install -Dm644 data/tasks.txt.example \
    %{buildroot}%{_sysconfdir}/startup-notice/tasks.txt
install -Dm644 data/phrases.txt.example \
    %{buildroot}%{_sysconfdir}/startup-notice/phrases.txt

install -d %{buildroot}%{_sysconfdir}/startup-notice/backgrounds
install -pm644 data/backgrounds/*.jpg \
    %{buildroot}%{_sysconfdir}/startup-notice/backgrounds/

%files
%{_bindir}/startup-notice
%{python3_sitelib}/startup_notice/
%{_sysconfdir}/xdg/autostart/startup-notice.desktop
%{_prefix}/lib/systemd/user/startup-notice.service
%config(noreplace) %{_sysconfdir}/startup-notice/config.ini
%config(noreplace) %{_sysconfdir}/startup-notice/tasks.txt
%config(noreplace) %{_sysconfdir}/startup-notice/phrases.txt
%{_sysconfdir}/startup-notice/backgrounds/
%doc data/backgrounds/SOURCES.md

%changelog
* Thu Sep 03 2026 romprs <romprs@gmail.com> - 1.0.0-8
- tasks.txt и phrases.txt теперь ставятся как реальные файлы
  (/etc/startup-notice/{tasks,phrases}.txt, config noreplace), а не
  только как примеры в документации — после установки ПО сразу готово
  к работе со своим демонстрационным контентом, без ручных шагов

* Thu Sep 03 2026 romprs <romprs@gmail.com> - 1.0.0-7
- Исправлен блёклый текст на кнопке «Вперёд!»: системная тема
  переопределяла цвет надписи внутри кнопки собственным правилом для
  `button label`, из-за чего белый цвет из нашего CSS не применялся;
  добавлен явный селектор `.proceed-button label`

* Thu Sep 03 2026 romprs <romprs@gmail.com> - 1.0.0-6
- Кнопка «Вперёд!» теперь строго по центру экрана (не по центру текстовой колонки)
- Таймер обратного отсчёта — самостоятельный виджет в правом верхнем углу экрана
- Увеличен размер шрифта заголовка и пунктов списка задач
- Тёмный градиент поверх фото теперь подбирается под тон конкретного
  изображения (усреднение цвета + затемнение), а не фиксированный синий
- В комплект добавлены 5 фоновых фотографий (Pexels License, см.
  data/backgrounds/SOURCES.md) — используются по умолчанию из коробки

* Thu Sep 03 2026 romprs <romprs@gmail.com> - 1.0.0-5
- Новый вид окна: дата/приветствие по системному пользователю, список
  задач и фраза дня из файлов, случайный фон из каталога изображений
- Конфиг переработан: title/text/text_file заменены на tasks_file,
  phrases_file и background_dir; font_size перенесён в [appearance]
- Новая зависимость: python3-cairo (нужна для отрисовки фона)

* Thu Aug 13 2026 romprs <romprs@gmail.com> - 1.0.0-4
- lock_duration_seconds=0 теперь полностью отключает показ окна

* Thu Aug 13 2026 romprs <romprs@gmail.com> - 1.0.0-3
- Добавлен обратный отсчёт времени до разблокировки окна

* Thu Aug 13 2026 romprs <romprs@gmail.com> - 1.0.0-2
- Исправлено имя зависимости: python3-gobject3 -> python3-gobject

* Thu Aug 13 2026 romprs <romprs@gmail.com> - 1.0.0-1
- Первый релиз: информационное окно при входе пользователя
