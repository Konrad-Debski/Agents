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
        self.upstream = self.new_remote("git-sync", "master")
        (self.upstream / "git-sync").write_bytes(
            (ROOT / ".upstream/git-sync/git-sync").read_bytes()
        )
        self.commit(self.upstream, "git-sync source")
        self.git(self.upstream, "push", "-u", "origin", "master")
        self.vendor = self.new_remote("vendor", "main")
        (self.vendor / "SKILL.md").write_text("Original vendor skill\n")
        self.commit(self.vendor, "vendor source")
        self.git(self.vendor, "push", "-u", "origin", "main")

        self.seed = self.new_remote("skills", "main")
        shutil.copytree(ROOT / "scripts", self.seed / "scripts")
        for directory in ("adapters", "mcp"):
            shutil.copytree(ROOT / directory, self.seed / directory)
        shutil.copy(ROOT / ".gitignore", self.seed)
        shutil.copy(ROOT / "AGENTS.md", self.seed)
        (self.seed / "skills").mkdir()
        (self.seed / "skills/skill.md").write_text("Original skill\n")
        (self.seed / "skills/remove.md").write_text("Remove later\n")
        for name, branch, remote in (
            ("git-sync", "master", "git-sync.git"),
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
        return self.run_cmd(repo, "bash", "scripts/install-sync.sh")

    def sync(self, repo=None, success=True, env=None):
        return self.run_cmd(repo or self.repo, "bash", "scripts/sync.sh",
                            success=success, env=env)

    def advance(self, repo, filename):
        with (repo / filename).open("a") as handle:
            handle.write("\n# New upstream revision\n")
        self.commit(repo, "upstream update")
        branch = self.git(repo, "branch", "--show-current")
        self.git(repo, "push", "origin", branch)
        return self.git(repo, "rev-parse", "HEAD")

    def test_installer_is_repeatable_and_units_are_valid(self):
        self.git(self.repo, "submodule", "deinit", "--all")
        self.assertFalse((self.repo / ".upstream/git-sync/git-sync").exists())
        self.install(self.repo)
        self.assertTrue((self.repo / ".upstream/git-sync/git-sync").exists())
        self.install(self.repo)
        units = self.base / "config/systemd/user"
        self.assertIn("enable --now agents-sync.timer",
                      (self.base / "systemd.log").read_text())
        self.assertEqual(self.git(self.repo, "config", "branch.main.syncNewFiles"), "true")
        self.assertEqual(self.git(self.repo, "status", "--porcelain"), "")
        if shutil.which("systemd-analyze"):
            self.run_cmd(self.base, "systemd-analyze", "--user", "verify",
                         str(units / "agents-sync.service"),
                         str(units / "agents-sync.timer"))

    def test_local_changes_make_one_commit_and_no_empty_commits(self):
        before = self.git(self.repo, "rev-parse", "HEAD")
        (self.repo / "skills/skill.md").write_text("Edited skill\n")
        (self.repo / "skills/new.md").write_text("New skill\n")
        (self.repo / "skills/remove.md").unlink()
        self.sync()
        self.assertEqual(self.git(self.repo, "rev-list", "--count", before + "..HEAD"), "1")
        self.assertEqual(self.git(self.repo, "rev-parse", "HEAD"),
                         self.git(self.base / "skills.git", "rev-parse", "main"))
        after = self.git(self.repo, "rev-parse", "HEAD")
        self.sync()
        self.assertEqual(after, self.git(self.repo, "rev-parse", "HEAD"))

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
        self.git(self.seed, 'submodule', 'update', '--remote', '--checkout', '--',
                 '.upstream/cursor-plugins')
        self.commit(self.seed, 'update the pinned vendor skill')
        self.git(self.seed, 'push', 'origin', 'main')
        self.sync(env=env)
        self.assertIn('New upstream revision', (installed / 'SKILL.md').read_text())

        source.unlink()
        self.commit(self.seed, 'deselect the vendor skill')
        self.git(self.seed, 'push', 'origin', 'main')
        self.sync(env=env)
        self.assertFalse(installed.is_symlink())
        self.assertEqual(personal.read_text(), 'Personal skill\n')

    def test_self_update_is_published_and_vendor_stays_pinned(self):
        vendor_before = self.git(self.repo / ".upstream/cursor-plugins", "rev-parse", "HEAD")
        self.advance(self.vendor, "SKILL.md")
        latest = self.advance(self.upstream, "git-sync")
        self.sync()
        self.assertEqual(latest, self.git(self.repo / ".upstream/git-sync", "rev-parse", "HEAD"))
        self.assertIn(latest, self.git(self.base / "skills.git", "ls-tree", "main", ".upstream/git-sync"))
        self.assertEqual(vendor_before, self.git(self.repo / ".upstream/cursor-plugins", "rev-parse", "HEAD"))
        after = self.git(self.repo, "rev-parse", "HEAD")
        self.sync()
        self.assertEqual(after, self.git(self.repo, "rev-parse", "HEAD"))

    def test_three_machines_converge_including_git_sync_update(self):
        others = [self.clone("computer-b"), self.clone("server")]
        for repo in others:
            self.install(repo)
        self.advance(self.upstream, "git-sync")
        (self.repo / "skills/skill.md").write_text("Shared update\n")
        self.sync()
        for repo in others:
            self.sync(repo, success=False)
            # An identical submodule update can be dropped during rebase by
            # upstream git-sync. Its next run must converge without a conflict.
            self.sync(repo)
            self.assertEqual(self.git(self.repo, "rev-parse", "HEAD"),
                             self.git(repo, "rev-parse", "HEAD"))
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
            'if [[ "$*" == "submodule update --init --recursive" ]]; then exit 42; fi\n'
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

    def test_conflict_stops_without_overwriting_remote(self):
        other = self.clone("other")
        self.install(other)
        (self.repo / "skills/skill.md").write_text("Version A\n")
        (other / "skills/skill.md").write_text("Version B\n")
        self.sync()
        remote_before = self.git(self.base / "skills.git", "rev-parse", "main")
        self.assertNotEqual(self.sync(other, success=False).returncode, 0)
        self.assertNotEqual(self.sync(other, success=False).returncode, 0)
        self.assertEqual(remote_before, self.git(self.base / "skills.git", "rev-parse", "main"))
        self.assertTrue((other / ".git/rebase-merge").exists())

    def test_local_files_are_ignored_and_forced_tracking_is_rejected(self):
        local = self.repo / 'local.json'
        local.write_text('Machine-specific settings')
        self.sync()
        self.assertEqual(self.git(self.repo, 'ls-files', '--', 'local.json'), '')
        self.git(self.repo, 'add', '-f', 'local.json')
        result = self.sync(success=False)
        self.assertIn('Poza zakresem synchronizacji', result.stdout)

    def test_secret_in_shared_source_is_not_committed(self):
        before = self.git(self.repo, 'rev-parse', 'HEAD')
        (self.repo / 'skills/leaked.txt').write_text('ghp_' + 'a' * 36)
        self.assertNotEqual(self.sync(success=False).returncode, 0)
        self.assertEqual(before, self.git(self.repo, 'rev-parse', 'HEAD'))

    def test_deleted_secret_in_unpushed_history_is_not_published(self):
        remote = self.git(self.base / 'skills.git', 'rev-parse', 'main')
        path = self.repo / 'skills/leaked.txt'
        path.write_text('ghp_' + 'b' * 36)
        self.commit(self.repo, 'accidental secret')
        path.unlink()
        self.commit(self.repo, 'remove secret')
        self.assertNotEqual(self.sync(success=False).returncode, 0)
        self.assertEqual(remote, self.git(self.base / 'skills.git', 'rev-parse', 'main'))

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
            self.run_cmd(repo, 'bash', 'scripts/install-sync.sh', env=env)
            environments.append(env)
        registry = self.repo / 'mcp/servers.json'
        data = json.loads(registry.read_text())
        data['servers']['shared'] = {'transport': 'http', 'url': 'https://example.com/shared'}
        registry.write_text(json.dumps(data))
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
        self.run_cmd(self.repo, 'bash', 'scripts/install-sync.sh', env=env)
        config = self.home / '.codex/config.toml'
        before = config.read_bytes()
        (self.seed / 'mcp/servers.json').write_text('{"version": 100}')
        self.commit(self.seed, 'invalid remote configuration')
        self.git(self.seed, 'push', 'origin', 'main')
        self.assertNotEqual(self.sync(env=env, success=False).returncode, 0)
        self.assertEqual(config.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
