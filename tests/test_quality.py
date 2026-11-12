"""Exercise quality commands in disposable repositories."""
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
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
        self.git('init', '--initial-branch=main')
        for key, value in (('user.name', 'Quality test'), ('user.email', 'quality@example.invalid'),
                           ('commit.gpgsign', 'false')):
            self.git('config', key, value)

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def check(self, *args):
        return subprocess.run(['bash', 'scripts/check.sh', *args], cwd=self.repo,
                              env=self.env, capture_output=True, text=True, timeout=30)

    def test_repository_command_rejects_a_missing_registered_skill(self):
        shutil.copy(ROOT / '.gitignore', self.repo)
        (self.repo / 'mcp').mkdir()
        (self.repo / 'mcp/servers.json').write_text('{"version":1,"servers":{}}')
        (self.repo / 'skills').mkdir()
        (self.repo / 'package.json').write_text('{"skills":["./skills/missing"]}')
        self.git('add', '-A')
        self.git('commit', '-m', 'test: seed repository')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        result = self.check('repository')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing', result.stdout + result.stderr)

    def test_commits_command_rejects_only_nonconventional_subjects(self):
        self.git('commit', '--allow-empty', '-m', 'Legacy base message')
        base = self.git('rev-parse', 'HEAD')
        self.git('switch', '-c', 'side')
        self.git('commit', '--allow-empty', '-m', 'fix(sync)!: Keep local commits')
        self.git('switch', 'main')
        self.git('commit', '--allow-empty', '-m', 'docs: Describe checks')
        self.git('merge', '--no-ff', 'side', '-m', "Merge branch 'side'")
        result = self.check('commits', base, 'HEAD')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.git('commit', '--allow-empty', '-m', 'Forgot the commit type')
        result = self.check('commits', base, 'HEAD')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Forgot the commit type', result.stdout)
