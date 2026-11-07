# Synchronizacja

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

`.upstream/git-sync` automatycznie aktualizuje się do najnowszego `master`, zgodnie z dotychczasową polityką. Nie wprowadzaj w nim własnych zmian. `.upstream/cursor-plugins`, `.upstream/ponytail` i `.upstream/mattpocock-skills` pozostają na wersjach zapisanych w repozytorium. Wybrane skille dowiązujemy całymi katalogami, zachowując ich referencje i metadane. Codex pomija symlinki samego pliku `SKILL.md` podczas wykrywania skilli. Dobór i aktualizację nowych źródeł opisuje [upstream.md](../skills/upstream.md).

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

## Dowiązania Claude Code

`apply` za każdym razem przegląda katalog `skills/`. Dla każdego katalogu z `SKILL.md`, także symlinku do submodułu, tworzy dowiązanie `~/.claude/skills/<nazwa>` do `~/.agents/skills/<nazwa>`. Przy ustawionym `CLAUDE_CONFIG_DIR` używa tego katalogu zamiast `~/.claude`.

Nowy skill wymaga jednego przebiegu `apply`. Edycja treści istniejącego skilla jest od razu widoczna przez to samo dowiązanie. Usunięcie skilla usuwa tylko dowiązanie wcześniej zarządzane przez adapter. Osobiste katalogi i obce symlinki pozostają chronione; kolizja nazwy zatrzymuje wdrażanie.

`sync.sh` wykonuje `apply.sh` po udanej synchronizacji Git i aktualizacji przypiętych submodułów. Timer obejmuje więc także nowe i usunięte skille. Na gałęzi roboczej synchronizacja jest pomijana; dodane właśnie skille udostępnij od razu przez:

```bash
bash ~/.agents/scripts/apply.sh --dry-run
bash ~/.agents/scripts/apply.sh
```

Claude Code musi być wykryty lub obecny w jawnej liście `harnesses`. Przy wyłączonym timerze uruchamiaj `apply` ręcznie po dodaniu lub usunięciu skilla. [Claude Code obsługuje automatyczne odświeżanie skilli](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md). Jeśli uruchomiona sesja nie pokazuje zmiany pochodzącej z symlinku lub aktualizacji submodułu, użyj dostępnego w swojej wersji `/reload-skills` albo rozpocznij nową sesję. Sam adapter sprawdza pliki, a nie pamięć działającego procesu Claude.
