# Zarządzanie kontekstem

Ten dokument dotyczy organizacji wiedzy w `~/.agents`. Wczytuj go przy zmianie globalnych instrukcji, skilli lub dokumentacji. Podsumowanie materiału źródłowego i przyjęte rozwiązania są w [context-design.md](context-design.md).

## Dobór źródeł

1. Z mapy `AGENTS.md` wybierz źródło potrzebne do bieżącego zadania. Przy pracy w innym projekcie uwzględnij też jego własne instrukcje.
2. W katalogu skilli harnessu sprawdź nazwę i opis. Wczytaj treść tylko pasującego `SKILL.md`. [Indeks skilli](../skills/README.md) jest zapasową mapą, gdy harness nie udostępnia katalogu.
3. Referencje skilla otwieraj dopiero dla fazy lub wariantu, który ich wymaga. Odnośnik do pliku nie jest poleceniem wczytania wszystkich jego sąsiadów.

## Gdzie zapisać wiedzę

| Zawartość | Miejsce |
| --- | --- |
| Temat i wskazanie, kiedy oraz gdzie go szukać | Główny `AGENTS.md` |
| Konwencje, konfiguracja, utrzymanie i objaśnienia | Tematyczny plik w `docs/` |
| Powtarzalna procedura dla konkretnego zadania | `skills/<nazwa>/SKILL.md` |
| Opcjonalny wariant, katalog danych lub obszerne przykłady procedury | `skills/<nazwa>/references/` z warunkiem odczytu w `SKILL.md` |
| Wiedza obowiązująca wyłącznie w jednym projekcie | Dokumentacja lub skille tego projektu |

Główny `AGENTS.md` pozostaje mapą. Nie dopisuj do niego kroków narzędzi, przykładów kodu, list kontrolnych ani reguł wymagających wczytania skilla przy każdym zadaniu. Nie zastępuj go odnośnikiem do jednego dokumentu, który agent ma zawsze przeczytać w całości.

## Utrzymanie dokumentacji i skilli

- Każda zasada ma jedno źródło. W pozostałych miejscach podaj link i warunek użycia.
- Opis skilla ma umożliwiać wybór zadania. Szczegóły procedury są w treści, a materiał potrzebny tylko w wybranych fazach w referencjach.
- Nie przenoś obowiązkowego warunku bezpieczeństwa do opcjonalnej referencji. Zachowaj zasady publikacji, wymagane testy i granice autoryzacji podczas podziału.
- Rozszerzaj instrukcje po rozpoznaniu konkretnego problemu. Sprawdź najpierw, czy właściwy plik lub skill już istnieje.
- Wiedzę wspólną zapisuj globalnie, a zależną od jednego projektu lokalnie. Nie instaluj globalnie kolejnych pakietów skilli bez potrzeby.
- Nie edytuj kopii skilli w `.upstream/`. Zasady aktualizacji źródeł zewnętrznych opisuje [synchronization.md](../operations/synchronization.md).

## Ścieżki i ładowanie

Globalny `AGENTS.md` jest udostępniany także przez symlinki poza repozytorium. Jego odnośniki używają `~/.agents/...`, aby agent mógł znaleźć źródła niezależnie od katalogu projektu i nazwy użytkownika. Narzędzie odczytu może wymagać rozwinięcia `~` do katalogu domowego. W `docs/` oraz wewnątrz skilla stosuj odnośniki względem danego pliku.

Nie dodawaj automatycznych importów całego `docs/` ani wszystkich `SKILL.md`. Treść otwartego pliku pozostaje w kontekście danej rozmowy; podział ogranicza przyszłe odczyty, nie usuwa już wczytanej wiedzy. Nazwy i opisy skilli nadal mogą trafiać do katalogu harnessu. Repozytorium nie kontroluje katalogów dostarczanych przez zewnętrzne pluginy.

Obsługa zagnieżdżonych `AGENTS.md`, symlinków i metadanych skilli zależy od harnessu. Nowe wskazówki sprawdzaj w świeżej sesji każdego używanego harnessu. Dokumentację integracji znajdziesz w [integrations.md](../integrations/README.md).
