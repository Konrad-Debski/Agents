# Instalacja

Wymagania: Linux z systemd użytkownika, Git, Bash, Python 3.11 lub nowszy oraz `flock` z util-linux. Git musi mieć ustawione `user.name` i `user.email`. Pobieranie i wysyłanie do `origin/main`, a także podpisywanie commitów, muszą działać bez interaktywnego logowania.

Repozytorium powinno zajmować katalog `~/.agents`. Nie klonuj go wewnątrz istniejącego `~/.agents/skills`. Przy istniejącej instalacji użyj `apply --dry-run` opisanego poniżej i rozwiąż zgłoszone kolizje.

Na nowym komputerze, jako docelowy użytkownik, bez `sudo`:

```bash
git clone --recurse-submodules git@github.com:Konrad-Debski/Agents.git ~/.agents
bash "$HOME/.agents/scripts/install.sh"
bash "$HOME/.agents/scripts/doctor.sh"
```

Instalator wykrywa harnessy po ich katalogach lub programach w `PATH`. Tworzy konfigurację i uruchamia `agents-sync.timer`. Wykonanie komendy ponownie aktualizuje instalację bez duplikatów. Zmiana lokalizacji repozytorium wymaga ponownej instalacji. Przy istniejących kolizjach najpierw scal własne instrukcje lub nadaj lokalnemu MCP inną nazwę. Instalator nie zastępuje odmiennego pliku instrukcji ani obcego symlinku.

Instalacja samej konfiguracji bez systemd:

```bash
bash "$HOME/.agents/scripts/install.sh" --no-sync --dry-run
bash "$HOME/.agents/scripts/install.sh" --no-sync
```

Skrypty korzystają ze standardowej biblioteki Pythona, bez instalacji pakietów. Automatyczny harmonogram obsługuje obecnie Linux. macOS i Windows nie mają instalatora harmonogramu.

## Wdrażanie i diagnostyka

```bash
bash "$HOME/.agents/scripts/apply.sh" --dry-run
bash "$HOME/.agents/scripts/apply.sh"
bash "$HOME/.agents/scripts/doctor.sh"
```

`--dry-run` nie zapisuje konfiguracji ani stanu. Wdrażanie najpierw sprawdza wszystkie kolizje, następnie zapisuje pliki atomowo i tworzy kopie poprzednich wersji. Obsłużony błąd zapisu powoduje wycofanie wcześniejszych zmian z tego przebiegu. Ręcznie zmienione zarządzane wpisy zatrzymują wdrażanie. Edytuj definicję źródłową zamiast wygenerowanego wpisu.

Nie uruchamiaj wdrażania równocześnie ze zmianą konfiguracji w interfejsie harnessu. Blokada chroni przed drugim procesem `apply`, ale zewnętrzne aplikacje jej nie znają. Nagłe wyłączenie komputera podczas zapisu wielu plików może wymagać odtworzenia ich z kopii zapasowych.

`doctor` sprawdza plan wdrażania, brakujące programy i zmienne środowiskowe, zerwane symlinki oraz stan timera. Nie łączy się z MCP, nie weryfikuje logowania OAuth i nie testuje zachowania modeli.

Ustawienia maszyny i sekrety opisuje [configuration.md](configuration.md), a harmonogram i submoduły [synchronization.md](synchronization.md).
