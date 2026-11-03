# Migracja z repozytorium skilli

Migrację wykonaj po opublikowaniu nowego układu repozytorium. Przed rozpoczęciem zatrzymaj stare timery na wszystkich komputerach. Stare instalacje nie powinny samodzielnie pobierać przebudowanej struktury do `~/.agents/skills`.

## Przygotowanie każdego komputera

```bash
systemctl --user disable --now agent-skills-sync.timer
systemctl --user stop agent-skills-sync.service
```

Sprawdź stan starego repozytorium i submodułów. Zachowaj lokalne zmiany. Nie wykonuj resetu ani czyszczenia katalogów.

```bash
git -C ~/.agents/skills status --short
git -C ~/.agents/skills submodule foreach --recursive git status --short
```

Zapisz i wyślij potrzebne zmiany przed migracją lub zachowaj je w kopii do ręcznego importu. Nie uruchamiaj starej synchronizacji, jeśli zdalna gałąź zawiera już nowy układ.

## Nowy katalog i kopia poprzedniej instalacji

Poniższe polecenia wymagają, aby `~/.agents-next` jeszcze nie istniał:

```bash
git clone --recurse-submodules git@github.com:KonradDebski/agent-skills.git ~/.agents-next
backup_dir=$(mktemp -d "$HOME/agents-backup.XXXXXX")
mv "$HOME/.agents" "$backup_dir/agents"
mv "$HOME/.agents-next" "$HOME/.agents"
printf 'Poprzednia instalacja: %s/agents\n' "$backup_dir"
```

Kopia pozostaje poza nowym repozytorium i nie trafi do synchronizacji. Nie przenoś samego `.git` ze starego katalogu `skills` do katalogu nadrzędnego. Jeśli stara instalacja jest worktree, zachowaj ją i jej główne repozytorium do czasu osobnego uporządkowania worktree przez Git.

Porównaj poprzedni globalny `AGENTS.md` z nowym i scal potrzebne instrukcje. Nie zastępuj go repozytoryjnym plikiem ze starego `skills/AGENTS.md`, który dotyczył utrzymania repozytorium.

Przenieś własne skille ze starego `skills/<nazwa>/` do nowego `skills/<nazwa>/`, porównując istniejące wersje. Kopiuj katalogi konkretnych skilli. Nie kopiuj całego starego repozytorium, jego `.git`, `.upstream`, skryptów i README do nowego `skills/`.

Jeśli pozostałe pliki starego `~/.agents` są cache, logami albo historią, pozostaw je poza Gitem. W razie potrzeby odtwórz je jako ignorowane pliki lokalne.

## Instrukcje i MCP harnessów

Sprawdź istniejące globalne instrukcje i lokalne MCP. Scalone instrukcje zapisz w nowym `~/.agents/AGENTS.md`. Jeśli harness ma odmienny zwykły plik instrukcji, zachowaj go w kopii poza repozytorium i usuń dopiero po scaleniu. Instalator odmawia jego nadpisania. Dawne symlinki do starej instalacji też wymagają sprawdzenia i usunięcia przed utworzeniem nowych.

Do `mcp/servers.json` przenieś tylko wspólne definicje. Tokeny zamień na odwołania do zmiennych środowiskowych. Nie importuj całych `~/.claude.json`, `~/.codex` lub `~/.cursor`, ponieważ mogą zawierać dane logowania i historię. Rejestr początkowo zawiera Context7 i dokumentację OpenAI; inne istniejące MCP pozostają lokalne, dopóki ich nie przeniesiesz.

Jeśli nazwa wspólnego MCP już istnieje w konfiguracji harnessu, zachowaj kopię jego konfiguracji i usuń lub przemianuj stary wpis po porównaniu. Adapter nie przejmuje istniejącego wpisu automatycznie, nawet jeśli wygląda identycznie.

W razie potrzeby utwórz lokalny `~/.config/agents/local.json` z listą harnessów i wyjątków. Dla Cursor dodaj regułę wskazaną w README.

## Sprawdzenie i włączenie synchronizacji

```bash
bash ~/.agents/scripts/install.sh --no-sync --dry-run
bash ~/.agents/scripts/install.sh --no-sync
bash ~/.agents/scripts/doctor.sh
```

Sprawdź instrukcje i listę MCP w nowej sesji każdego używanego harnessu. Diagnostyka nie zastępuje tego sprawdzenia. Następnie na `main`, śledzącej `origin/main`:

```bash
bash ~/.agents/scripts/install.sh
systemctl --user status agents-sync.timer
```

Instalator wyłącza i usuwa stare jednostki `agent-skills-sync`, a następnie włącza nowe `agents-sync`. Powtórz migrację na pozostałych komputerach przed wznowieniem pracy nad wspólną konfiguracją.

## Powrót do poprzedniej instalacji

Wyłącz `agents-sync.timer` i zatrzymaj `agents-sync.service`. Usuń tylko dowiązania i wpisy dodane przez nowy instalator lub przywróć konfigurację z kopii w `~/.local/state/agents/backups`. Każda kopia jest JSON-em zawierającym ścieżkę, rodzaj pliku, uprawnienia i zawartość zakodowaną szesnastkowo albo cel symlinku. Przy własnym `XDG_STATE_HOME` użyj tej lokalizacji.

Zachowaj nowy katalog poza `~/.agents` i przywróć poprzedni z kopii. Nie włączaj starej synchronizacji przeciwko zdalnej gałęzi zawierającej nowy układ. Najpierw uzgodnij wersję repozytorium na wszystkich komputerach. Kopię starej instalacji usuń dopiero po sprawdzeniu nowego środowiska.
