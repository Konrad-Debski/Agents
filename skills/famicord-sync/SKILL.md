---
name: famicord-sync
description: Use when asked to port a commit, diff or shared WordPress theme change across Famicord company repositories in ~/Dev. Preserve company customizations.
argument-hint: 'Source repository and commit, range, diff, or requested change; optional target repositories'
---

# Famicord theme synchronization

Port shared behavior into each company's existing implementation, not necessarily into identically named files. Preserve company customizations and unrelated user work. A successful patch or build alone does not prove behavioral compatibility.

## Inputs and scope

- Require a source repository and identifiable change: commit, range, supplied diff, or precise behavior. Distinguish the exact commit diff from the latest committed state of files identified by that commit. Clarify ambiguity once, then freeze source SHAs and paths. For merge commits, establish the intended parent; for ranges, establish endpoint diff versus commit sequence. Keep the source worktree unchanged unless explicitly asked to edit it.
- Read [references/targets.md](references/targets.md) when selecting targets. Use its registry, excluding the source and requested exclusions. It also lists website URLs and staging deployment exceptions needed before publication. An explicit target list replaces the default. Resolve company aliases by verified remote identity; clarify ambiguous names.
- Limit edits to the shared theme and dependencies required for the behavior. Ask before including bundled changes elsewhere, extending missing functionality, or changing runtime requirements.
- The workflow includes local commits, push, PR creation and ordinary merge into `develop`, subject to publication confirmation. Database changes and deployment commands are outside scope. Disclose known merge-triggered deployments before confirmation.

## Execution and run state

- Work only in each repository's main directory under `~/Dev`. Do not create linked worktrees, temporary working copies or additional clones to bypass local changes. Leave existing user-modified files untouched whenever possible; if they block checkout or updating, temporarily stash them as described in section 2.
- Keep one structured run record outside company repositories. Record source SHAs and scope, exclusions, repository identities, starting states, main repository paths, temporary stash SHAs and restoration status, base SHAs, adaptations, common branch and commit plan, validation commands/results, validated HEADs, PR URLs and merge SHAs. Update after each completed target or publication action. Store no credentials.
- On resume, verify recorded state against local Git and GitHub, then continue the first unfinished step. Existing PRs or branches are reusable only after verifying they belong to this run. Revalidate if code or the validated HEAD changed.
- Use one active command per shared terminal, including subagent commands. Parallelize independent reads only; run builds sequentially. Wait for confirmed completion before sending another command. If a tool returns before completion, use its execution ID and supported completion/output mechanism; do not poll or replace a running process with another command.
- Record command, working directory, exit code and decisive output. Cancellation, code `130`, a truncated log, a success line from an earlier gate, or a build-start message is not a pass. Set `GH_PAGER=cat` and `PAGER=cat` for CLI work and disable shell spelling prompts when they interfere.
- Prefer bounded, theme-scoped reads and structured summaries. Do not inventory unrelated plugin dependencies. Keep progress updates to phase changes, actual results and blockers.

## 1. Preflight and identify repositories

1. Read applicable source and target instructions. Check publication prerequisites without loading the publication protocol until phase 6. Missing access blocks publication, not independent local work.
2. Before implementation, check Git, Git LFS when configured, PHP, nvm, Node 18, the required Yarn version, and publication tools/authentication. Prefer authenticated `gh` for batch publication where tool instructions permit it. Do not print tokens or request secrets in chat. Installation or login requiring user action is a separate setup step; ask before installing missing tools.
3. Resolve `~/Dev`. Match clones by normalized HTTPS/SSH GitHub remotes, not folder names. Prefer the matching `~/Dev/<repository-name>` clone. Clarify conflicts or duplicate matching clones. Clone missing targets from registry URLs without overwriting directories; record authentication/network failures and continue independent targets.
4. Record branch, HEAD, tracked/untracked changes and local `develop` state before changing anything. Preserve user work without reset, clean or discard. Local changes do not justify a separate worktree or working copy. Use a temporary stash only when needed, following section 2.
5. Locate the theme, build directory, package scripts, lockfile, runtime declarations, relevant tests and Git hooks. Inspect hooks before checkout, commits or push; hooks must not silently trigger out-of-scope Docker or deployment operations. An absent equivalent theme is a blocker, not permission to introduce one.

Complete when each selected target has a verified identity and preserved starting state, or an explicit blocker, and environment/publication prerequisites are known.

## 2. Freeze source and update target bases

1. Resolve the agreed source references to fixed SHAs, fetching only necessary refs without switching the source worktree. Inspect scoped additions, modifications, renames and deletions from committed versions. Separate shared behavior from source-company customization and unrelated changes.
2. Fetch target `develop` from the verified remote before detailed compatibility analysis. Missing `develop` or fetch failure blocks that target; do not substitute another base. Avoid analyzing stale checkout code and then repeating the analysis after updating it.
3. In the main repository directory, check local `develop` for divergence or unpushed commits. Ask if either exists. Preserve non-conflicting local changes in place. If local changes prevent checkout or updating, use the temporary stash procedure below. Otherwise switch to `develop`, creating its tracking branch if needed, then run `git pull --ff-only <remote> develop`. Record the resulting remote base SHA; no additional pull/merge cycle is needed without evidence of a newer base.
4. When a temporary stash is necessary, give it a run-specific label and record its exact SHA and original branch. Include untracked files if needed to preserve them. Never alter pre-existing stashes. Restore the saved changes, including their staged/unstaged state, as soon as the blocking update is complete and before final handoff. Verify restoration against the recorded starting state before dropping only this run's stash. If restoration conflicts, retain the stash and report the conflict; do not discard or overwrite user changes. Keep user changes out of task commits and validation evidence. Continue in the main repository directory throughout.

Complete when source scope and revisions are fixed and each available target has a verified current `develop` base, or an explicit blocker.

## 3. Map behavior and plan adaptations

1. Read the source's controlling code and immediate callers/dependencies. Define observable acceptance conditions and the cheapest focused check that can disprove the intended behavior.
2. Map each shared behavior to its target owner by responsibility, symbols, hooks and callers. A missing filename does not establish missing behavior. Find an existing equivalent implementation or extension point before declaring a blocker or adding a new abstraction. Record where the behavior currently lives and how it will be adapted.
3. Check local translations, schemas, configuration, URLs, integrations, conditional branches, variants, instance selectors and limits. Preserve existing translations; translate new visible strings into the language used by the corresponding target UI, not a language guessed from the domain. If the target supports multiple variants or instances, account for each without imposing source-only defaults.
4. Classify each source change per target as adapt, already present, not applicable with a reason, or blocked. Ask concrete questions only for unresolved behavioral choices or scope changes. Continue independent targets while answers are pending.
5. Choose one common branch with a conventional type prefix such as `feat/`, `fix/` or `refactor/` and identical full commit messages for equivalent logical changes. Check local and remote branch collisions across targets and choose one common alternate if needed. Clarify conflicting commit conventions. Create topic branches only for feasible changes, from recorded bases; already-complete targets need validation, not empty commits or PRs.
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
5. Inspect the build script and confirm it is production, not development/watch. Run the documented production `yarn build` sequentially in every available target, including already-present changes. Include Node/Yarn versions in the run record. If no equivalent production script exists, ask rather than inventing one.
6. Review the final diff against the recorded base and starting state: whitespace, lost customization, unexpected files, dependencies and generated output. Keep tracked production output when repository policy requires it; leave ignored output untracked. Ask if policy is unclear or output overlaps user work. Reserve a shared asset commit message only where tracked output needs a separate commit.
7. Stage only task-owned files/hunks, inspect staged diffs and run repository hooks. Use the common full messages; omit empty commits for already-present/not-applicable changes. Record necessary target-specific repair commits, using identical messages wherever the same repair applies.
8. Confirm no uncommitted task changes remain. Record validated final HEAD, changed paths and all gate outcomes. If commits/hooks or later repairs change code, rerun affected checks and builds before recording the new validated HEAD.

Complete when each target has explicit compatibility, behavior, PHP and production build results, with final committed HEADs for implemented changes. Failed/unavailable gates remain failed/blocked; unrelated failures do not authorize unrelated repairs.

## 6. Publish

Read [the publication protocol](../create-pr/references/workflow.md) now. It owns confirmation, naming, PR lookup, CI handling and ordinary merge. Apply these batch-specific settings:

- Use each actual target repository and task branch, with `develop` as base. One confirmation covers the presented repositories and common settings. Disclose the staging autodeploy exceptions from [references/targets.md](references/targets.md) before confirmation.
- Publish only targets with passing required gates and a recorded validated HEAD. Include company adaptations and unverified requirements in each PR.
- Record each target's merged, pending or blocked result and continue independent targets. A repair or conflict resolution requires fresh compatibility checks, PHP validation and a Node 18 production build before publication of the changed HEAD.

Complete when every publishable target has a verified merged PR or an explicit pending or blocked outcome. PR creation alone is not completed synchronization.

## 7. Report and stop

- In chat, give a concise per-target status with PR links, common branch/commit plan, validation summary, blockers and unverified requirements. Reference the run record without repeating every path and command.
- Classify targets as merged, PR pending, already present, not applicable, partially completed or blocked. Do not declare all projects synchronized while a selected target, required gate or merge is unresolved.
- Stop after scoped implementation, verification and confirmed publication outcomes. No unrelated cleanup or deployments.

When the user requests changed website URLs, changed file directory paths or final delivery links, read [references/delivery.md](references/delivery.md) before responding. That reference includes the required Crioestaminal ZIP for final link requests. Use the website and server-root mapping in [references/targets.md](references/targets.md).
