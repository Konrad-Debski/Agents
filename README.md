# Agents

Wspólne instrukcje, skille i konfiguracja MCP dla agentów AI. Repozytorium instalujemy w `~/.agents` i synchronizujemy między komputerami przez Git.

## Instalacja

Wymagania: Linux z systemd użytkownika, Git, Bash, Python 3.11 lub nowszy oraz `flock` z util-linux. Git musi mieć ustawione `user.name` i `user.email`. Pobieranie i wysyłanie do `origin/main`, a także podpisywanie commitów, muszą działać bez interaktywnego logowania.

Jeśli masz już `~/.agents`, najpierw wykonaj [migrację](docs/migration.md). Nie klonuj repozytorium wewnątrz istniejącego `~/.agents/skills`.

Na nowym komputerze, jako docelowy użytkownik, bez `sudo`:

```bash
git clone --recurse-submodules git@github.com:KonradDebski/agent-skills.git ~/.agents
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

## Struktura

- `AGENTS.md` zawiera Twoje globalne instrukcje. Dalsze zmiany tego pliku synchronizują się przez Git.
- `skills/` zawiera skille oraz symlink katalogu `unslop` do przypiętego submodułu.
- `mcp/servers.json` zawiera wspólne definicje serwerów bez sekretów.
- `adapters/` opisuje integracje z harnessami.
- `scripts/` zawiera instalację, wdrażanie, synchronizację i diagnostykę.
- `.upstream/` przechowuje zewnętrzne repozytoria.
- [Zasady utrzymania](docs/maintenance.md) opisują pracę nad tym repozytorium.

## Obsługiwane harnessy

Codex otrzymuje symlink globalnych instrukcji do `~/.codex/AGENTS.md`. Skille odczytuje z `~/.agents/skills`. Adapter aktualizuje oznaczony blok MCP w `~/.codex/config.toml`, zachowując pozostałe ustawienia i komentarze.

Claude Code otrzymuje symlink do `~/.claude/CLAUDE.md` i pojedyncze dowiązania skilli w `~/.claude/skills`. Adapter scala globalne `mcpServers` w `~/.claude.json`, zachowując pozostałe dane. Uwzględniamy także `CODEX_HOME` i `CLAUDE_CONFIG_DIR`, jeśli są ustawione. Przy niestandardowych katalogach wybierz harness jawnie w `local.json` i zapewnij te same zmienne procesowi synchronizacji.

Cursor odczytuje skille z `~/.agents/skills`, a adapter scala MCP w `~/.cursor/mcp.json`. Globalne User Rules ustawia się przez interfejs Cursor. Jednorazowo dodaj w **Customize > Rules**:

```text
Read and follow ~/.agents/AGENTS.md before every task.
```

To instrukcja dla modelu, nie natywny import pliku. `doctor.sh` przypomina o niej, ale nie sprawdza ustawień interfejsu. Nie zapisujemy globalnych reguł Cursor do nieudokumentowanego pliku.

T3 korzysta z uruchamianych harnessów. Repozytorium nie modyfikuje wewnętrznej bazy T3 ani jego konektorów. Dostępność MCP w T3 trzeba sprawdzić w nowej sesji danego dostawcy. Analogicznie inne harnessy wymagają własnego adaptera. Zmiany konfiguracji mogą wymagać ponownego uruchomienia agenta. Wspólne pliki nie gwarantują identycznego zachowania modeli ani identycznej obsługi metadanych skilli.

Źródła integracji: [Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md), [Codex MCP](https://developers.openai.com/codex/mcp), [Claude Code MCP](https://code.claude.com/docs/en/mcp), [Claude Code skills](https://code.claude.com/docs/en/skills), [Cursor rules](https://cursor.com/docs/rules), [Cursor skills](https://cursor.com/docs/skills), [Cursor MCP](https://cursor.com/docs/mcp).

## Ustawienia lokalne i sekrety

Opcjonalny plik `${XDG_CONFIG_HOME:-~/.config}/agents/local.json` pozostaje poza repozytorium:

```json
{
  "harnesses": ["codex", "claude-code", "cursor"],
  "disabled_servers": []
}
```

Brak `harnesses` oznacza automatyczne wykrywanie. Pusta lista wyłącza integracje. Usunięcie harnessu z jawnej listy usuwa wyłącznie jego wcześniej zarządzane wpisy i dowiązania. `disabled_servers` pozwala wyłączyć serwer na konkretnej maszynie bez zmiany wspólnej definicji.

Stan własności wpisów, blokada wdrażania i lokalne kopie zapasowe znajdują się w `${XDG_STATE_HOME:-~/.local/state}/agents`. Nie usuwaj `managed.json`, jeśli chcesz nadal automatycznie aktualizować istniejące wpisy. Utrata stanu powoduje wykrycie kolizji zamiast przejęcia obcej konfiguracji. Kopie zapasowe mają uprawnienia `600` i przechowują także zawartość zastępowanych plików lokalnych. Chroń je tak samo jak konfigurację harnessów.

Klucze API dostarczaj w środowisku uruchamianego harnessu. Zmienne ustawione tylko w terminalu mogą nie być dostępne w aplikacji graficznej lub usłudze systemd. Tokeny OAuth zapisuje lokalnie odpowiedni harness. Logowanie wykonujemy oddzielnie na każdym komputerze. Repozytorium nie przenosi sesji logowania, historii rozmów ani danych konektorów.

## Definicje MCP

Początkowy rejestr obejmuje Context7 przez `npx` oraz publiczny serwer dokumentacji OpenAI. Context7 wymaga lokalnego `npx` i dostępu do sieci. Pozostałe MCP dodawaj do `mcp/servers.json`, po przeniesieniu sekretów do środowiska.

Przykład formatu:

```json
{
  "version": 1,
  "servers": {
    "local-tool": {
      "transport": "stdio",
      "command": "my-mcp-server",
      "args": ["serve"],
      "env_vars": ["MY_TOOL_API_KEY"],
      "requires_env": ["MY_TOOL_API_KEY"]
    },
    "remote-tool": {
      "transport": "http",
      "url": "https://example.com/mcp",
      "header_env": {"X-API-Key": "MY_TOOL_API_KEY"},
      "harnesses": ["codex", "claude-code"]
    }
  }
}
```

Obsługujemy `stdio` i Streamable HTTP. `env_vars` przekazuje zmienne do procesu, `header_env` wskazuje zmienne z wartościami nagłówków, a `requires_env` dodaje wymagania do diagnostyki. Wygenerowana konfiguracja zawiera odwołania do zmiennych, nigdy odczytane wartości. `harnesses` opcjonalnie ogranicza integrację do wskazanych narzędzi.

Nie umieszczaj sekretów w argumentach, URL ani plikach źródłowych. Wspólny rejestr nie przyjmuje dowolnych pól `env` lub `headers` ze stałymi wartościami. Polecenia powinny być dostępne w `PATH`, bez ścieżek `/home/...`. Zależności MCP instalujesz lokalnie. Jeśli potrzebujesz powtarzalnej wersji paczki, przypnij jej wersję w argumentach polecenia.

## Wdrażanie i diagnostyka

```bash
bash "$HOME/.agents/scripts/apply.sh" --dry-run
bash "$HOME/.agents/scripts/apply.sh"
bash "$HOME/.agents/scripts/doctor.sh"
```

`--dry-run` nie zapisuje konfiguracji ani stanu. Wdrażanie najpierw sprawdza wszystkie kolizje, następnie zapisuje pliki atomowo i tworzy kopie poprzednich wersji. Obsłużony błąd zapisu powoduje wycofanie wcześniejszych zmian z tego przebiegu. Ręcznie zmienione zarządzane wpisy zatrzymują wdrażanie. Edytuj definicję źródłową zamiast wygenerowanego wpisu.

Nie uruchamiaj wdrażania równocześnie ze zmianą konfiguracji w interfejsie harnessu. Blokada chroni przed drugim procesem `apply`, ale zewnętrzne aplikacje jej nie znają. Nagłe wyłączenie komputera podczas zapisu wielu plików może wymagać odtworzenia ich z kopii zapasowych.

`doctor` sprawdza plan wdrażania, brakujące programy i zmienne środowiskowe, zerwane symlinki oraz stan timera. Nie łączy się z MCP, nie weryfikuje logowania OAuth i nie testuje zachowania modeli.

## Synchronizacja

Pierwszy przebieg następuje około minuty po instalacji, kolejne co 15 minut od zakończenia poprzedniego. Synchronizacja działa wyłącznie na `main`, automatycznie zapisuje także nowe i usunięte pliki źródłowe. Może zapisać trwającą edycję. Do pracy nad zmianami używaj osobnej gałęzi.

`.gitignore` dopuszcza tylko wspólne katalogi. Dodatkowa kontrola obejmuje również pliki już śledzone i lokalne niewysłane commity. Blokuje ścieżki poza zakresem, typowe pliki poświadczeń i rozpoznawane formaty tokenów. Nie zastępuje przeglądu zmian i nie wykrywa wszystkich możliwych sekretów.

Przed synchronizacją sprawdzamy rejestr MCP. Po udanej synchronizacji i aktualizacji submodułów ponownie sprawdzamy źródła oraz wykonujemy `apply`. Konflikt Gita zatrzymuje proces i wymaga ręcznego rozwiązania. Błąd wdrażania nie cofa synchronizacji Git; po usunięciu przyczyny ponów `apply`.

```bash
systemctl --user status agents-sync.timer
journalctl --user -u agents-sync.service -n 50 --no-pager
systemctl --user start agents-sync.service
```

Wyłączenie:

```bash
systemctl --user disable --now agents-sync.timer
systemctl --user stop agents-sync.service
```

Instalator próbuje włączyć działanie systemd po wylogowaniu przez `loginctl enable-linger`. Jeśli system odmówi, wyświetla polecenie dla administratora. Importuje `PATH` i bieżące `SSH_AUTH_SOCK`. Po zmianie agenta SSH uruchom instalator ponownie. Po restarcie uwierzytelnianie musi być dostępne dla usługi bez pytania o hasło.

## Submoduły

`.upstream/git-sync` automatycznie aktualizuje się do najnowszego `master`, zgodnie z dotychczasową polityką. Nie wprowadzaj w nim własnych zmian. `.upstream/cursor-plugins` pozostaje na wersji zapisanej w repozytorium. `skills/unslop` jest symlinkiem do katalogu skilla w submodule. Dowiązujemy cały katalog, ponieważ Codex pomija symlinki samego pliku `SKILL.md` podczas wykrywania skilli.

Pobranie zapisanych wersji:

```bash
git -C ~/.agents pull --ff-only
git -C ~/.agents submodule update --init --recursive
bash ~/.agents/scripts/apply.sh
```

Świadoma aktualizacja `unslop`:

```bash
git -C ~/.agents submodule update --init --remote --checkout -- .upstream/cursor-plugins
```

Zmianę wskazania submodułu zapisz w commicie, aby udostępnić ją innym komputerom. Niezapisane zmiany wewnątrz submodułów zatrzymują synchronizację.

## Testy

```bash
python3 -m unittest discover -s tests -v
```

Testy używają tymczasowych katalogów domowych, lokalnych zdalnych repozytoriów Git i atrapy systemd. Nie zmieniają działającej konfiguracji użytkownika.
