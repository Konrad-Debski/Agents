# Utrzymanie repozytorium

Repozytorium jest instalowane jako `~/.agents`. Globalny `AGENTS.md` zawiera instrukcje użytkownika dla wszystkich projektów. Zasady dotyczące wyłącznie utrzymania tej bazy zapisujemy tutaj.

- Na `main` usługa `agents-sync` automatycznie zapisuje i wysyła zmiany co 15 minut. Pracuj na osobnej gałęzi, aby usługa nie zapisała niedokończonej edycji. Inne gałęzie pomija.
- Nie uruchamiaj instalatora z worktree na rzeczywistym HOME w ramach testów. Testy mają izolowane środowisko.
- `.upstream/git-sync` automatycznie aktualizuje się do źródłowego `master`. Nie wprowadzaj w nim własnych zmian.
- `.upstream/cursor-plugins` pozostaje na przypiętej wersji. Aktualizuj przez `--remote` wyłącznie w zadaniu aktualizacji skilla `unslop`.
- Nowy katalog najwyższego poziomu wymaga zmiany `.gitignore` oraz listy zakresu w `scripts/agents.py`.
- Dodanie harnessu wymaga manifestu w `adapters/`, obsługi jego formatu w `scripts/agents.py`, testów oraz opisania ograniczeń. Sam manifest nie wystarczy do obsługi dowolnego nowego formatu.
- Zmiany skilli muszą uwzględniać przenośność ścieżek i zależności od narzędzi konkretnego harnessu. Nie zmieniaj po cichu procedur publikowania zawartych w skillach.

Przed przekazaniem zmian uruchom `python3 -m unittest discover -s tests -v` oraz sprawdź składnię zmienionych skryptów przez `bash -n`.

Instalacja na docelowym komputerze odbywa się przez `bash ~/.agents/scripts/install.sh`, bez `sudo`. Procedura przejścia ze starego układu znajduje się w [migration.md](migration.md).
