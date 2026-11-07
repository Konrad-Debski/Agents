# Requested delivery formats

### Changed website list on request

When the user asks to list websites with changes, return one fenced `text` code block containing a bulleted list of plain website URLs, one `- https://<domain>/` per line. Use the website mapping in [targets.md](targets.md), including the staging addresses for Famicord and IR. Include only websites changed in the current task; omit not-applicable, unchanged and blocked targets. Keep any status clarification outside the code block.

```text
- https://www.pbkm.pl/
- https://stageir.famicord.com/
```

When a Crioestaminal ZIP has been prepared, omit Crioestaminal from the main domain list and place the following separate `text` code block below it, preserving the wording and numbered item exactly. Keep the actual ZIP download link outside the code block.

```text
Przygotowałem też plik zip z poprawkami:

1. https://crioestaminal.pt/
```

### Changed file directory paths on request

When the user asks for links or paths to changed files, including files to replace through FileZilla, provide paths to their containing directories, omitting the filenames. Use a separate fenced `text` code block for each affected directory in each repository. Put exactly two plain paths inside each block: the absolute local directory path first, then the corresponding server directory path. End both paths with `/`. List a directory only once when multiple changed files share it. Do not use Markdown links, tables, labels or commands inside the blocks.

```text
<absolute-local-repository-path>/<relative-directory-path>/
/public_html/<domain>/<relative-directory-path>/
```

Use the actual local paths and the correct website domain, accounting for staging and repository names that differ from domains. Apply the server root exceptions in [targets.md](targets.md) before using the general `/public_html/<domain>/` layout. Prefer verified server paths. If FTP roots are unknown, state once before the blocks that `/public_html/<domain>/` is an assumed layout. Listing paths does not authorize uploading files or deployment.

### Crioestaminal ZIP on final link requests

When the user asks for links at the end of a task that changed `crioestaminal.pt`, also create a ZIP with that repository's task changes and provide a clickable download link. This also applies when the user writes "crioesteminal". Include the final validated changed files at their paths relative to the WordPress root, such as `wp-content/themes/starter-empressia/...`, without an enclosing repository folder. Add a short English `readme.txt` at the archive root explaining where to upload the files and which existing files to replace. Exclude unrelated local changes. Store the ZIP in a task-specific folder under `~/.agents/artifacts/`, expanding the current user home, and verify its contents before linking it. Keep generated archives out of Git. Record the archive's absolute path in the run record. Do not create an empty package when Crioestaminal has no task changes. Preparing the archive does not authorize uploading it.
