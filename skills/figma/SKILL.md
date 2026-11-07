---
name: figma
description: Prepare a WordPress/ACF section implementation brief from Figma designs. Produces a brief only, not implementation code or general Figma editing.
disable-model-invocation: true
argument-hint: "Section name, desktop/mobile Figma URLs, content, variants and interactions"
---

# WordPress section brief from Figma

Return a concise implementation brief in the user's language. Do not implement the section or create files. Keep the existing skill name for compatibility.

## Inputs

Accept these fields, including the existing Polish format:

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

Mark unknown values `DECISION REQUIRED`. Without any Figma URL, ask for the target node before analysis. Distinguish observed design facts from proposed behavior.

## Project conventions

Read applicable project instructions and `figma-sections.instructions.md` when present. Inspect existing blocks, parts, media helpers and ACF groups before proposing new structures. The following defaults apply to themes using the `blocks/`, `parts/`, `inc/media/` and ACF-clone conventions. If the project uses another architecture, follow its documented equivalent and identify missing decisions.

- Reuse Heading, Button, Image, Video and their ACF clones. Add fields only for requirements existing parts cannot express. Use the project's top-level accordion convention for new groups.
- Start with `block.json`, `index.php`, `index.twig` and ACF JSON. Add TypeScript, CSS or partials only for required behavior or reuse.
- Prefer native HTML/CSS, then WordPress Interactivity, then scoped TypeScript, where supported by the project.
- Reuse `media()` and existing assets. Preserve source, crop and alt ownership. Account for `preview.webp` and `block.json` validation.
- Inspect desktop/mobile nodes, variants, states, interactions, semantics and empty data.

## Output

Use the following Polish labels for a Polish request. Translate labels for other languages.

1. **Zakres**: name, slug, category, nodes, confirmed facts and `DECISION REQUIRED`.
2. **Layout**: DOM, desktop/mobile behavior, variants and states.
3. **Mapa design → dane**: table with Figma element, existing part/clone, proposed field, type/rules, fallback and semantics/accessibility.
4. **Architektura**: required files, justified optional files, existing patterns with paths and interaction approach.
5. **Assety i preview**: reused/new assets, `preview.webp` and `block.json` requirements.
6. **Plan implementacji**: at most eight steps. Include `./bin/link_block_jsons` and `php bin/check_acf_ids.php` when the project provides them. Identify unavailable required checks rather than inventing replacements.
7. **Kryteria akceptacji**: desktop/mobile, states, empty/populated data, editor/frontend, accessibility, crop and responsive ordering.

Do not repeat the supplied input as a second description of the task.
