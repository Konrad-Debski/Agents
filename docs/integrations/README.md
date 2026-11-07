# Integracje z harnessami

Codex otrzymuje symlink globalnych instrukcji do `~/.codex/AGENTS.md`. Skille odczytuje z `~/.agents/skills`. Adapter aktualizuje oznaczony blok MCP w `~/.codex/config.toml`, zachowując pozostałe ustawienia i komentarze.

Claude Code otrzymuje symlink do `~/.claude/CLAUDE.md` i pojedyncze dowiązania skilli w `~/.claude/skills`. Adapter scala globalne `mcpServers` w `~/.claude.json`, zachowując pozostałe dane. Uwzględniamy także `CODEX_HOME` i `CLAUDE_CONFIG_DIR`, jeśli są ustawione. Przy niestandardowych katalogach wybierz harness jawnie w `local.json` i zapewnij te same zmienne procesowi synchronizacji.

OpenCode otrzymuje symlink globalnego `AGENTS.md` w `${XDG_CONFIG_HOME:-~/.config}/opencode`. Skille odczytuje bezpośrednio z `~/.agents/skills`, bez dodatkowych kopii. Wykrywamy go po programie `opencode` w `PATH` lub istniejącym katalogu konfiguracji XDG.

Adapter OpenCode aktualizuje `opencode.jsonc`, jeśli istnieje, a w pozostałych przypadkach `opencode.json`. Nowy plik używa sekcji `mcp.servers` OpenCode 2. Istniejące niepuste płaskie mapy `mcp` zachowują format zgodności OpenCode 1. Zmiany obejmują wyłącznie zarządzane wpisy, z zachowaniem komentarzy JSONC, końcowych przecinków, lokalnych MCP oraz innych ustawień, w tym timeoutów. Gdy istnieją oba pliki, adapter sprawdza kolizje także w drugim, ponieważ OpenCode wczytuje obie konfiguracje.

Serwery stdio otrzymują `type: local`, tablicę `command` i opcjonalne `environment`. Serwery HTTP otrzymują `type: remote`, `url` i opcjonalne `headers`. Zmienne mają składnię `{env:NAZWA}`. Adapter nie przenosi poświadczeń OAuth ani wartości sekretów. Nie dopisuje pól `enabled` lub `disabled`, których format różni się między wydaniami. Osobne warstwy `OPENCODE_CONFIG`, `OPENCODE_CONFIG_DIR` i `OPENCODE_CONFIG_CONTENT`, a także konfiguracja projektu, mogą nadpisać ustawienia globalne. Adapter nie modyfikuje tych warstw; `apply` i `doctor` informują o ustawionych zmiennych dodatkowej konfiguracji. Zmienne środowiskowe używane do wyboru konfiguracji muszą być takie same w terminalu, T3 i usłudze synchronizacji.

Cursor odczytuje skille z `~/.agents/skills`, a adapter scala MCP w `~/.cursor/mcp.json`. Globalne User Rules ustawia się przez interfejs Cursor. Jednorazowo dodaj w **Customize > Rules**:

```text
Read and follow ~/.agents/AGENTS.md before every task.
```

To instrukcja dla modelu, nie natywny import pliku. `doctor.sh` przypomina o niej, ale nie sprawdza ustawień interfejsu. Nie zapisujemy globalnych reguł Cursor do nieudokumentowanego pliku.

VS Code w harnessie Local odczytuje osobiste skille z `~/.agents/skills`, więc adapter ich nie kopiuje. Adapter scala MCP w `${XDG_CONFIG_HOME:-~/.config}/Code/User/mcp.json`, czyli w profilu użytkownika. Wspólne serwery trafiają do sekcji `servers` i używają odwołań `${env:NAZWA}`. Zachowujemy komentarze, końcowe przecinki, `inputs`, osobiste serwery i pozostałe ustawienia. Adapter nie zapisuje do `.vscode/mcp.json` w projekcie ani do przenośnego `.mcp.json`. Pluginy w `~/.vscode/agent-plugins` są poza zakresem, ponieważ działają wyłącznie w VS Code. Nie czytamy ich i nie zmieniamy.

Instrukcje harnessu Local nie mają udokumentowanego pliku globalnego, dlatego dodaj je ręcznie w **Chat: Open Customizations > Instructions** dla harnessu Local jako instrukcję użytkownika:

```text
Read and follow ~/.agents/AGENTS.md before every task.
```

Adapter obsługuje domyślny profil użytkownika na Linuxie. Nie zmienia VS Code Insiders ani innych profili. Zmienne `${env:NAZWA}` odczytuje proces VS Code. Aplikacja uruchomiona z menu może ich nie widzieć, jeśli są ustawione tylko w terminalu.

T3 korzysta z uruchamianych harnessów. Repozytorium nie modyfikuje wewnętrznej bazy T3 ani jego konektorów. Dostępność MCP w T3 trzeba sprawdzić w nowej sesji danego dostawcy. Analogicznie inne harnessy wymagają własnego adaptera. Zmiany konfiguracji mogą wymagać ponownego uruchomienia agenta. Wspólne pliki nie gwarantują identycznego zachowania modeli ani identycznej obsługi metadanych skilli.

Źródła integracji: [Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md), [Codex MCP](https://developers.openai.com/codex/mcp), [Claude Code MCP](https://code.claude.com/docs/en/mcp), [Claude Code skills](https://code.claude.com/docs/en/skills), [Cursor rules](https://cursor.com/docs/rules), [Cursor skills](https://cursor.com/docs/skills), [Cursor MCP](https://cursor.com/docs/mcp), [VS Code MCP](https://code.visualstudio.com/docs/agents/reference/mcp-configuration), [VS Code skills](https://code.visualstudio.com/docs/agent-customization/agent-skills), [VS Code instructions](https://code.visualstudio.com/docs/agent-customization/custom-instructions), [OpenCode config](https://opencode.ai/docs/config/), [OpenCode rules](https://opencode.ai/docs/rules/), [OpenCode skills](https://opencode.ai/docs/skills/), [OpenCode MCP v2](https://github.com/anomalyco/opencode/blob/dev/packages/schema/src/config/mcp.ts).
