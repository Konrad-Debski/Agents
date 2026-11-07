# Źródła i decyzje organizacji wiedzy

## Film i wnioski

Źródło: Kyle Cook, Web Dev Simplified, [Why Your AI Generates Crap Code - And How to Fix It](https://www.youtube.com/watch?v=jojMVmRZABw). Analiza opiera się na [transkrypcji całego filmu](https://transcriptly.libmap.cn/transcripts/jojMVmRZABw) oraz tytule i rozdziałach potwierdzonych w danych YouTube. Nie oceniano osobno obrazu demonstracji.

- Od 00:45 Kyle rozróżnia prompt systemowy, instrukcje, skille, dokumentację i kod. Każdy wczytany materiał zajmuje kontekst.
- Od 03:55 pokazuje koszt rozbudowanych instrukcji, duplikacji i dopisywania kolejnych reguł po każdej pomyłce.
- Od 07:23 proponuje krótkie instrukcje z warunkowymi odnośnikami do dokumentacji tematycznej. Jeden zawsze czytany, obszerny plik zastępczy zachowuje ten sam problem.
- Od 13:53 omawia wspólne źródło `AGENTS.md` i `CLAUDE.md` przez symlink, a od 15:50 instrukcje dla wybranych części projektu.
- Od 18:47 umieszcza powtarzalne, wyspecjalizowane zadania w skillach. Ich nazwy i opisy też zajmują kontekst, więc liczy się dobór zestawu i zwięzłość opisów.

## Przyjęte rozwiązania

- Główny `AGENTS.md` zawiera wyłącznie mapę wiedzy i warunki odczytu.
- Context7 ma jedno źródło procedury. Skill stylu jest dobierany do pisania, bez wymuszonego odczytu przy każdym zadaniu.
- Dokumentacja ma katalogi `operations/`, `integrations/`, `contributing/` i `skills/`, zależnie od rodzaju pracy.
- Warunkowe dane Famicord oraz referencje audytu WordPressa są obok odpowiednich skilli. Obowiązkowe kontrole i zasady publikacji pozostają w głównych procedurach.
- Źródła Ponytail i Matt Pocock są przypięte w submodułach. Wybrane całe katalogi są udostępnione przez symlinki, z zachowaniem zależności i metadanych. Dobór opisuje [upstream.md](../skills/upstream.md).
- Nowe skille Claude Code udostępnia istniejący adapter uruchamiany po synchronizacji. Testy obejmują dodanie skilla, aktualizację submodułu, usunięcie dowiązania i ochronę osobistych skilli.

## Sprawdzanie w rzeczywistych zadaniach

Po aktualizacji rozpocznij świeżą sesję harnessu, aby katalog skilli i instrukcje nie pochodziły z poprzedniej wersji. Dla działającego Claude Code można też użyć odświeżenia opisanego w [synchronization.md](../operations/synchronization.md).

Przy kolejnych rzeczywistych zadaniach sprawdź dobór źródeł: pytanie o API powinno prowadzić do Context7, aktualizacja WP do `wp-update`, a zmiana instrukcji do zasad organizacji wiedzy. Raporty zadań nie powinny wymagać wczytania całego katalogu skilli. To obserwacja zachowania modeli, której same testy plików nie zastępują.

Dodatkowe skille dodawaj po rozpoznaniu brakującej procedury. [Zasady utrzymania kontekstu](context-management.md) opisują, gdzie zapisać nowe informacje.
