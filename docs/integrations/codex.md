# Codex

Codex otrzymuje symlink globalnych instrukcji do `~/.codex/AGENTS.md`. Skille odczytuje z `~/.agents/skills`. Adapter aktualizuje oznaczony blok MCP w `~/.codex/config.toml`, zachowując pozostałe ustawienia i komentarze.

Przy ustawionym `CODEX_HOME` adapter używa tego katalogu zamiast `~/.codex`. Przy niestandardowej lokalizacji wybierz harness jawnie w `local.json` i zapewnij tę samą zmienną procesowi synchronizacji.
