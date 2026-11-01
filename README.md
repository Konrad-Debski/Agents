# Agent skills

Osobista kolekcja skilli dla agentów AI, współdzielona między komputerami.

## Instalacja przez agenta

Skrócone zasady pracy dla agentów zawiera [AGENTS.md](AGENTS.md). Instrukcje instalacji i synchronizacji znajdują się poniżej.

Po sklonowaniu uruchom jedną komendę z sekcji [Automatyczna synchronizacja](#automatyczna-synchronizacja). Instaluje ona `git-sync` oraz usługę i timer systemd użytkownika.

## Skille

- [create-pr](create-pr/SKILL.md): tworzenie i scalanie pull requestów przez GitHub CLI.
- [famicord-sync](famicord-sync/SKILL.md): synchronizacja motywów WordPress między projektami Famicord.
- [figma](figma/SKILL.md): brief implementacji sekcji WordPress/ACF na podstawie Figmy.
- [unslop](unslop/SKILL.md): usuwanie charakterystycznych zwrotów AI z tekstu.
- [wordpress-audit](wordpress-audit/SKILL.md): sprawdzanie plików i bazy WordPress pod kątem infekcji.
- [wp-update](wp-update/SKILL.md): aktualizacja WordPressa, wtyczek i ACF Pro.
- [wp-update-list](wp-update-list/SKILL.md): porządkowanie list aktualizacji WordPressa.

## Submoduły

`.upstream/cursor-plugins` zawiera repozytorium [cursor/plugins](https://github.com/cursor/plugins), śledzące gałąź `main`. Katalog `unslop` jest symlinkiem do skilla w tym submodule.

`.upstream/git-sync` zawiera repozytorium [simonthum/git-sync](https://github.com/simonthum/git-sync), śledzące gałąź `master`. Instalator i usługa synchronizacji automatycznie aktualizują ten submoduł do najnowszej wersji źródłowej. Usługa zapisuje zmianę jego wskazania w repozytorium skilli.

## Klonowanie

Poniższe polecenie zakłada, że katalog docelowy nie istnieje. Jeśli zawiera już kopię tego repozytorium, skorzystaj z sekcji pobierania zmian. Jeśli zawiera inne skille lub inne repozytorium, zachowaj je, sklonuj to repozytorium do osobnego katalogu i połącz zawartość bez utraty lokalnych plików.

```bash
git clone --recurse-submodules git@github.com:KonradDebski/agent-skills.git ~/.agents/skills
```

## Automatyczna synchronizacja

Na każdej maszynie z Linuksem wykonaj jako docelowy użytkownik, bez `sudo`:

```bash
bash "$HOME/.agents/skills/scripts/install-sync.sh"
```

Wymagane są Git, Bash, `flock` z util-linux oraz działający systemd użytkownika. Gałąź `main` musi śledzić `origin/main`. Git musi mieć ustawione `user.name` i `user.email`, a dostęp do repozytorium musi pozwalać na pobieranie i wysyłanie zmian bez interaktywnego logowania. Jeśli korzystasz z podpisywania commitów, klucz także musi być dostępny dla usługi bez pytania o hasło.

Instalator inicjalizuje submoduły, aktualizuje `.upstream/git-sync` do najnowszej wersji z gałęzi `master` i tworzy `agent-skills-sync.service` oraz `agent-skills-sync.timer` w katalogu konfiguracji systemd użytkownika. Włącza uwzględnianie nowych plików oraz wysyłanie do `origin/main`. Lokalny katalog `agent-skills-sync` wewnątrz katalogu Git przechowuje blokadę i stan aktualizacji submodułów.

Tę samą komendę można wykonać ponownie. Pobierze aktualny `git-sync` i odtworzy konfigurację usług. Zmiana ścieżki instalacji repozytorium również wymaga ponownego uruchomienia instalatora.

Pierwsza synchronizacja rusza po około minucie od włączenia timera. Kolejne uruchomienia następują co 15 minut od zakończenia poprzedniej synchronizacji. Usługa automatycznie zapisuje zmodyfikowane, nowe i usunięte pliki, z uwzględnieniem `.gitignore`, pobiera zmiany oraz wysyła lokalne commity. Brak zmian oznacza brak nowego commita. Commit może powstać w trakcie edycji. Na gałęziach innych niż `main` usługa pomija synchronizację.

Przed każdym przebiegiem usługa aktualizuje `.upstream/git-sync` przez `--remote` do najnowszego `master`, a następnie uruchamia tę wersję narzędzia. Nowe wskazanie submodułu zapisuje razem z pozostałymi zmianami. Jeśli upstream się nie zmienił, samo sprawdzenie nie tworzy commita. Po udanej synchronizacji usługa ustawia wszystkie submoduły na wersje zapisane w repozytorium. Dla `.upstream/cursor-plugins` nadal obowiązuje zapisana wersja, bez automatycznego `--remote`.

Niezapisane zmiany wewnątrz submodułu zatrzymują synchronizację. Własne zmiany w takim repozytorium trzeba najpierw zapisać i wysłać do jego zdalnego repozytorium. Nie wprowadzaj własnych commitów w `.upstream/git-sync`, ponieważ automatyczna aktualizacja ustawia go na źródłowy `master`.

Instalator próbuje włączyć pozostawienie systemd użytkownika po wylogowaniu przez `loginctl enable-linger`. Jeśli system odmówi, wyświetli polecenie do wykonania przez administratora. Przy korzystaniu z agenta SSH instalator przekazuje do systemd bieżące `SSH_AUTH_SOCK`. Po zmianie agenta uruchom instalator ponownie. Po restarcie maszyny uwierzytelnianie musi być dostępne także dla sesji działającej w tle.

Stan timera i logi:

```bash
systemctl --user status agent-skills-sync.timer
journalctl --user -u agent-skills-sync.service -n 50 --no-pager
```

Natychmiastowa synchronizacja:

```bash
systemctl --user start agent-skills-sync.service
```

Wyłączenie automatycznej synchronizacji:

```bash
systemctl --user disable --now agent-skills-sync.timer
systemctl --user stop agent-skills-sync.service
```

Błąd sieci lub konflikt trafi do logów. Timer ponowi próbę w kolejnym terminie, ale konflikt wymaga rozwiązania i zakończenia operacji Git. Nie trzeba ponownie instalować usługi. Po rozwiązaniu problemu można uruchomić ją od razu poleceniem podanym powyżej.

## Pobieranie zmian

Pobranie zmian repozytorium i zapisanej w nim wersji submodułu:

```bash
cd ~/.agents/skills
git pull --ff-only &&
git submodule update --init --recursive
```

Pobranie najnowszej wersji `unslop` ze źródłowej gałęzi `main`:

```bash
git submodule update --init --remote --checkout -- .upstream/cursor-plugins
```

Polecenie wykonaj w katalogu repozytorium. Aby udostępnić tę wersję innym komputerom, zapisz zmianę wskazania submodułu w commicie i wykonaj `git push`.
