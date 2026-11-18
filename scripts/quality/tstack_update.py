"""Prepare a Dependabot tstack update without checking out the PR or upstream."""

import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


SUBMODULE = '.upstream/tstack'
UPSTREAM = 'https://github.com/t3dotgg/tstack.git'
LOCAL = ('council', 'full-send', 'full-stop', 'takeover')
LINKED = ('babysit-pr', 'leaving-pr-comments', 'modernize', 'sol-loop')
SHA = re.compile(r'[0-9a-f]{40}')


def run(*args, cwd=None, data=None):
    return subprocess.run(args, cwd=cwd, input=data, stdout=subprocess.PIPE, check=True).stdout


def git(repo, *args):
    return run('git', *args, cwd=repo)


def tree(repo, ref, *paths):
    entries = {}
    for entry in git(repo, 'ls-tree', '-rz', ref, '--', *paths).split(b'\0')[:-1]:
        metadata, path = entry.split(b'\t', 1)
        entries[path.decode()] = metadata.decode().split()
    return entries


def merge_skills(repo, base, upstream, old, new, scratch):
    paths = tuple(f'skills/{name}' for name in LOCAL)
    before, after = (tree(upstream, ref, *paths) for ref in (old, new))
    local = tree(repo, base, *paths)
    current = tree(repo, 'origin/main', *paths)
    additions = []
    conflicts = []
    for path in sorted(before.keys() | after.keys()):
        if before.get(path) == after.get(path):
            continue
        if local.get(path) != current.get(path):
            conflicts.append(f'{path}: local copy changed on main after the PR branched')
            continue
        entries = (local.get(path), before.get(path), after.get(path))
        if any(entry is None or entry[:2] != ['100644', 'blob'] for entry in entries):
            conflicts.append(f'{path}: file added, removed, missing locally or changed mode')
            continue
        blobs = [git(source, 'cat-file', 'blob', entry[2]) for source, entry in
                 zip((repo, upstream, upstream), entries)]
        if any(b'\0' in blob for blob in blobs):
            conflicts.append(f'{path}: binary content')
            continue
        files = [scratch / label for label in ('local', 'old-upstream', 'new-upstream')]
        for file, blob in zip(files, blobs):
            file.write_bytes(blob)
        result = subprocess.run(['git', 'merge-file', '--diff3', '-p',
                                 '-L', 'local', '-L', 'old upstream', '-L', 'new upstream',
                                 *files], stdout=subprocess.PIPE)
        if result.returncode:
            conflicts.append(f'{path}:\n{result.stdout.decode(errors="replace")}')
        elif result.stdout != blobs[0]:
            additions.append({'path': path, 'contents': base64.b64encode(result.stdout).decode()})
    return additions, conflicts


def prepare(number, expected_head):
    repo = os.environ['GITHUB_REPOSITORY']
    pr = json.loads(run('gh', 'api', f'repos/{repo}/pulls/{number}'))
    head = pr['head']
    if (pr['state'] != 'open' or pr['draft'] or pr['user']['login'] != 'dependabot[bot]'
            or pr['base']['ref'] != 'main' or head['sha'] != expected_head
            or (head.get('repo') or {}).get('full_name') != repo
            or not re.fullmatch(r'dependabot/submodules/dot-upstream/tstack-[0-9a-f]+', head['ref'])
            or pr['changed_files'] != 1):
        return None

    git('.', 'fetch', '--no-tags', '--no-recurse-submodules', 'origin',
        '+refs/heads/main:refs/remotes/origin/main',
        f'+refs/pull/{number}/head:refs/remotes/origin/tstack-update')
    if git('.', 'rev-parse', 'refs/remotes/origin/tstack-update').decode().strip() != expected_head:
        return None
    base = git('.', 'merge-base', 'origin/main', expected_head).decode().strip()
    if git('.', 'diff', '--name-only', '-z', base, expected_head) != SUBMODULE.encode() + b'\0':
        return None

    old, new = (tree('.', ref, SUBMODULE).get(SUBMODULE, []) for ref in (base, expected_head))
    if any(entry[:2] != ['160000', 'commit'] for entry in (old, new)) or old == new:
        raise ValueError('Expected a change between two tstack gitlinks')
    if tree('.', 'origin/main', SUBMODULE).get(SUBMODULE) != old:
        raise ValueError('main has a different tstack pin. Wait for Dependabot to update the PR.')
    old, new = old[2], new[2]
    with tempfile.TemporaryDirectory(prefix='agents-tstack-') as directory:
        scratch = Path(directory)
        upstream = scratch / 'upstream'
        git('.', 'clone', '--bare', '--single-branch', '--branch', 'main', '--no-tags', UPSTREAM, upstream)
        git(upstream, 'merge-base', '--is-ancestor', old, new)
        git(upstream, 'merge-base', '--is-ancestor', new, 'refs/heads/main')
        additions, conflicts = merge_skills('.', base, upstream, old, new, scratch)
        paths = tuple(f'skills/{name}' for name in LOCAL + LINKED) + ('LICENSE', '.gitmodules', '.gitattributes')
        diff = git(upstream, 'diff', '--no-ext-diff', '--no-textconv', old, new, '--', *paths)
    return {
        'branch': head['ref'],
        'additions': additions,
        'conflicts': conflicts,
        'selected_changed': bool(diff),
        'context': {
            'old': old,
            'new': new,
            'upstream_diff': diff.decode(errors='replace'),
            'merged_files': {change['path']: base64.b64decode(change['contents']).decode(errors='replace')
                             for change in additions},
            'conflicts': conflicts,
        },
    }


def publish(plan, number, head):
    if plan['conflicts']:
        raise ValueError('The current update has conflicts. See the review run.')
    if plan['additions']:
        payload = {
            'query': 'mutation($input: CreateCommitOnBranchInput!) {'
                     ' createCommitOnBranch(input: $input) { commit { oid } } }',
            'variables': {'input': {
                'expectedHeadOid': head,
                'branch': {'repositoryNameWithOwner': os.environ['GITHUB_REPOSITORY'],
                           'branchName': plan['branch']},
                'message': {'headline': 'chore(deps): Reconcile tstack skill copies'},
                'fileChanges': {'additions': plan['additions']},
            }},
        }
        print(run('gh', 'api', 'graphql', '--input', '-', data=json.dumps(payload).encode()).decode().strip())
    if plan['selected_changed']:
        print('Installed tstack skills or upstream configuration changed. Maintainer review is required.')
    else:
        run('gh', 'pr', 'merge', str(number), '--repo', os.environ['GITHUB_REPOSITORY'],
            '--auto', '--merge', '--match-head-commit', head)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'publish'))
    parser.add_argument('number', type=int)
    parser.add_argument('head')
    args = parser.parse_args()
    if args.number <= 0 or not SHA.fullmatch(args.head):
        parser.error('expected a positive PR number and a full commit SHA')
    try:
        plan = prepare(args.number, args.head)
        if plan is None:
            if args.command == 'prepare':
                raise ValueError('The pull request is no longer an eligible tstack update')
            print('The pull request is no longer an eligible tstack update.')
        elif args.command == 'publish':
            publish(plan, args.number, args.head)
        else:
            context = json.dumps(plan['context'], ensure_ascii=False, indent=2)
            if len(context.encode()) > 128_000:
                raise ValueError('The tstack update is too large for automatic review')
            Path('tstack-review.json').write_text(context, encoding='utf-8')
            with open(os.environ['GITHUB_OUTPUT'], 'a') as file:
                print(f"conflicts={str(bool(plan['conflicts'])).lower()}", file=file)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
