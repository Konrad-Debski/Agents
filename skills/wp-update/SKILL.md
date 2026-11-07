---
name: wp-update
description: Use when asked to update WordPress core, plugins or ACF in a local project. For formatting pasted update notices, use wp-update-list instead.
argument-hint: 'Optional additional project names or paths under ~/Dev; default: current project'
---

# WordPress updates

Update the current WordPress project, plus any additional projects explicitly named under `~/Dev`. Process projects sequentially because `docker-stop-all` stops containers globally. This workflow authorizes local updates and commits; publication requires confirmation through the shared publication protocol in phase 6.

## Scope and blockers

- Resolve the current project from the workspace and Git root, even when the terminal starts in a theme directory. Resolve additional names to existing repositories under `~/Dev`, deduplicate them, and show the selected projects. An explicit request for only named projects replaces the default. Ask about ambiguous names; do not scan or update every project in `~/Dev`.
- Read each project's applicable instructions. Inspect its Git state, remote, Compose configuration, theme Composer manifest and lockfile, and required checks. Record the starting branch and SHA. A dirty worktree, divergent base, missing prerequisite or ambiguous theme blocks that project. Preserve user changes without automatic stash, reset, clean or force operations.
- Use the latest stable releases, not prereleases. Keep PHP, Composer constraints and lockfiles consistent. If a constraint, PHP version, license or unavailable premium download prevents the latest release, report the exact blocker. Do not silently call an older constrained release the latest or change constraints/runtime requirements without agreement.
- Report blockers promptly with the project, failed command, decisive error and required user action. Stop dependent steps for that project; continue independent selected projects. Never expose credentials or ask for secrets in chat.
- Run one terminal command at a time. Confirm its exit status before starting another command. Retain project, base SHA, branch, completed phases, versions, commit SHAs, checks and PR URL in run state so interruptions do not cause duplicate operations.

## 1. Update the base and create the branch

1. Check GitHub CLI availability and authentication if publication is expected. Missing publication access blocks that phase, not independent local updates. Read the publication protocol only at phase 6.
2. Prefer the repository's established integration branch, usually `develop`. Verify it against repository instructions and remote branches. If `develop` is absent, determine the documented main branch or ask when ambiguous. Use this same verified base for pull, branch creation and PR.
3. Fetch the verified remote. On a clean worktree, switch to the base and pull with `git pull --ff-only <remote> <base>`. A local base with unpushed commits or divergence blocks the update; do not merge or rebase it automatically.
4. Determine today's local date with `date +%F`. Create `chore/update-<YYYY-MM-DD>` from the refreshed base, using the `chore` prefix required by the publication naming convention. Check local and remote branch collisions first. Reuse only a verified branch from this run; otherwise ask instead of overwriting or inventing a suffix.

Complete when the update branch starts at the verified, refreshed base and the original worktree state is preserved.

## 2. Start this project's Docker environment

From the selected project's Compose directory on the host, run in order:

```sh
docker-stop-all
docker compose up -d
docker compose exec dev bash -l
```

1. Before stopping containers, tell the user that this command will stop all Docker containers, including unrelated projects. The requested workflow authorizes this action. Verify that `docker-stop-all` exists in the user's host shell; it may be a function or alias. If unavailable, report the blocker rather than substituting a different global shutdown command.
2. Confirm Compose starts successfully and the `dev` service is ready. Verify that its mounted WordPress files belong to this project and its database is either local to this Compose environment or hosted at `10.1.1.99`. The user has confirmed that `10.1.1.99` is their trusted local development database server; accept this host without asking again or requiring its IP to match the Compose database container. Verify that the selected database belongs to this project, and retain the backup requirement below. Stop on any other unexpected external or production database.
3. Inside the dev container, identify the WordPress root and the project's actual theme directory. Change into that directory, for example `cd wp-content/themes/starter-empressia`. Do not assume all projects use that theme name or container working directory.
4. Verify Composer, WP-CLI and database access. Record initial WordPress, plugin and ACF versions. Before database migrations, ensure a recoverable local database backup exists, or create one outside tracked files with restricted access. Keep dumps and credentials out of Git.

For noninteractive tool execution, use equivalent `docker compose exec -T dev bash -lc '<commands>'` calls. Preserve the login-shell environment and explicitly select the verified directory on each call. Run update commands inside the container; run Git commands from the host repository.

Complete when this project's dev service, paths and local database are verified and a database recovery point is available.

## 3. Determine ACF ownership

Inspect manifests, lockfiles, installation paths and symlinks before choosing the update method. A mu-plugin directory alone does not establish Composer ownership.

- Composer-managed ACF: read [references/composer-acf.md](references/composer-acf.md), update through the owning manifest and commit that phase separately.
- Regular-plugin ACF without Composer ownership: record its slug and version for phase 5. Skip the Composer command and separate ACF commit.
- Unmanaged mu-plugin or conflicting ownership: report the blocker and clarify the update method. Preserve the installed distribution.

Complete when ACF ownership is established and Composer-managed ACF is validated and committed, or regular-plugin ACF is assigned to phase 5.

## 4. Update WordPress core and commit

From the verified WordPress root inside the dev container:

```sh
wp core update && wp core update-db && wp language core update
```

1. Check each command's result. A failure blocks the phase even if files were partly updated. Database and ignored translation changes do not belong in a Git commit.
2. Verify the resulting stable core version and run `wp core verify-checksums`. Inspect changed files against the phase's starting state and run required core-related project checks.
3. Commit only this phase's tracked changes, normally `chore: update WordPress core`. Omit an empty commit when already current. An expected update that produces no deployable tracked files or dependency metadata requires checking the repository's deployment convention before claiming completion.

Complete when core, its local database schema and core translations are current, validation passes and tracked changes are committed.

## 5. Update all plugins and commit

From the verified WordPress root inside the dev container:

```sh
wp plugin update --all && wp language plugin update --all
```

1. First check whether WP-CLI proposes updating any Composer-managed plugin, including ACF. Updating it again through WP-CLI can desynchronize installed files and the lockfile. If ownership overlaps, report the blocker and ask to exclude those slugs from WP-CLI and update them through their owning manifest instead. Do not silently change the requested command or ignore a plugin.
	Include regular-plugin ACF identified in step 3 in `wp plugin update --all`, without a separate approval. Verify its installed version against the latest stable release for that distribution and include its tracked changes in the plugin-phase commit. For ACF Pro, a missing license, unavailable update source or failed premium download is a blocker, not evidence that it is already current. Never request license keys in chat.
2. Account for every plugin update result. WP-CLI may report individual failures despite a successful process exit. Identify remaining updates, failed downloads and premium plugins without an update source; these are unresolved outcomes, not successful updates.
3. Verify final plugin and translation update status. Run applicable repository checks and a local HTTP/frontend and admin smoke check when available. Report unavailable checks explicitly. Do not repair unrelated failures or provision extra infrastructure without agreement.
4. Inspect the final diff for unrelated files, secrets, database dumps and unexpected dependency changes. Stage only plugin-phase changes and commit, normally `chore: update WordPress plugins`. Omit an empty commit if already current.

Complete when all plugin updates are accounted for, required checks pass and task changes are committed. Failed or unavailable required gates block publication.

## 6. Create the PR and merge

Read [the publication protocol](../create-pr/references/workflow.md) now. Apply it to this project's repository, branch, verified base and validated HEAD. Include version changes and verification results in the PR. If no phase changed tracked files, report already current without an empty PR.

A failed or unavailable required local check blocks publication. Record the protocol's merged, pending or blocked result for the final report.

## 7. Report and stop

Give a concise per-project result: updated versions, validation status, PR URL and merged, already current, partial, pending or blocked outcome. Include outstanding user actions. Do not claim all projects are updated while a selected project or required phase remains unresolved.

Leave the last processed project's containers running. Do not restart unrelated containers, deploy, update themes, update unrelated Composer packages or delete branches unless separately requested.
