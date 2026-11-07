# VS Code

VS Code w harnessie Local odczytuje osobiste skille z `~/.agents/skills`, więc adapter ich nie kopiuje. Adapter scala MCP w `${XDG_CONFIG_HOME:-~/.config}/Code/User/mcp.json`, czyli w profilu użytkownika. Wspólne serwery trafiają do sekcji `servers` i używają odwołań `${env:NAZWA}`. Zachowujemy komentarze, końcowe przecinki, `inputs`, osobiste serwery i pozostałe ustawienia. Adapter nie zapisuje do `.vscode/mcp.json` w projekcie ani do przenośnego `.mcp.json`. Pluginy w `~/.vscode/agent-plugins` są poza zakresem, ponieważ działają wyłącznie w VS Code. Nie czytamy ich i nie zmieniamy.

Instrukcje harnessu Local nie mają udokumentowanego pliku globalnego, dlatego dodaj je ręcznie w **Chat: Open Customizations > Instructions** dla harnessu Local jako instrukcję użytkownika:

```text
Read and follow ~/.agents/AGENTS.md before every task.
```

Adapter obsługuje domyślny profil użytkownika na Linuxie. Nie zmienia VS Code Insiders ani innych profili. Zmienne `${env:NAZWA}` odczytuje proces VS Code. Aplikacja uruchomiona z menu może ich nie widzieć, jeśli są ustawione tylko w terminalu.
