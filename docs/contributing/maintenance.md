# Utrzymanie repozytorium

Repozytorium jest instalowane jako `~/.agents`. Globalny `AGENTS.md` jest mapą wiedzy dla wszystkich projektów. Ten dokument wczytuj przy zmianach w samej bazie `~/.agents`.

- Na `main` usługa `agents-sync` automatycznie zapisuje i wysyła zmiany co 15 minut. Pracuj na osobnej gałęzi, aby usługa nie zapisała niedokończonej edycji. Inne gałęzie pomija.
- Nie uruchamiaj instalatora z worktree na rzeczywistym HOME w ramach testów. Testy mają izolowane środowisko.
- Instalator i synchronizacja aktualizują wszystkie submoduły do najnowszych commitów gałęzi upstream. Nie edytuj ich plików. Udostępniaj tylko wybrane skille według [upstream.md](../skills/upstream.md).
- Nowy katalog najwyższego poziomu wymaga zmiany `.gitignore` oraz listy zakresu w `scripts/agents.py`.
- Dodanie harnessu wymaga manifestu w `adapters/`, obsługi jego formatu w `scripts/agents.py`, testów oraz opisania ograniczeń. Sam manifest nie wystarczy do obsługi dowolnego nowego formatu.
- Zmiany skilli muszą uwzględniać przenośność ścieżek i zależności od narzędzi konkretnego harnessu. Nie zmieniaj po cichu procedur publikowania zawartych w skillach.

Przed przekazaniem zmian uruchom `python3 -m unittest discover -s tests -v` oraz sprawdź składnię zmienionych skryptów przez `bash -n`.

Instalacja na docelowym komputerze odbywa się przez `bash ~/.agents/scripts/install.sh`, bez `sudo`. Bieżące wymagania opisuje [installation.md](../operations/installation.md).

## Organizacja wiedzy

Zasady podziału instrukcji, dokumentacji i skilli opisuje [context-management.md](context-management.md). Przeczytaj je przed zmianą `AGENTS.md`, dodaniem skilla lub reorganizacją wiedzy.

## Testy

```bash
python3 -m unittest discover -s tests -v
```

Testy używają tymczasowych katalogów domowych, lokalnych zdalnych repozytoriów Git i atrapy systemd. Nie zmieniają działającej konfiguracji użytkownika.

Jeśli OpenCode 2 jest dostępny w `PATH`, dodatkowe testy uruchamiają `opencode debug config --standalone` z izolowanymi katalogami HOME i XDG. Sprawdzają konfigurację JSON, JSONC oraz zgodność formatu OpenCode 1. Serwery MCP w tych kopiach konfiguracji są wyłączone; testy nie uruchamiają modelu. Bez lokalnej instalacji OpenCode 2 te testy są pomijane, a testy adaptera nadal działają.
