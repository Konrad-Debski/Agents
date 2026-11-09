# Indeks skilli

Użyj tej mapy, gdy harness nie pokazuje katalogu skilli. Otwórz procedurę pasującą do zadania. Tryb poniżej wynika z metadanych, a jego obsługa zależy od [harnessu](../integrations/README.md). Wskazanie pliku nie upoważnia do publikacji ani wdrożenia.

| Zadanie | Skill | Tryb | Wynik |
| --- | --- | --- | --- |
| Aktualna dokumentacja bibliotek, SDK, API, CLI i chmury | [context7-mcp](../../skills/context7-mcp/SKILL.md) | Dobór przez agenta | Odpowiedź lub implementacja oparta na dokumentacji |
| Redakcja tekstu | [unslop](../../skills/unslop/SKILL.md) | Ręczny | Poprawiony tekst |
| Pisanie opisu PR | [pr](../../skills/pr/SKILL.md) | Dobór przez agenta | Opis PR |
| Publikacja PR i merge | [create-pr](../../skills/create-pr/SKILL.md) | Ręczny | Zweryfikowany wynik publikacji |
| Przeniesienie zmian motywów między spółkami | [famicord-sync](../../skills/famicord-sync/SKILL.md) | Dobór przez agenta | Zmiany, walidacja i status każdego repozytorium |
| Brief sekcji WordPress/ACF z Figmy | [figma](../../skills/figma/SKILL.md) | Ręczny | Brief, bez implementacji |
| Analiza kopii WordPressa lub SQL po włamaniu | [wp-audit](../../skills/wp-audit/SKILL.md) | Dobór przez agenta | Raport dowodów i zakresu analizy |
| Aktualizacja WordPressa, wtyczek i ACF | [wp-update](../../skills/wp-update/SKILL.md) | Dobór przez agenta | Wersje, walidacja i status publikacji |
| Formatowanie wklejonych powiadomień o aktualizacjach | [wp-update-list](../../skills/wp-update-list/SKILL.md) | Dobór przez agenta | Lista wersji, bez aktualizacji projektu |
| Doprecyzowanie planu | [grill-me](../../skills/grill-me/SKILL.md) | Ręczny | Wywiad według [grilling](../../skills/grilling/SKILL.md) |
| Pisanie instrukcji dla agentów | [writing-for-agents](../../skills/writing-for-agents/SKILL.md) | Dobór przez agenta | Instrukcje i warunki odczytu |
| Diagnoza błędu lub regresji wydajności | [diagnosing-bugs](../../skills/diagnosing-bugs/SKILL.md) | Dobór przez agenta | Potwierdzona przyczyna i weryfikacja naprawy |
| Retrospektywa sesji programowania | [retro](../../skills/retro/SKILL.md) | Ręczny | Propozycje usprawnień środowiska agenta |
| Przekazanie pracy do kolejnej sesji | [handoff](../../skills/handoff/SKILL.md) | Ręczny | Dokument przekazania w katalogu tymczasowym |
| Implementacja lub naprawa metodą TDD | [tdd](../../skills/tdd/SKILL.md) | Dobór przez agenta | Zachowanie zweryfikowane testem napisanym przed implementacją |
| Projektowanie interfejsów i poprawa testowalności | [codebase-design](../../skills/codebase-design/SKILL.md) | Dobór przez agenta | Zasady projektowania modułów |
| Implementacja z wykorzystaniem istniejących wzorców | [ponytail](../../skills/ponytail/SKILL.md) | Dobór przez agenta | Mały, kompletny zakres zmian |
| Przegląd poprawności i zbędnego kodu | [ponytail-review](../../skills/ponytail-review/SKILL.md) | Dobór przez agenta | Raport przeglądu, bez zmian kodu |

## Wspólne referencje

`wp-update` i `famicord-sync` czytają [protokół publikacji](../../skills/create-pr/references/workflow.md) dopiero przed tą fazą. Jest to odczyt dokumentu, bez wywoływania ręcznego `create-pr`. Dla odnośników do zasad stylu w globalnej mapie również odczytaj wskazany plik jako referencję.

Protokół publikacji odczytuje `pr` przy przygotowaniu opisu. `pr` odpowiada za treść opisu, a protokół za publikację i merge. Samo pisanie opisu nie upoważnia do tych operacji.

`grill-me` wymaga `grilling`. W harnessie bez narzędzia `Skill` odczytaj oba pliki. Samo zainstalowanie skilla nie rozpoczyna wywiadu.

`retro` korzysta z `writing-for-agents`, a `tdd` z `codebase-design`, gdy trzeba zaprojektować interfejs pod testy. Symlinki całych katalogów zachowują referencje TDD oraz projektowania modułów. `tdd` odsyła do `code-review` przy omawianiu etapu przeglądu; ten skill pozostaje w upstream, a osobno dostępny `ponytail-review` ma własną procedurę.

Opisy `tdd` i `codebase-design` wystarczają do doboru przez agenta. `retro` i `handoff` zachowują ręczny tryb wywołania. Ich mapa pozostaje w tym indeksie, bez dodatkowych wpisów w globalnym `AGENTS.md`.

Dobór źródeł, zależności i aktualizacje opisuje [upstream.md](upstream.md). Własne instrukcje wykonawcze są po angielsku. Dokumentacja użytkownika i ustalone polskie komunikaty pozostają po polsku.
