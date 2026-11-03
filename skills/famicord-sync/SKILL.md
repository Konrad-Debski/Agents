---
name: famicord-sync
description: 'Use to sync Famicord WordPress themes or port a commit, diff, or selected current file changes across companies in ~/Dev. Preserve local customizations, update develop, validate PHP and Node 18 production builds, and publish matching branches and commits through confirmed PR merges.'
argument-hint: 'Source repository and commit, range, diff, or requested change; optional target repositories'
---

# Famicord theme synchronization

Port shared behavior into each company's existing implementation, not necessarily into identically named files. Preserve company customizations and unrelated user work. A successful patch or build alone does not prove behavioral compatibility.

## Inputs and scope

- Require a source repository and identifiable change: commit, range, supplied diff, or precise behavior. Distinguish the exact commit diff from the latest committed state of files identified by that commit. Clarify ambiguity once, then freeze source SHAs and paths. For merge commits, establish the intended parent; for ranges, establish endpoint diff versus commit sequence. Keep the source worktree unchanged unless explicitly asked to edit it.
- Use the registry below, excluding the source and requested exclusions. An explicit target list replaces the default. Resolve company aliases by verified remote identity; clarify ambiguous names.
- Limit edits to the shared theme and dependencies required for the behavior. Ask before including bundled changes elsewhere, extending missing functionality, or changing runtime requirements.
- The workflow includes local commits, push, PR creation and ordinary merge into `develop`, subject to publication confirmation. Database changes and deployment commands are outside scope. Disclose known merge-triggered deployments before confirmation.

## Execution and run state

- Keep one structured run record outside company repositories. Record source SHAs and scope, exclusions, repository identities, starting states, worktree paths, base SHAs, adaptations, common branch and commit plan, validation commands/results, validated HEADs, PR URLs and merge SHAs. Update after each completed target or publication action. Store no credentials.
- On resume, verify recorded state against local Git and GitHub, then continue the first unfinished step. Existing PRs or branches are reusable only after verifying they belong to this run. Revalidate if code or the validated HEAD changed.
- Use one active command per shared terminal, including subagent commands. Parallelize independent reads only; run builds sequentially. Wait for confirmed completion before sending another command. If a tool returns before completion, use its execution ID and supported completion/output mechanism; do not poll or replace a running process with another command.
- Record command, working directory, exit code and decisive output. Cancellation, code `130`, a truncated log, a success line from an earlier gate, or a build-start message is not a pass. Set `GH_PAGER=cat` and `PAGER=cat` for CLI work and disable shell spelling prompts when they interfere.
- Prefer bounded, theme-scoped reads and structured summaries. Do not inventory unrelated plugin dependencies. Keep progress updates to phase changes, actual results and blockers.

## 1. Preflight and identify repositories

1. Read applicable source and target instructions and `~/.agents/skills/create-pr/SKILL.md`. Treat that procedure as the authority for PR naming, confirmation, templates, lookup and ordinary merge. If unavailable, record publication as blocked; independent local work can continue.
2. Before implementation, check Git, Git LFS when configured, PHP, nvm, Node 18, the required Yarn version, and publication tools/authentication. Prefer authenticated `gh` for batch publication where tool instructions permit it. Do not print tokens or request secrets in chat. Installation or login requiring user action is a separate setup step; ask before installing missing tools.
3. Resolve `~/Dev`. Match clones by normalized HTTPS/SSH GitHub remotes, not folder names. Prefer the matching `~/Dev/<repository-name>` clone. Clarify conflicts or duplicate matching clones. Clone missing targets from registry URLs without overwriting directories; record authentication/network failures and continue independent targets.
4. Record branch, HEAD, tracked/untracked changes and local `develop` state before changing anything. Preserve user work without automatic reset, stash, clean or discard. Dirty originals will use isolated linked worktrees.
5. Locate the theme, build directory, package scripts, lockfile, runtime declarations, relevant tests and Git hooks. Inspect hooks before checkout, commits or push; hooks must not silently trigger out-of-scope Docker or deployment operations. An absent equivalent theme is a blocker, not permission to introduce one.

Complete when each selected target has a verified identity and preserved starting state, or an explicit blocker, and environment/publication prerequisites are known.

## 2. Freeze source and update target bases

1. Resolve the agreed source references to fixed SHAs, fetching only necessary refs without switching the source worktree. Inspect scoped additions, modifications, renames and deletions from committed versions. Separate shared behavior from source-company customization and unrelated changes.
2. Fetch target `develop` from the verified remote before detailed compatibility analysis. Missing `develop` or fetch failure blocks that target; do not substitute another base. Avoid analyzing stale checkout code and then repeating the analysis after updating it.
3. For clean originals, check local `develop` for divergence or unpushed commits. Ask if either exists. Otherwise switch to `develop`, creating its tracking branch if needed, then run `git pull --ff-only <remote> develop`. Record the resulting remote base SHA; no additional pull/merge cycle is needed without evidence of a newer base.
4. For dirty originals, create an isolated linked worktree at the fetched remote `develop` SHA. Leave the original branch, local `develop` and user changes untouched. Record this explicit exception to switching/pulling the original worktree. Analyze that isolated base.

Complete when source scope and revisions are fixed and each available target has a verified current `develop` base, or an explicit blocker.

## 3. Map behavior and plan adaptations

1. Read the source's controlling code and immediate callers/dependencies. Define observable acceptance conditions and the cheapest focused check that can disprove the intended behavior.
2. Map each shared behavior to its target owner by responsibility, symbols, hooks and callers. A missing filename does not establish missing behavior. Find an existing equivalent implementation or extension point before declaring a blocker or adding a new abstraction. Record where the behavior currently lives and how it will be adapted.
3. Check local translations, schemas, configuration, URLs, integrations, conditional branches, variants, instance selectors and limits. Preserve existing translations; translate new visible strings into the language used by the corresponding target UI, not a language guessed from the domain. If the target supports multiple variants or instances, account for each without imposing source-only defaults.
4. Classify each source change per target as adapt, already present, not applicable with a reason, or blocked. Ask concrete questions only for unresolved behavioral choices or scope changes. Continue independent targets while answers are pending.
5. Choose one common branch with a `create-pr`-recognized type prefix and identical full commit messages for equivalent logical changes. Check local and remote branch collisions across targets and choose one common alternate if needed. Clarify conflicting commit conventions. Create topic branches only for feasible changes, from recorded bases; already-complete targets need validation, not empty commits or PRs.
6. Briefly report frozen source, selected targets, adaptations/blockers, branch and commit plan before editing. If the base changed since analysis, assess the changed slice before using a new base.

Complete when every shared behavior has a target mapping or explicit disposition, acceptance checks are defined, and implementation branches have verified bases.

## 4. Adapt and review

1. Process each target independently. Form a local hypothesis, make the smallest compatible edit, then immediately run its focused check before further edits. Repair local failures and repeat that check before expanding scope. Reuse existing tests/helpers; new nontrivial behavior needs reusable regression proof rather than an unrecorded manual assertion.
2. Port required dependencies and callers together, including deletion/rename effects. Preserve target structure and customization. Do not copy whole divergent files or blindly cherry-pick. For mechanical repetition, use a bounded transformation with unique-anchor assertions and per-target checks; stop that target on an anchor mismatch.
3. Before production builds, review the adapted slice for lost variants/settings, behavior changes, missing callers and security risks. Tests must reproduce relevant runtime/framework settings, including actual escaping and data-handling behavior, rather than relying on permissive mocks or safer defaults than production.
4. Use existing local runtime/browser checks where available. Ask before provisioning infrastructure or changing configuration. Record which runtime and visual requirements cannot be verified; passing mocked checks does not prove live integration.

Complete when implementation coverage is accounted for, focused checks pass, and task-specific review findings are resolved or explicitly blocking.

## 5. Validate and commit final code

Use local tools without starting or stopping Docker containers.

1. Load nvm and select Node 18 in the same shell used for installation/build. Confirm `node --version` is `v18.*`; install Node 18 with nvm if absent. If nvm is unavailable or declared/locked dependencies conflict with Node 18, record the blocker and ask before changing runtime requirements, dependency versions or using `--ignore-engines`.
2. Verify the required Yarn version, lockfile presence and changes before installation. Existing `node_modules` is not evidence that dependencies match the current base. When installation is needed, use the target's pinned package manager with lockfile-preserving options. A missing, removed or unexpectedly changed lockfile blocks installation until ownership and intended state are established.
3. Avoid package-manager metadata churn, including automatic runtime/package-manager pinning. Separate network, authentication, cache, engine and code failures. Diagnose the decisive error before retrying. Use an isolated task cache if the shared cache is corrupt; do not delete shared caches, rewrite lockfiles or upgrade packages merely to obtain a build. Preserve user changes made during the run.
4. Run `php -l` on each added/modified/renamed task PHP file using absolute paths or paths relative to the command's verified directory. Run applicable configured PHP checks and focused tests. Run relevant frontend lint/type checks where configured. A failed command blocks the gate even if later commands pass.
5. Inspect the build script and confirm it is production, not development/watch. Run the documented production `yarn build` sequentially in every available target, including already-present changes. Record command, directory, Node/Yarn versions, exit code and decisive output. If no equivalent production script exists, ask rather than inventing one.
6. Review the final diff against the recorded base and starting state: whitespace, lost customization, unexpected files, dependencies and generated output. Keep tracked production output when repository policy requires it; leave ignored output untracked. Ask if policy is unclear or output overlaps user work. Reserve a shared asset commit message only where tracked output needs a separate commit.
7. Stage only task-owned files/hunks, inspect staged diffs and run repository hooks. Use the common full messages; omit empty commits for already-present/not-applicable changes. Record necessary target-specific repair commits, using identical messages wherever the same repair applies.
8. Confirm no uncommitted task changes remain. Record validated final HEAD, changed paths and all gate outcomes. If commits/hooks or later repairs change code, rerun affected checks and builds before recording the new validated HEAD.

Complete when each target has explicit compatibility, behavior, PHP and production build results, with final committed HEADs for implemented changes. Failed/unavailable gates remain failed/blocked; unrelated failures do not authorize unrelated repairs.

## 6. Publish using create-pr

Follow the loaded `create-pr` procedure, with these batch-specific requirements:

1. Use each actual target repository and task branch, not the VS Code workspace branch. Override the procedure's default base with `develop`. Present repository list, common branch, generated title, base and merge method for explicit VS Code question-tool confirmation. One confirmation covers only those repositories/settings; keep it across retries unless scope/settings change.
2. Publish only complete targets with passing local gates and the recorded validated HEAD. Push without force. Verify the remote head SHA and look up existing PRs before creating any. Read each target's PR template and include target adaptations, validation evidence and unverified requirements without inventing ticket references.
3. Use noninteractive CLI publication when available and permitted. If a tool returns an interactive form, stop and wait for submission; the form is not a created PR. Record creation only after receiving a real PR number/URL and verifying its head and base. A closed unmerged PR or duplicate matches requires investigation, not an automatic replacement.
4. Check statuses, check runs, reviews, mergeability and effective branch protections for the current head. Watch pending checks with a supported command. Use ordinary merge with the generated title and exact validated head guard, such as `gh pr merge --merge --subject <title> --match-head-commit <sha>`. No squash, rebase or administrator override. Verify GitHub reports merged and record the merge SHA. Scheduled auto-merge is pending until observed as merged.
5. If checks fail or protections/conflicts block merge, record the blocker and continue independent targets. Scoped repairs or conflict resolutions require fresh compatibility checks, PHP validation and Node 18 production build before pushing/merging the new validated HEAD.

Complete when every publishable target has a confirmed merged PR or an explicit pending/failed/blocked outcome. PR creation alone is not completed synchronization.

## 7. Report and stop

- Keep detailed evidence in the run record: source/base/validated/merge SHAs, changed paths, adaptations/exclusions, commit messages, commands/directories, gate outcomes, PR URLs and outstanding blockers.
- In chat, give a concise per-target status with PR links, common branch/commit plan, validation summary, blockers and unverified requirements. Reference the run record without repeating every path and command.
- Classify targets as merged, PR pending, already present, not applicable, partially completed or blocked. Do not declare all projects synchronized while a selected target, required gate or merge is unresolved.
- Stop after scoped implementation, verification and confirmed publication outcomes. No unrelated cleanup or deployments.

## Website addresses

Use this mapping for website links and live checks. Repository names are not always public domains. Famicord and IR use the staging addresses below for this workflow; label them as staging, not production. These URLs do not establish FTP document roots or authorize deployments.

| Repository in empressia-co | Website URL | Environment |
| --- | --- | --- |
| wordpress-biogenis.ro | https://biogenis.ro | Production |
| wordpress-nabassaite.lv | https://cilmessunubanka.lv | Production |
| wordpress-famicord.ch | https://famicord.ch | Production |
| wordpress-famicord.lu | https://famicord.lu | Production |
| wordpress-krio.hu | https://krio.hu | Production |
| wordpress-sevibe.es | https://sevibe.es | Production |
| wordpress-kordonkanibankasi.com | https://kordonkanibankasi.com | Production |
| famicord.com | https://stage.famicord.com | Staging |
| ir.famicord.com | https://stageir.famicord.com | Staging |
| wordpress-famicordcryobank.ch | https://famicordcryobank.ch | Production |
| smartcells.ae | https://smartcells.ae | Production |
| smartcells.com | https://smartcells.com | Production |
| sorgente.com | https://sorgente.com | Production |
| pupecnikovakrev.cz | https://pupecnikovakrev.cz | Production |
| smartcells.com.hk | https://smartcells.com.hk | Production |
| cakam-babatko.sk | https://cakam-babatko.sk/ | Production |
| crioestaminal.pt | https://crioestaminal.pt | Staging |

## Repository registry

This is the default target allowlist. Folder names are hints; Git remote identity is authoritative. Clone missing selected repositories from these URLs.

- https://github.com/empressia-co/pbkm-multisite
- https://github.com/empressia-co/wordpress-biogenis.ro
- https://github.com/empressia-co/wordpress-nabassaite.lv
- https://github.com/empressia-co/wordpress-famicord.ch
- https://github.com/empressia-co/wordpress-famicord.lu
- https://github.com/empressia-co/wordpress-krio.hu
- https://github.com/empressia-co/wordpress-sevibe.es
- https://github.com/empressia-co/wordpress-kordonkanibankasi.com
- https://github.com/empressia-co/famicord.com
- https://github.com/empressia-co/ir.famicord.com
- https://github.com/empressia-co/wordpress-famicordcryobank.ch
- https://github.com/empressia-co/smartcells.ae
- https://github.com/empressia-co/smartcells.com
- https://github.com/empressia-co/sorgente.com
- https://github.com/empressia-co/pupecnikovakrev.cz
- https://github.com/empressia-co/smartcells.com.hk
- https://github.com/empressia-co/cakam-babatko.sk
- https://github.com/empressia-co/crioestaminal.pt