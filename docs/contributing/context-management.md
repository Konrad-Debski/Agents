# Organizacja wiedzy dla agentów

Wczytuj przy zmianie instrukcji, skilli lub dokumentacji w `~/.agents`.

## Gdzie zapisać wiedzę

| Zawartość | Miejsce |
| --- | --- |
| Warunek odczytu i wskazanie źródła | Główny `AGENTS.md` |
| Konfiguracja, konwencje i utrzymanie | Tematyczny plik w `docs/` |
| Spójna procedura dla konkretnego zadania | `skills/<nazwa>/SKILL.md` |
| Szczegóły potrzebne tylko w określonym wariancie | `skills/<nazwa>/references/` |
| Wspólny protokół kilku procedur | Jedna referencja Markdown wskazana przez wszystkich odbiorców |
| Wiedza dotycząca jednego projektu | Instrukcje, dokumentacja lub skille tego projektu |

## Treść i warunki odczytu

- Główny `AGENTS.md` pozostaje mapą. Każdy odnośnik wskazuje temat i warunek odczytu. Otwieraj wyłącznie źródła potrzebne do zadania.
- Zachowuj spójne jednostki pracy. Wydzielaj warianty i obszerne referencje, gdy nie są potrzebne przy każdym użyciu. Krótki skill może pozostać jednym plikiem.
- Każda reguła ma jedno źródło. Współdzielone protokoły odczytuj jako pliki, bez wywoływania ręcznych skilli jako zależności. Zachowuj dotychczasowy tryb wywoływania skilli i wymagane zgody.
- Opis skilla określa intencję użytkownika i granicę wobec podobnych zadań. Kroki, komendy i format wyniku należą do treści lub referencji.
- Zachowuj istotne wyjątki środowiska, granice autoryzacji i sprawdzalne kryteria zakończenia. Usuwaj powtórzenia i ogólne porady, które nie zmieniają decyzji agenta.
- Pisz własne instrukcje wykonawcze i referencje po angielsku, dokumentację użytkownika po polsku. Zachowuj język danych wejściowych oraz wymaganych komunikatów. Nie utrzymuj tłumaczeń tej samej procedury w dwóch miejscach.

## Źródła i utrzymanie

Podstawą redakcji jest [seria For skill creators](https://agentskills.io/skill-creation/best-practices):

- [Quickstart](https://agentskills.io/skill-creation/quickstart): minimalna struktura i odkrywanie skilla.
- [Best practices](https://agentskills.io/skill-creation/best-practices): wiedza domenowa, zakres i warunkowe referencje.
- [Optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions): dobór na podstawie intencji i odróżnianie podobnych próśb.
- [Evaluating skills](https://agentskills.io/skill-creation/evaluating-skills): ocena rezultatów i przebiegu rzeczywistych zadań.
- [Using scripts](https://agentskills.io/skill-creation/using-scripts): automatyzacja powtarzanej pracy, gdy uzasadnia ją użycie.

Zmieniaj instrukcje na podstawie rozpoznanego problemu. Samo skrócenie tekstu lub poprawny frontmatter nie dowodzi lepszego działania. Przyszłe oceny powinny uwzględniać zarówno dobór skilla, jak i jakość wyniku. Automatyzację dodawaj dopiero dla powtarzanej pracy.

Źródła zewnętrzne są submodułami aktualizowanymi automatycznie do najnowszych wersji upstream. Nie edytuj ich plików. Ich dobór opisuje [upstream.md](../skills/upstream.md), a zasady aktualizacji [synchronization.md](../operations/synchronization.md).

## Ścieżki

Globalna mapa używa `~/.agents/...`, bo jest udostępniana przez symlinki poza repozytorium. Rozwijaj `~` do bieżącego katalogu domowego. W dokumentach i skillach używaj odnośników względem danego pliku.

Plik już odczytany pozostaje w kontekście rozmowy. Podział ogranicza przyszłe odczyty. Obsługa katalogu skilli, metadanych i odświeżania zależy od [harnessu](../integrations/README.md).
