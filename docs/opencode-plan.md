# Plan wdrożenia adaptera OpenCode

## Zakres

1. Dodać manifest `adapters/opencode/adapter.json` oraz wykrywanie programu `opencode` i katalogu `${XDG_CONFIG_HOME:-~/.config}/opencode`.
2. Udostępnić globalne instrukcje przez dowiązanie `AGENTS.md` w globalnym katalogu konfiguracji. Zachować natywne wykrywanie `~/.agents/skills`, w tym dowiązania katalogu `unslop`.
3. Przetłumaczyć wspólny rejestr MCP na sekcję `mcp.servers` OpenCode 2. Istniejące, niepuste płaskie mapy `mcp` zachowują format OpenCode 1. Dla stdio generować `type: local`, tablicę `command` i `environment`. Dla HTTP generować `type: remote`, `url` oraz `headers`. Sekrety pozostawić jako `{env:NAZWA}`. Nie wymuszać pól `enabled` lub `disabled`, które różnią się między wydaniami OpenCode.
4. Edytować istniejący `opencode.jsonc`, a przy jego braku `opencode.json`. Jeśli żaden nie istnieje, utworzyć `opencode.json`. Zachować komentarze, ustawienia użytkownika i obce MCP. Sprawdzać kolizje także w drugim pliku, ponieważ OpenCode wczytuje oba.
5. Wykorzystać istniejący stan własności, kopie zapasowe, blokadę i wycofanie zapisów po błędzie. Ręczna zmiana zarządzanego wpisu ma zatrzymywać wdrażanie. Usunięcie serwera lub wyłączenie adaptera ma usuwać tylko zarządzane wpisy i dowiązania.
6. Uwzględnić `opencode` w filtrach rejestru i lokalnym wyborze harnessów. Informować o dodatkowych warstwach `OPENCODE_CONFIG`, `OPENCODE_CONFIG_DIR` i `OPENCODE_CONFIG_CONTENT`, które mogą nadpisać konfigurację globalną. Adapter zarządza wyłącznie globalnym katalogiem XDG, nie konfiguracją projektów ani usługą w tle.
7. Dodać testy izolowanej instalacji, ponownego uruchomienia, JSONC, kolizji, zmiany pliku konfiguracji, usuwania wpisów, sekretów i katalogu XDG. Uruchomić pełne testy repozytorium i sprawdzić wynik w zainstalowanym OpenCode przez prywatny proces, bez uruchamiania modelu lub połączeń MCP.
8. Uzupełnić README i instrukcję migracji. Zachować wcześniejsze zmiany adresu repozytorium.

## Kryteria odbioru

- Instalator i `doctor` rozpoznają OpenCode bez ręcznego wskazywania domyślnego katalogu.
- Zwykłe ustawienia i komentarze pozostają bez zmian, także po usunięciu adaptera.
- Pliki konfiguracji oraz stan nie zawierają odczytanych wartości zmiennych środowiskowych.
- Powtórne wdrożenie nie zmienia plików i nie tworzy dodatkowych kopii.
- Nie zmieniamy działającej konfiguracji użytkownika podczas testów.

## Źródła

- [Konfiguracja i jej kolejność](https://opencode.ai/docs/config/)
- [Globalne instrukcje](https://opencode.ai/docs/rules/)
- [Wykrywanie skilli](https://opencode.ai/docs/skills/)
- [MCP](https://opencode.ai/docs/mcp-servers/)
- [Bieżący schemat MCP](https://github.com/anomalyco/opencode/blob/dev/packages/schema/src/mcp.ts)
- [Kontener MCP wersji 2](https://github.com/anomalyco/opencode/blob/dev/packages/schema/src/config/mcp.ts)

Dokumentację sprawdzono przez Context7 i źródła projektu. Zainstalowana wersja przeznaczona do weryfikacji integracji to OpenCode 2.2.5.
