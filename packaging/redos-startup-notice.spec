Name:           redos-startup-notice
Version:        1.0.0
Release:        3%{?dist}
Summary:        Информационное окно при входе пользователя в систему

License:        MIT
URL:            https://github.com/romprs/data3
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
Requires:       python3-gobject
Requires:       gtk3
Requires:       systemd

%description
Механизм информирования пользователя при старте компьютера. После входа
пользователя в графическую сессию (X11) показывает модальное окно с
настраиваемым сообщением, которое нельзя закрыть, свернуть или
переключить в другое приложение в течение настраиваемого времени. По
истечении этого времени в окне появляется кнопка закрытия. Текст
сообщения и время блокировки задаются в /etc/startup-notice/config.ini.

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

%files
%{_bindir}/startup-notice
%{python3_sitelib}/startup_notice/
%{_sysconfdir}/xdg/autostart/startup-notice.desktop
%{_prefix}/lib/systemd/user/startup-notice.service
%config(noreplace) %{_sysconfdir}/startup-notice/config.ini

%changelog
* Thu Aug 13 2026 romprs <romprs@gmail.com> - 1.0.0-3
- Добавлен обратный отсчёт времени до разблокировки окна

* Thu Aug 13 2026 romprs <romprs@gmail.com> - 1.0.0-2
- Исправлено имя зависимости: python3-gobject3 -> python3-gobject

* Thu Aug 13 2026 romprs <romprs@gmail.com> - 1.0.0-1
- Первый релиз: информационное окно при входе пользователя
