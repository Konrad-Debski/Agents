# Agents

Wspólna baza wiedzy, skilli i konfiguracji MCP dla agentów AI. Repozytorium instalujemy w `~/.agents` i synchronizujemy między komputerami przez Git.

`AGENTS.md` jest krótką mapą wiedzy. Szczegółowe zasady są w `docs/` oraz `skills/` i agent wczytuje je dla konkretnego zadania.

## Dokumentacja

- [Instalacja i diagnostyka](docs/operations/installation.md): nowy komputer, wdrażanie konfiguracji, rozwiązywanie kolizji.
- [Integracje](docs/integrations/README.md): Codex, Claude Code, OpenCode, Cursor, VS Code i T3.
- [Konfiguracja i MCP](docs/operations/configuration.md): ustawienia lokalne, sekrety, rejestr serwerów.
- [Synchronizacja](docs/operations/synchronization.md): timer, Git i submoduły.
- [Utrzymanie i testy](docs/contributing/maintenance.md): zmiany w tym repozytorium.
- [Zarządzanie kontekstem](docs/contributing/context-management.md): gdzie zapisywać wiedzę i kiedy ją wczytywać.
- [Indeks skilli](docs/skills/README.md): dobór procedury, gdy harness nie pokazuje katalogu.
- [Źródła i decyzje](docs/contributing/context-design.md): podsumowanie filmu Kyle'a i uzasadnienie podziału wiedzy.

## Struktura

- `AGENTS.md` wskazuje źródła wiedzy dla wszystkich projektów.
- `docs/` zawiera dokumentację tematyczną.
- `skills/` zawiera procedury oraz ich opcjonalne referencje.
- `mcp/servers.json` zawiera wspólne definicje serwerów bez sekretów.
- `adapters/` opisuje integracje z harnessami.
- `scripts/` zawiera instalację, wdrażanie, synchronizację i diagnostykę.
- `tests/` sprawdza adaptery i synchronizację w izolowanych katalogach.
- `.upstream/` przechowuje przypięte źródła zewnętrzne.
