"""Integration tests using local Git remotes and a simulated systemd manager.

Run with: python3 -m unittest discover -s tests -v
"""

import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git")


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="agents-sync-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.stubs = self.base / "bin"
        self.stubs.mkdir()
        self.home = self.base / "home"
        self.home.mkdir()
        self.env = dict(
            os.environ,
            GIT_CONFIG_GLOBAL="/dev/null",
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_COUNT="1",
            GIT_CONFIG_KEY_0="protocol.file.allow",
            GIT_CONFIG_VALUE_0="always",
            PATH=str(self.stubs) + os.pathsep + os.environ["PATH"],
            HOME=str(self.home),
            XDG_STATE_HOME=str(self.base / "state"),
            XDG_CONFIG_HOME=str(self.base / "config"),
            SYSTEMD_TEST_LOG=str(self.base / "systemd.log"),
        )
        for command in ("systemctl", "loginctl"):
            stub = self.stubs / command
            stub.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$SYSTEMD_TEST_LOG"\n')
            stub.chmod(0o755)

        local = self.base / "config/agents/local.json"
        local.parent.mkdir(parents=True)
        local.write_text('{"harnesses": []}')
        self.vendor = self.new_remote("vendor", "main")
        (self.vendor / "SKILL.md").write_text("Original vendor skill\n")
        self.commit(self.vendor, "vendor source")
        self.git(self.vendor, "push", "-u", "origin", "main")

        self.seed = self.new_remote("skills", "main")
        shutil.copytree(ROOT / "scripts", self.seed / "scripts")
        for directory in ("adapters", "mcp"):
            shutil.copytree(ROOT / directory, self.seed / directory, symlinks=True)
        shutil.copy(ROOT / ".gitignore", self.seed)
        shutil.copy(ROOT / "install.sh", self.seed)
        shutil.copy(ROOT / "AGENTS.md", self.seed)
        (self.seed / "skills").mkdir()
        (self.seed / "skills/skill.md").write_text("Original skill\n")
        (self.seed / "skills/remove.md").write_text("Remove later\n")
        for name, branch, remote in (
            ("cursor-plugins", "main", "vendor.git"),
        ):
            self.git(self.seed, "submodule", "add", "-b", branch,
                     str(self.base / remote), ".upstream/" + name)
        self.commit(self.seed, "initial skills")
        self.git(self.seed, "push", "-u", "origin", "main")
        self.repo = self.clone("computer a % dollars$")
        self.install(self.repo)

    def run_cmd(self, cwd, *args, success=True, env=None):
        result = subprocess.run(args, cwd=cwd, env=env or self.env,
                                text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout)
        return result

    def git(self, cwd, *args):
        return self.run_cmd(cwd, GIT, *args).stdout.strip()

    def identity(self, repo):
        for key, value in (("user.name", "Sync test"),
                           ("user.email", "sync@example.invalid"),
                           ("commit.gpgsign", "false")):
            self.git(repo, "config", "--local", key, value)

    def new_remote(self, name, branch):
        self.git(self.base, "init", "--bare", "--initial-branch=" + branch,
                 name + ".git")
        repo = self.base / (name + "-source")
        self.git(self.base, "clone", str(self.base / (name + ".git")), str(repo))
        self.identity(repo)
        return repo

    def clone(self, name):
        repo = self.base / name
        self.git(self.base, "clone", "--recurse-submodules",
                 str(self.base / "skills.git"), str(repo))
        self.identity(repo)
        return repo

    def commit(self, repo, message):
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-m", message)

    def install(self, repo):
        return self.run_cmd(repo, "bash", "install.sh")

    def sync(self, repo=None, success=True, env=None):
        return self.run_cmd(repo or self.repo, "bash", "scripts/sync/run.sh",
                            success=success, env=env)

    def advance(self, repo, filename):
        with (repo / filename).open("a") as handle:
            handle.write("\n# New upstream revision\n")
        self.commit(repo, "upstream update")
        branch = self.git(repo, "branch", "--show-current")
        self.git(repo, "push", "origin", branch)
        return self.git(repo, "rev-parse", "HEAD")

    def remove_legacy_sync_submodule(self):
        legacy = self.new_remote('legacy-sync', 'master')
        (legacy / 'git-sync').write_text('#!/usr/bin/env bash\nexit 0\n')
        self.commit(legacy, 'legacy sync fixture')
        self.git(legacy, 'push', '-u', 'origin', 'master')
        self.git(self.seed, 'submodule', 'add', '-b', 'master',
                 str(self.base / 'legacy-sync.git'), '.upstream/git-sync')
        self.commit(self.seed, 'install legacy sync')
        self.git(self.seed, 'push', 'origin', 'main')
        self.sync()
        # Match the historical checkout without using its real remote over the network.
        self.git(self.repo / '.upstream/git-sync', 'remote', 'set-url', 'origin',
                 'https://github.com/simonthum/git-sync.git')
        self.git(self.seed, 'rm', '.upstream/git-sync')
        self.commit(self.seed, 'retire legacy sync')
        self.git(self.seed, 'push', 'origin', 'main')

    def test_upgrading_an_existing_machine_archives_the_retired_submodule(self):
        self.remove_legacy_sync_submodule()
        self.sync()
        self.sync()
        self.install(self.repo)
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), '')
        archives = list((self.repo / '.git/agents-sync').glob('retired-git-sync.*/checkout'))
        self.assertEqual(len(archives), 1)
        self.assertEqual((archives[0] / 'git-sync').read_text(), '#!/usr/bin/env bash\nexit 0\n')
        self.assertEqual(self.git(archives[0], 'status', '--porcelain'), '')

    def test_installer_recovers_a_retired_checkout_left_by_an_older_runner(self):
        self.remove_legacy_sync_submodule()
        self.git(self.repo, 'pull', '--ff-only')
        self.install(self.repo)
        self.sync()
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), '')
        self.assertFalse((self.repo / '.upstream/git-sync').exists())

    def test_dirty_retired_checkout_is_preserved_by_sync_and_installer(self):
        self.remove_legacy_sync_submodule()
        self.git(self.repo, 'pull', '--ff-only')
        path = self.repo / '.upstream/git-sync/git-sync'
        path.write_text('Local work that must survive migration\n')
        for result in (self.sync(success=False), self.run_cmd(self.repo, 'bash', 'install.sh', success=False)):
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Preserved local changes', result.stdout)
        self.assertEqual(path.read_text(), 'Local work that must survive migration\n')
        self.assertFalse(list((self.repo / '.git/agents-sync').glob('retired-git-sync.*')))

    def test_retired_checkout_with_a_different_origin_is_not_archived(self):
        self.remove_legacy_sync_submodule()
        self.git(self.repo, 'pull', '--ff-only')
        checkout = self.repo / '.upstream/git-sync'
        self.git(checkout, 'remote', 'set-url', 'origin', 'https://example.com/personal.git')
        result = self.sync(success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('different origin', result.stdout)
        self.assertTrue((checkout / 'git-sync').exists())

    def test_archiving_a_clean_retired_checkout_preserves_its_local_commits(self):
        self.remove_legacy_sync_submodule()
        checkout = self.repo / '.upstream/git-sync'
        self.identity(checkout)
        self.git(checkout, 'switch', '-c', 'personal-work')
        (checkout / 'git-sync').write_text('Committed local customization\n')
        self.commit(checkout, 'local customization')
        local_head = self.git(checkout, 'rev-parse', 'HEAD')
        self.git(self.repo, 'pull', '--ff-only')
        self.install(self.repo)
        archive = next((self.repo / '.git/agents-sync').glob('retired-git-sync.*/checkout'))
        self.assertEqual(self.git(archive, 'rev-parse', 'HEAD'), local_head)
        self.assertEqual((archive / 'git-sync').read_text(), 'Committed local customization\n')

    def test_installer_is_repeatable_and_units_are_valid(self):
        self.git(self.repo, "submodule", "deinit", "--all")
        self.assertFalse((self.repo / ".upstream/cursor-plugins/SKILL.md").exists())
        self.install(self.repo)
        self.assertTrue((self.repo / ".upstream/cursor-plugins/SKILL.md").exists())
        self.install(self.repo)
        units = self.base / "config/systemd/user"
        self.assertIn("enable --now agents-sync.timer",
                      (self.base / "systemd.log").read_text())
        self.assertEqual(self.git(self.repo, "status", "--porcelain"), "")
        if shutil.which("systemd-analyze"):
            self.run_cmd(self.base, "systemd-analyze", "--user", "verify",
                         str(units / "agents-sync.service"),
                         str(units / "agents-sync.timer"))

    def test_local_edits_are_preserved_without_committing_or_pushing(self):
        before = self.git(self.repo, "rev-parse", "HEAD")
        (self.repo / "skills/skill.md").write_text("Edited skill\n")
        (self.repo / "skills/new.md").write_text("New skill\n")
        (self.repo / "skills/remove.md").unlink()
        self.assertNotEqual(self.sync(success=False).returncode, 0)
        self.assertEqual(before, self.git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(before, self.git(self.base / "skills.git", "rev-parse", "main"))
        self.assertEqual((self.repo / "skills/skill.md").read_text(), "Edited skill\n")
        self.assertTrue((self.repo / "skills/new.md").exists())
        self.assertFalse((self.repo / "skills/remove.md").exists())

    def test_sync_refreshes_claude_skills_from_remote_and_preserves_personal_skills(self):
        local = self.base / "config/agents/local.json"
        local.write_text('{"harnesses": ["claude-code"]}')
        env = dict(self.env)
        env.pop('CLAUDE_CONFIG_DIR', None)
        personal = self.home / '.claude/skills/personal/SKILL.md'
        personal.parent.mkdir(parents=True)
        personal.write_text('Personal skill\n')
        installed = self.home / '.claude/skills/vendor-skill'
        self.assertFalse(installed.exists())

        source = self.seed / 'skills/vendor-skill'
        source.symlink_to('../.upstream/cursor-plugins', target_is_directory=True)
        self.commit(self.seed, 'select a vendor skill')
        self.git(self.seed, 'push', 'origin', 'main')
        self.sync(env=env)
        self.assertTrue(installed.is_symlink())
        self.assertEqual(installed.resolve(), self.repo / '.upstream/cursor-plugins')
        self.assertEqual((installed / 'SKILL.md').read_text(), 'Original vendor skill\n')

        self.advance(self.vendor, 'SKILL.md')
        self.sync(env=env)
        self.assertEqual((installed / 'SKILL.md').read_text(), 'Original vendor skill\n')
        self.git(self.seed, 'submodule', 'update', '--remote', '--checkout')
        self.commit(self.seed, 'approve vendor update')
        self.git(self.seed, 'push', 'origin', 'main')
        self.sync(env=env)
        self.assertIn('New upstream revision', (installed / 'SKILL.md').read_text())

        self.git(self.seed, 'pull', '--ff-only')
        source.unlink()
        self.commit(self.seed, 'deselect the vendor skill')
        self.git(self.seed, 'push', 'origin', 'main')
        self.sync(env=env)
        self.assertFalse(installed.is_symlink())
        self.assertEqual(personal.read_text(), 'Personal skill\n')

    def test_sync_reinstalls_the_codex_plugin_once_per_downloaded_commit(self):
        log = self.base / 'codex.log'
        stub = self.stubs / 'codex'
        stub.write_text(f'#!/bin/bash\nprintf "%s\\n" "$*" >> "{log}"\n')
        stub.chmod(0o755)
        claude_log = self.base / 'claude.log'
        # Keep a locally installed Claude Code out of the test.
        (self.stubs / 'claude').write_text(f'#!/bin/bash\nprintf "%s\\n" "$*" >> "{claude_log}"\n')
        (self.stubs / 'claude').chmod(0o755)
        (self.vendor / '.claude-plugin').mkdir()
        (self.vendor / '.claude-plugin/plugin.json').write_text('{}\n')
        self.commit(self.vendor, 'plugin manifest')
        self.git(self.vendor, 'push', 'origin', 'main')
        self.git(self.seed, 'submodule', 'add', '-b', 'main', str(self.base / 'vendor.git'), '.upstream/ponytail')
        self.commit(self.seed, 'add ponytail')
        self.git(self.seed, 'push', 'origin', 'main')
        expected = f'plugin marketplace add {self.repo}/adapters/codex\nplugin add ponytail@agents\n'
        self.sync()
        self.assertEqual(log.read_text(), expected)
        self.assertIn('plugin install php-lsp@claude-plugins-official\n', claude_log.read_text())
        self.assertIn('plugin install typescript-lsp@claude-plugins-official\n', claude_log.read_text())
        self.sync()
        self.assertEqual(log.read_text(), expected)
        self.advance(self.seed, 'AGENTS.md')
        self.sync()
        self.assertEqual(log.read_text(), expected * 2)

    def test_unapproved_upstream_updates_are_not_installed_or_published(self):
        recorded = self.git(self.repo / '.upstream/cursor-plugins', 'rev-parse', 'HEAD')
        before = self.git(self.repo, 'rev-parse', 'HEAD')
        self.advance(self.vendor, 'SKILL.md')
        self.sync()
        self.assertEqual(recorded, self.git(self.repo / '.upstream/cursor-plugins', 'rev-parse', 'HEAD'))
        self.assertEqual(before, self.git(self.base / 'skills.git', 'rev-parse', 'main'))

    def test_installer_keeps_approved_submodule_versions_and_retires_autocommit(self):
        recorded = self.git(self.repo / '.upstream/cursor-plugins', 'rev-parse', 'HEAD')
        self.advance(self.vendor, "SKILL.md")
        self.git(self.repo, 'config', 'branch.main.autocommitscript', 'exit 99')
        self.install(self.repo)
        self.assertEqual(recorded, self.git(self.repo / '.upstream/cursor-plugins', 'rev-parse', 'HEAD'))
        result = self.run_cmd(self.repo, GIT, 'config', '--get', 'branch.main.autocommitscript', success=False)
        self.assertEqual(result.returncode, 1)

    def test_installer_preserves_a_locally_selected_submodule_revision(self):
        latest = self.advance(self.vendor, 'SKILL.md')
        submodule = self.repo / '.upstream/cursor-plugins'
        self.git(submodule, 'fetch', 'origin', 'main')
        self.git(submodule, 'checkout', latest)
        result = self.run_cmd(self.repo, 'bash', 'install.sh', success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(latest, self.git(submodule, 'rev-parse', 'HEAD'))

    def test_three_machines_download_the_same_approved_revision(self):
        others = [self.clone("computer-b"), self.clone("server")]
        for repo in others:
            self.install(repo)
        self.advance(self.vendor, "SKILL.md")
        self.git(self.seed, 'submodule', 'update', '--remote', '--checkout')
        (self.seed / 'skills/skill.md').write_text('Approved shared update\n')
        self.commit(self.seed, 'approve shared update')
        self.git(self.seed, 'push', 'origin', 'main')
        expected = self.git(self.seed, 'rev-parse', 'HEAD')
        for repo in [self.repo, *others]:
            self.sync(repo)
            self.assertEqual(expected, self.git(repo, 'rev-parse', 'HEAD'))
            self.assertEqual(self.git(repo, "status", "--porcelain"), "")

    def test_uncommitted_submodule_changes_are_preserved(self):
        skill = self.repo / ".upstream/cursor-plugins/SKILL.md"
        skill.write_text("Unfinished local edit\n")
        before = self.git(self.repo, "rev-parse", "HEAD")
        result = self.sync(success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(skill.read_text(), "Unfinished local edit\n")
        self.assertEqual(before, self.git(self.repo, "rev-parse", "HEAD"))

    def test_other_branches_and_overlapping_runs_do_not_commit(self):
        before = self.git(self.repo, "rev-parse", "HEAD")
        (self.repo / "skills/new.md").write_text("Still editing\n")
        self.git(self.repo, "switch", "-c", "topic")
        self.sync()
        self.git(self.repo, "switch", "main")
        with (self.repo / ".git/agents-sync/lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.sync()
        self.assertEqual(before, self.git(self.repo, "rev-parse", "HEAD"))

    def test_failed_submodule_checkout_does_not_revert_remote_pointer(self):
        latest = self.advance(self.vendor, "SKILL.md")
        self.git(self.seed, "submodule", "update", "--remote", "--checkout", "--", ".upstream/cursor-plugins")
        self.commit(self.seed, "update vendor pointer")
        self.git(self.seed, "push", "origin", "main")
        expected = self.git(self.seed, "rev-parse", "HEAD")
        shim = self.stubs / "git"
        shim.write_text(
            '#!/bin/bash\n'
            'if [[ "$*" == "submodule update --init --recursive --checkout" ]]; then exit 42; fi\n'
            'exec ' + GIT + ' "$@"\n'
        )
        shim.chmod(0o755)
        result = self.sync(success=False)
        self.assertEqual(result.returncode, 42, result.stdout)
        self.assertTrue((self.repo / ".git/agents-sync/submodules-pending").exists())
        shim.unlink()
        self.sync()
        self.assertEqual(expected, self.git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(latest, self.git(self.repo / ".upstream/cursor-plugins", "rev-parse", "HEAD"))
        self.assertEqual(expected, self.git(self.base / "skills.git", "rev-parse", "main"))

    def test_local_commits_are_never_pushed_or_rebased(self):
        remote_before = self.git(self.base / 'skills.git', 'rev-parse', 'main')
        (self.repo / 'skills/skill.md').write_text('Local version\n')
        self.commit(self.repo, 'local commit')
        local_before = self.git(self.repo, 'rev-parse', 'HEAD')
        self.assertNotEqual(self.sync(success=False).returncode, 0)
        self.assertEqual(local_before, self.git(self.repo, 'rev-parse', 'HEAD'))
        self.assertEqual(remote_before, self.git(self.base / 'skills.git', 'rev-parse', 'main'))
        self.assertFalse((self.repo / '.git/rebase-merge').exists())

    def test_local_files_are_ignored_and_forced_tracking_is_rejected(self):
        local = self.repo / 'local.json'
        local.write_text('Machine-specific settings')
        self.sync()
        self.assertEqual(self.git(self.repo, 'ls-files', '--', 'local.json'), '')
        self.git(self.repo, 'add', '-f', 'local.json')
        result = self.sync(success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(local.read_text(), 'Machine-specific settings')

    def test_ci_configuration_is_trackable_and_passes_the_repository_guard(self):
        workflow = self.repo / '.github/workflows/ci.yml'
        workflow.parent.mkdir(parents=True)
        workflow.write_text('name: CI\n')
        self.git(self.repo, 'add', '.github/workflows/ci.yml')
        self.run_cmd(self.repo, 'python3', 'scripts/agents.py', 'guard', '--staged')

    def test_guard_rejects_a_secret_in_shared_source(self):
        (self.repo / 'skills/leaked.txt').write_text('ghp_' + 'a' * 36)
        result = self.run_cmd(self.repo, 'python3', 'scripts/agents.py', 'guard', success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Possible secret in skills/leaked.txt', result.stdout)

    def test_guard_rejects_a_secret_deleted_in_unpublished_history(self):
        path = self.repo / 'skills/leaked.txt'
        path.write_text('ghp_' + 'b' * 36)
        self.commit(self.repo, 'accidental secret')
        path.unlink()
        self.commit(self.repo, 'remove secret')
        result = self.run_cmd(self.repo, 'python3', 'scripts/agents.py', 'guard', success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Possible secret in skills/leaked.txt', result.stdout)

    def test_invalid_registry_does_not_commit_or_apply(self):
        before = self.git(self.repo, 'rev-parse', 'HEAD')
        (self.repo / 'mcp/servers.json').write_text('{"version": 1, "servers": {"bad": {"transport": "unknown"}}}')
        self.assertNotEqual(self.sync(success=False).returncode, 0)
        self.assertEqual(before, self.git(self.repo, 'rev-parse', 'HEAD'))

    def test_two_machines_apply_pulled_mcp_configuration(self):
        other = self.clone('second-machine')
        environments = []
        for number, repo in enumerate((self.repo, other)):
            home = self.base / ('home-' + str(number))
            home.mkdir()
            config = home / '.config/agents'
            config.mkdir(parents=True)
            (config / 'local.json').write_text('{"harnesses": ["codex", "opencode"]}')
            env = dict(self.env, HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'),
                       XDG_STATE_HOME=str(home / '.local/state'))
            env.pop('CODEX_HOME', None)
            self.run_cmd(repo, 'bash', 'install.sh', env=env)
            environments.append(env)
        registry = self.seed / 'mcp/servers.json'
        data = json.loads(registry.read_text())
        data['servers']['shared'] = {'transport': 'http', 'url': 'https://example.com/shared'}
        registry.write_text(json.dumps(data))
        self.commit(self.seed, 'approve shared MCP')
        self.git(self.seed, 'push', 'origin', 'main')
        for repo, env in zip((self.repo, other), environments):
            self.sync(repo, env=env)
            path = Path(env['HOME']) / '.codex/config.toml'
            self.assertEqual(tomllib.loads(path.read_text())['mcp_servers']['shared']['url'],
                             'https://example.com/shared')
            opencode = Path(env['XDG_CONFIG_HOME']) / 'opencode/opencode.json'
            self.assertEqual(json.loads(opencode.read_text())['mcp']['servers']['shared']['url'],
                             'https://example.com/shared')

    def test_invalid_pulled_registry_keeps_previous_mcp_configuration(self):
        local = self.base / 'config/agents/local.json'
        local.write_text('{"harnesses": ["codex"]}')
        env = dict(self.env)
        env.pop('CODEX_HOME', None)
        self.run_cmd(self.repo, 'bash', 'install.sh', env=env)
        config = self.home / '.codex/config.toml'
        before = config.read_bytes()
        (self.seed / 'mcp/servers.json').write_text('{"version": 100}')
        self.commit(self.seed, 'invalid remote configuration')
        self.git(self.seed, 'push', 'origin', 'main')
        self.assertNotEqual(self.sync(env=env, success=False).returncode, 0)
        self.assertEqual(config.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
