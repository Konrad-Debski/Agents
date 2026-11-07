---
name: context7-mcp
description: Use when a question or implementation depends on current library, framework, SDK, API, CLI or cloud-service documentation. Skip API-independent refactoring and general programming.
---

# Current documentation with Context7

Use Context7 for API syntax, configuration, version migration, porting between libraries, platforms or SQL dialects, library-specific debugging, setup and CLI usage. Prefer it over web search for library documentation, even when the API seems familiar. A framework name alone does not require a lookup when the task does not depend on its API.

1. Call `resolve-library-id` with `libraryName` and a `query` describing what to look up. Skip resolution only when the user supplies an exact `/org/project` ID.
2. Select by exact name, relevance, snippet coverage, source reputation and benchmark score. Prefer official sources with High or Medium reputation and a version-specific ID when the user names a version. Retry with an alternate name or query if the results do not match.
3. Call `query-docs` with the selected `libraryId` and a focused question. Query distinct concepts separately using the same ID; combine them only when asking how they interact.
4. Use the fetched documentation in the answer or implementation. Match the project's version and cite sources when available. If Context7 is unavailable or lacks the needed documentation, report that limitation and use official documentation as a fallback.
