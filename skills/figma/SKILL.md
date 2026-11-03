---
name: figma
description: Przygotuj precyzyjny brief implementacji nowej sekcji WordPress/ACF na podstawie projektu Figma
disable-model-invocation: true
argument-hint: "Wklej nazwę sekcji, adres(y) URL Figmy, treść, warianty i wymagania dotyczące interakcji"
---
Przygotuj brief implementacji nowej sekcji WordPress/ACF z Figma. Nie pisz kodu i nie twórz plików.

## Wejście

Otrzymasz brief w formie:

```text
Sekcja: ...
Desktop URL: ...
Mobile URL: ...
Kategoria: shared
Opis: ...
Warianty: ...
Interakcje: ...
Podobny blok: ...
```

Brakujące wartości oznacz `DECISION REQUIRED`. Gdy nie ma żadnego URL-a = blokada, najpierw poproś o node.

## Zasady

- Analizuj wskazane node'y Figma: desktop/mobile, stany, hierarchię, semantykę, interakcje, puste dane.
- Szukaj istniejących wzorców przed tworzeniem nowych: `blocks/`, `parts/`, `inc/media/`, grupy ACF.
- Używaj istniejących Heading, Button, Image, Video i ich ACF clones. Nowe pola tylko, gdy istniejący wzorzec nie wystarcza.
- Dla nowych grup ACF: top-level accordion zgodny z konwencją.
- Minimalna architektura: `block.json`, `index.php`, `index.twig`, ACF JSON. `index.ts`/`ts/`, `style.css`, partial tylko, gdy wymaga tego zachowanie lub reużycie.
- Zachowanie: native HTML/CSS, potem WordPress Interactivity, potem scoped TypeScript.
- Assety: najpierw `media()` i istniejące; zachowaj source, crop, alt ownership; waliduj `preview.webp` i `block.json`.
- Przestrzegaj `AGENTS.md` i `figma-sections.instructions.md`. Nie powielaj ich treści.

## Wynik

Zwięzły brief:

1. **Zakres** — nazwa, slug, kategoria, node'y, pewne fakty, `DECISION REQUIRED`.
2. **Layout** — DOM, desktop/mobile, warianty, stany.
3. **Mapa design → dane** — tabela: Element Figmy | Istniejący part/clone | Proponowane pole | Typ i reguły | Fallback | Semantyka/a11y.
4. **Architektura** — wymagane pliki, opcjonalne z powodem, wzorce reuse ze ścieżkami, wybór interakcji z uzasadnieniem.
5. **Assety i preview** — reuse, nowe assety, `preview.webp` i `block.json`.
6. **Plan implementacji** — max 8 kroków, łącznie z `./bin/link_block_jsons` i `php bin/check_acf_ids.php`.
7. **Kryteria akceptacji** — desktop/mobile, stany, puste/pełne dane, edytor i frontend, a11y, crop i responsive reordering.

Pisz krótko i technicznie. Nie powtarzaj danych wejściowych.
