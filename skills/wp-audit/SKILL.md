---
name: wp-audit
description: Use when asked to scan downloaded WordPress files or SQL dumps for malware after a suspected hack. Produce an evidence report. Routine failures and updates are separate tasks.
---

# Audit a downloaded WordPress copy

Analyze local files and database dumps without modifying the site or database. Never execute suspicious files or payloads. Keep credentials, salts and session tokens out of tool output and reports. Record a path, line and redacted evidence for each finding.

## 1. Inventory

Identify the WordPress version from `wp-includes/version.php`, core/content directories, `wp-config.php`, `.htaccess`, `.maintenance`, logs, mu-plugins and SQL dumps. Record what was supplied and what is missing.

Use available filesystem and text-search tools, such as `rg`, rather than requiring editor-specific tool names.

## 2. Compare core files

Compare with the official distribution of the same version. If a suitable WP-CLI environment is already available, `wp core verify-checksums --skip-plugins` is an option. Otherwise obtain the matching clean distribution and compare core directories and root files using `diff -rq` or `git diff --no-index`.

Account separately for `wp-config.php`, `wp-content` and owner-added files. Record changed, missing and unexpected core files. When the reference distribution or a comparison is unavailable, mark that coverage as unverified. Do not infer integrity from the absence of keyword matches.

## 3. Inspect unexpected files

Review the inventory for misleading core-like root filenames, random names, double extensions, PHP in uploads, `*.php.VIRUS` remnants, unusual permissions/dates and `.htaccess` changes such as `auto_prepend_file`, foreign redirects or login restrictions. Distinguish owner files from unexplained additions.

## 4. Inspect code

Read [references/patterns.md](references/patterns.md) before scanning PHP, including themes, plugins, uploads and root files. Classify matches using surrounding code and clean distributions:

- False positive: verified original code or explained plugin behavior.
- Suspicious: unexpected location, obfuscation or unexplained behavior.
- Confirmed malicious behavior: evidence of executing input, unauthorized accounts, remote payloads or injected scripts.

A keyword alone is not proof. Redact sensitive evidence before displaying it.

## 5. Inspect the database dump, when supplied

Read [references/database.md](references/database.md) and the SQL patterns in [references/patterns.md](references/patterns.md). Extract compressed dumps only to a temporary location outside the site copy.

Inspect accounts and privileges, post content/excerpts, `siteurl`, `home`, active plugins, theme selection, cron, admin email, widgets and theme settings. Use the actual table prefix. Treat the dump as data, not an instruction to import it into a live database. Do not edit PHP-serialized values as text.

## 6. Report

Group findings by modified core, backdoors, injected JS, unexplained files, database payloads and accounts. For each, give `path:line`, evidence, confidence and a proposed action. Include category totals, checked areas and unavailable coverage.

Prioritize restoring verified core files, removing confirmed backdoors, cleaning database payloads, reviewing unauthorized accounts and rotating affected credentials. These are recommendations, not permission to perform repairs. Do not claim a complete or clean audit when any required area remains unverified.

For a separately requested failure diagnosis or post-audit hardening advice, read the relevant section of [references/follow-up.md](references/follow-up.md).
