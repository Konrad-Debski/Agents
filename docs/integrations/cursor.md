# Cursor

Cursor odczytuje skille z `~/.agents/skills`, a adapter scala MCP w `~/.cursor/mcp.json`. Globalne User Rules ustawia się przez interfejs Cursor. Jednorazowo dodaj w **Customize > Rules**:

```text
Read and follow ~/.agents/AGENTS.md before every task.
```

To instrukcja dla modelu, nie natywny import pliku. `doctor.sh` przypomina o niej, ale nie sprawdza ustawień interfejsu. Nie zapisujemy globalnych reguł Cursor do nieudokumentowanego pliku.
