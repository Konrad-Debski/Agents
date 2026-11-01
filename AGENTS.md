# Instrukcje dla agentów

- Na `main` usługa co 15 minut automatycznie tworzy commity, pobiera i wysyła zmiany. Może zapisać także trwającą edycję. Inne gałęzie pomija.
- `.upstream/git-sync` automatycznie aktualizuje się do najnowszego `master`. Nie wprowadzaj w nim własnych zmian.
- `.upstream/cursor-plugins`, zawierający `unslop`, pozostaje na wersji zapisanej w repozytorium. Aktualizuj go przez `--remote` wyłącznie w ramach zadania aktualizacji tego skilla.

Po sklonowaniu do `~/.agents/skills` uruchom jako docelowy użytkownik, bez `sudo`:

```bash
bash "$HOME/.agents/skills/scripts/install-sync.sh"
```

Komenda inicjalizuje submoduły i włącza usługę oraz timer systemd użytkownika. Wymagania, instalację w istniejącym katalogu i obsługę błędów opisuje [README.md](README.md).
