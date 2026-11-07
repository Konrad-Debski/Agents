# Composer-managed ACF Pro

Read when the owning project manifest manages ACF through Composer.

Run from the owning manifest directory inside the verified dev container:

```sh
composer update wpengine/advanced-custom-fields-pro
```

1. Verify that the owning manifest declares `wpengine/advanced-custom-fields-pro` before running the command. A different Composer-managed ACF distribution requires clarification of its package-specific update command.
2. Verify the resolved version against the latest stable release available from the configured authenticated package source. If the constraint prevents that version, stop this phase and report it. Do not broaden the update to all Composer dependencies or add `--with-all-dependencies` without agreement.
3. Check the lockfile and installed ACF version, inspect the diff, and run the relevant configured checks. Preserve expected plugin installation/symlink conventions. Include tracked package files only where repository policy requires them.
4. Stage only this phase's changes and commit using the repository's conventions, normally `chore: update ACF Pro`. If nothing changed, record that ACF is already current and omit an empty commit.
