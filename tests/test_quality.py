"""Exercise quality commands in disposable repositories and environments."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agents-quality-')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        shutil.copytree(ROOT / 'scripts', self.repo / 'scripts')
        (self.repo / 'tests').mkdir()

    def check(self, command):
        return subprocess.run(['bash', 'scripts/check.sh', command], cwd=self.repo,
                              env=os.environ, capture_output=True, text=True, timeout=30)

    def test_test_command_rejects_a_failing_test(self):
        (self.repo / 'tests/test_probe.py').write_text(
            'import unittest\nclass Probe(unittest.TestCase):\n'
            ' def test_failure(self): self.fail("quality probe failed")\n')
        result = self.check('tests')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('quality probe failed', result.stdout + result.stderr)

    def test_test_command_allows_optional_client_tests_to_skip(self):
        (self.repo / 'tests/test_opencode_cli.py').write_text(
            'import unittest\nclass Probe(unittest.TestCase):\n'
            ' @unittest.skip("OpenCode is not installed")\n'
            ' def test_contract(self): pass\n')
        (self.repo / 'tests/test_probe.py').write_text(
            'import unittest\nclass Probe(unittest.TestCase):\n'
            ' def test_required_behavior(self): pass\n')
        result = self.check('tests')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('skipped=1', result.stdout + result.stderr)

    def test_static_command_rejects_invalid_bash(self):
        (self.repo / 'install.sh').write_text('#!/usr/bin/env bash\nexit 0\n')
        (self.repo / 'scripts/broken.sh').write_text('if true; then\n')
        result = self.check('static')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('broken.sh', result.stdout + result.stderr)

    def test_tool_installation_requires_go_before_downloading(self):
        binaries = self.repo / 'tool-bin'
        binaries.mkdir()
        for name in ('dirname', 'uname', 'mktemp', 'rm'):
            (binaries / name).symlink_to(shutil.which(name))
        probe = self.repo / 'downloaded'
        curl = binaries / 'curl'
        curl.write_text('#!/bin/sh\nprintf download > "$DOWNLOAD_PROBE"\nexit 77\n')
        curl.chmod(0o755)
        result = subprocess.run([shutil.which('bash'), 'scripts/quality/install-tools.sh',
                                 str(self.repo / 'installed')], cwd=self.repo,
                                env=dict(os.environ, PATH=str(binaries), DOWNLOAD_PROBE=str(probe)),
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Go is required', result.stderr)
        self.assertFalse(probe.exists())

    def test_tool_installation_does_not_download_or_install_opencode(self):
        binaries = self.repo / 'tool-bin'
        binaries.mkdir()
        for name in ('bash', 'dirname', 'uname', 'mktemp', 'rm', 'mkdir'):
            (binaries / name).symlink_to(shutil.which(name))
        curl = binaries / 'curl'
        curl.write_text('''#!/bin/sh
if [ "$3" != https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash ]; then
    printf 'Unexpected tool download: %s\\n' "$3" >&2
    exit 1
fi
printf '%s\\n' '#!/bin/sh' ': > "$2/actionlint"' > "$2"
''')
        curl.chmod(0o755)
        go = binaries / 'go'
        go.write_text('#!/bin/sh\n: > "$GOBIN/gitleaks"\n')
        go.chmod(0o755)
        destination = self.repo / 'installed'
        result = subprocess.run([shutil.which('bash'), 'scripts/quality/install-tools.sh', str(destination)],
                                cwd=self.repo, env=dict(os.environ, PATH=str(binaries)),
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sorted(path.name for path in destination.iterdir()), ['actionlint', 'gitleaks'])

    def test_repository_command_rejects_a_missing_registered_skill(self):
        shutil.copy(ROOT / '.gitignore', self.repo)
        (self.repo / 'mcp').mkdir()
        (self.repo / 'mcp/servers.json').write_text('{"version":1,"servers":{}}')
        (self.repo / 'skills').mkdir()
        (self.repo / 'package.json').write_text('{"skills":["./skills/missing"]}')
        env = dict(os.environ, GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
        for args in [('init', '--initial-branch=main'), ('add', '-A'),
                     ('-c', 'user.name=Quality test', '-c', 'user.email=quality@example.invalid',
                      '-c', 'commit.gpgsign=false', 'commit', '-m', 'test: seed repository'),
                     ('update-ref', 'refs/remotes/origin/main', 'HEAD')]:
            subprocess.run(['git', *args], cwd=self.repo, env=env, check=True, capture_output=True)
        result = self.check('repository')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing', result.stdout + result.stderr)

    def test_secret_command_checks_history_even_after_the_secret_was_deleted(self):
        env = dict(os.environ, GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
        def git(*args):
            return subprocess.run(['git', *args], cwd=self.repo, env=env, check=True,
                                  capture_output=True, text=True).stdout.strip()
        git('init', '--initial-branch=main')
        git('config', 'user.name', 'Quality test')
        git('config', 'user.email', 'quality@example.invalid')
        git('config', 'commit.gpgsign', 'false')
        git('commit', '--allow-empty', '-m', 'test: seed')
        git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        path = self.repo / 'leak.txt'
        path.write_text('token = "ghp_' + 'a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8' + '"\n')
        git('add', 'leak.txt')
        git('commit', '-m', 'test: introduce example token')
        path.unlink()
        git('add', 'leak.txt')
        git('commit', '-m', 'test: remove example token')
        result = self.check('secrets')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('leaks found', result.stdout + result.stderr)
        self.assertNotIn('a1B2c3D4e5F6g7H8', result.stdout + result.stderr)
