"""Exercise the tstack update plan in disposable Git repositories."""

import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'quality'))
import tstack_update


class TstackUpdateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='agents-tstack-test-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.repo, self.upstream = root / 'local', root / 'upstream'
        for repo in (self.repo, self.upstream):
            repo.mkdir()
            self.git(repo, 'init', '--initial-branch=main')
            self.git(repo, 'config', 'user.name', 'Tstack test')
            self.git(repo, 'config', 'user.email', 'tstack@example.invalid')
            self.git(repo, 'config', 'commit.gpgsign', 'false')
        self.path = 'skills/council/SKILL.md'
        self.original = 'provider: upstream\n\n# Details\n\nOld instructions.\n'
        self.old = self.commit(self.upstream, self.path, self.original)
        self.commit(self.repo, self.path, self.original.replace('provider: upstream', 'provider: local'))
        self.pin(self.old)
        self.git(self.repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.git(self.repo, 'switch', '-c', 'update')

    def git(self, repo, *args):
        return subprocess.run(['git', *args], cwd=repo, text=True, check=True,
                              capture_output=True).stdout.strip()

    def commit(self, repo, path, text):
        file = repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)
        self.git(repo, 'add', '--', path)
        self.git(repo, 'commit', '-m', 'test: Prepare fixture')
        return self.git(repo, 'rev-parse', 'HEAD')

    def pin(self, sha):
        self.git(self.repo, 'update-index', '--add', '--cacheinfo', f'160000,{sha},.upstream/tstack')
        self.git(self.repo, 'commit', '-m', 'test: Pin tstack')
        return self.git(self.repo, 'rev-parse', 'HEAD')

    def prepare(self, new, extra_change=False, stale=False):
        head = self.pin(new)
        if extra_change:
            head = self.commit(self.repo, 'other.txt', 'Unrelated content')
        self.git(self.repo, 'update-ref', 'refs/remotes/origin/tstack-update', head)
        pr = {
            'state': 'open', 'draft': False, 'user': {'login': 'dependabot[bot]'},
            'base': {'ref': 'main'},
            'head': {'sha': head, 'ref': f'dependabot/submodules/dot-upstream/tstack-{new[:7]}',
                     'repo': {'full_name': 'example/agents'}},
            'changed_files': 1,
        }
        original_git, original_run = tstack_update.git, tstack_update.run

        def git(repo, *args):
            if args[0] == 'fetch':
                return b''
            return original_git(self.repo if repo == '.' else repo, *args)

        def run(*args, **kwargs):
            if args[0] == 'gh':
                return json.dumps(pr).encode()
            return original_run(*args, **kwargs)

        with patch.dict('os.environ', {'GITHUB_REPOSITORY': 'example/agents'}), \
                patch.object(tstack_update, 'UPSTREAM', str(self.upstream)), \
                patch.object(tstack_update, 'git', side_effect=git), \
                patch.object(tstack_update, 'run', side_effect=run):
            return tstack_update.prepare(1, self.old if stale else head)

    def test_merges_non_overlapping_edits_and_keeps_the_update_for_review(self):
        new = self.commit(self.upstream, self.path, self.original.replace('Old instructions', 'New instructions'))
        plan = self.prepare(new)
        self.assertFalse(plan['conflicts'])
        self.assertTrue(plan['selected_changed'])
        self.assertEqual(plan['additions'][0]['path'], self.path)
        merged = base64.b64decode(plan['additions'][0]['contents']).decode()
        self.assertEqual(merged, 'provider: local\n\n# Details\n\nNew instructions.\n')

        head = self.git(self.repo, 'rev-parse', 'HEAD')
        with patch.dict('os.environ', {'GITHUB_REPOSITORY': 'example/agents'}), \
                patch.object(tstack_update, 'run', return_value=b'{}') as run:
            tstack_update.publish(plan, 1, head)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args, ('gh', 'api', 'graphql', '--input', '-'))
        commit = json.loads(run.call_args.kwargs['data'])['variables']['input']
        self.assertEqual(commit['expectedHeadOid'], head)
        self.assertEqual(commit['branch']['branchName'], plan['branch'])
        self.assertEqual(commit['fileChanges']['additions'], plan['additions'])

    def test_reports_overlapping_edits_without_a_candidate(self):
        new = self.commit(self.upstream, self.path, self.original.replace('provider: upstream', 'provider: other'))
        plan = self.prepare(new)
        self.assertEqual(plan['additions'], [])
        self.assertIn('<<<<<<< local', plan['conflicts'][0])
        self.assertIn('provider: other', plan['conflicts'][0])
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            tstack_update.publish(plan, 1, self.git(self.repo, 'rev-parse', 'HEAD'))

    def test_reports_local_copy_changed_on_main_after_the_pr_branched(self):
        self.git(self.repo, 'switch', 'main')
        self.commit(self.repo, self.path, 'Updated local instructions')
        self.git(self.repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.git(self.repo, 'switch', 'update')
        new = self.commit(self.upstream, self.path, self.original.replace('Old instructions', 'New instructions'))
        plan = self.prepare(new)
        self.assertEqual(plan['additions'], [])
        self.assertEqual(plan['conflicts'], [f'{self.path}: local copy changed on main after the PR branched'])

    def test_linked_skills_require_review(self):
        new = self.commit(self.upstream, 'skills/babysit-pr/SKILL.md', 'Changed instructions')
        plan = self.prepare(new)
        self.assertTrue(plan['selected_changed'])
        self.assertEqual(plan['additions'], [])

    def test_unselected_skill_change_can_enable_auto_merge_for_the_reviewed_head(self):
        new = self.commit(self.upstream, 'skills/file-pr/SKILL.md', 'Changed instructions')
        plan = self.prepare(new)
        self.assertFalse(plan['selected_changed'])
        head = self.git(self.repo, 'rev-parse', 'HEAD')
        with patch.dict('os.environ', {'GITHUB_REPOSITORY': 'example/agents'}), \
                patch.object(tstack_update, 'run') as run:
            tstack_update.publish(plan, 1, head)
        run.assert_called_once_with('gh', 'pr', 'merge', '1', '--repo', 'example/agents',
                                    '--auto', '--merge', '--match-head-commit', head)

    def test_rejects_a_stale_head(self):
        new = self.commit(self.upstream, 'README.md', 'Updated readme')
        self.assertIsNone(self.prepare(new, stale=True))

    def test_checks_the_git_diff_even_when_the_api_reports_one_changed_file(self):
        new = self.commit(self.upstream, 'README.md', 'Updated readme')
        self.assertIsNone(self.prepare(new, extra_change=True))
