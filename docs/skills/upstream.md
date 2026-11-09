# Źródła zewnętrzne i wybór skilli

Wczytuj przy dodawaniu lub aktualizowaniu zewnętrznych skilli. Źródła są submodułami, a `skills/` zawiera symlinki do wybranych całych katalogów. Zachowuje to referencje, skrypty, metadane i licencje oryginałów.

## Aktywny zestaw

| Źródło | Symlinki w `skills/` | Zastosowanie |
| --- | --- | --- |
| [cursor/plugins](https://github.com/cursor/plugins) | `unslop` | Redakcja tekstów |
| [DietrichGebert/ponytail](https://github.com/dietrichgebert/ponytail) | `ponytail`, `ponytail-review` | Mały zakres implementacji i przegląd zmian w motywie |
| [mattpocock/skills](https://github.com/mattpocock/skills) | `grill-me`, `grilling`, `writing-for-agents`, `diagnosing-bugs`, `pr` | Wymagania dla sekcji, instrukcje dla agentów, diagnoza błędów i opisy PR |

`grilling` jest zależnością aktualnego `grill-me`. Pozostawienie samego aliasu uniemożliwiłoby wykonanie jego procedury. `diagnosing-bugs` ma własny szablon skryptu, a `writing-for-agents` plik `SKILL-MECHANICS.md`; symlink całego katalogu udostępnia także te zasoby.

Skille są ogólne i stosują się do PHP, Twig, ACF, CSS oraz TypeScript w motywach. Nie wnoszą gotowych konwencji konkretnego motywu, więc agent nadal korzysta z instrukcji projektu.

Pozostałe skille są dostępne w źródłach, ale nie mają globalnych symlinków. Pomijamy pakietowy instalator, hooki i globalne reguły Ponytail, żeby dodanie źródła nie wymuszało jego odczytu przy każdym zadaniu. `ponytail` ma szeroki opis wywołania i po uruchomieniu działa przez sesję; zachowujemy zachowanie autora. Nie dopisujemy go do głównego `AGENTS.md`.

`pr` z `engineering/pr` określa treść opisu PR. Własny `create-pr` prowadzi publikację i merge przez wspólny protokół, który odczytuje `pr` przy przygotowaniu opisu.

Z repo Matta nie udostępniamy globalnie procedur trackerów, generatorów środowiska, materiałów szkoleniowych ani skilli eksperymentalnych. TDD i projektowanie architektury pozostają w upstream do użycia w projekcie, który ich potrzebuje. Dodanie kolejnego skilla wymaga sprawdzenia jego zależności i uzasadnienia odrębnego zastosowania.

## Aktualizacja

Gitlink w repo nadrzędnym określa dokładną wersję każdego źródła. Instalator i synchronizacja automatycznie aktualizują wszystkie źródła do najnowszych commitów gałęzi upstream. Synchronizacja zapisuje i wysyła nowe gitlinki. Gałąź pochodzi z `.gitmodules`, a bez wpisu `branch` Git używa domyślnej gałęzi zdalnego repozytorium.

Przy zadaniu aktualizacji wybranego źródła:

```bash
git -C ~/.agents submodule update --init --remote --checkout -- .upstream/ponytail
git -C ~/.agents submodule update --init --remote --checkout -- .upstream/mattpocock-skills
```

Uruchom tylko polecenie dotyczące aktualizowanego źródła. Sprawdź diff, metadane i ścieżki wybranych skilli. Jeśli upstream je zmienił, popraw symlinki oraz listę `skills` w `package.json`. Nie edytuj plików wewnątrz submodułu. Zapisz nowy gitlink albo pozostaw to synchronizacji. Po zmianach uruchom `apply`, aby odświeżyć dowiązania Claude Code. Szczegóły tego procesu opisuje [synchronization.md](../operations/synchronization.md).

Nie uruchamiaj skryptu Matta `scripts/link-skills.sh`, bo udostępnia szerszy zestaw niż wybrany tutaj. Samo pobranie repozytorium do `.upstream/` nie instaluje całego pakietu w katalogu skilli.

## Podział dokumentacji

Z repo Matta przejmujemy podział dokumentacji według rodzaju pracy oraz wskazanie, kiedy użyć danego materiału. W tej bazie kategorie to `operations/`, `integrations/`, `contributing/` i `skills/`. Dobieramy je do utrzymania wspólnej konfiguracji, zamiast kopiować kategorie jego pakietu.

Plik o skillu wyjaśnia jego dobór. Procedura pozostaje w `SKILL.md`. W ten sposób dokumentacja nie staje się drugą kopią instrukcji.
