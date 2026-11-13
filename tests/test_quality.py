"""Exercise quality commands in disposable repositories."""
import json
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

    @unittest.skipUnless((ROOT / 'node_modules/.bin/commitlint').exists(), 'Run npm ci to test commitlint')
    def test_commits_command_rejects_only_nonconventional_subjects(self):
        for name in ('package.json', 'commitlint.config.mjs'):
            shutil.copy(ROOT / name, self.repo)
        (self.repo / 'node_modules').symlink_to(ROOT / 'node_modules')
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
        self.assertIn('Forgot the commit type', result.stdout + result.stderr)

    @unittest.skipUnless((ROOT / 'node_modules/.bin/commitlint').exists(), 'Run npm ci to test commitlint')
    def test_pr_policy_checks_title_branch_and_description(self):
        body = ('## Summary\nKeep private comments.\n## Evidence\n**Before:** The comment was deleted.\n'
                '**After:** The test keeps it.\n## Merge Danger\n**Door:** two-way\n**Blast Radius:** configuration\n')

        def run(title='fix: Preserve Private Comments', branch='fix/private-comments', body=body, base='main'):
            event = self.repo / 'event.json'
            event.write_text(json.dumps({'pull_request': {'title': title, 'body': body, 'head': {'ref': branch}, 'base': {'ref': base}}}))
            return subprocess.run(['python3', str(ROOT / 'scripts/quality/pr_policy.py'), str(event)],
                                  cwd=self.repo, env=self.env, capture_output=True, text=True, timeout=30)

        for arguments in ({}, {'title': '[ALTER-65] fix: Preserve Private Comments', 'branch': 'fix/ALTER-65-private-comments'},
                          {'title': 'fix: Keep $(touch injected) literal'}):
            result = run(**arguments)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.repo / 'injected').exists())
        for arguments, message in (
                ({'title': 'Preserve Private Comments'}, 'commitlint'),
                ({'title': 'feat: Preserve Private Comments'}, 'branch'),
                ({'branch': 'fix/Private_Comments'}, 'branch'),
                ({'base': 'develop'}, 'base'),
                ({'body': ''}, 'Summary'),
                ({'body': body.replace('**Before:** The comment was deleted.', '**Before:** <!-- explain -->')}, 'Before'),
                ({'body': body.replace('**Door:** two-way', '**Door:** <!-- choose one -->')}, 'Door')):
            with self.subTest(arguments=arguments):
                result = run(**arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
