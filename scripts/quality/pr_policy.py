"""Check a pull request event: title by commitlint, branch name and description sections."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[2]


def fail(message):
    sys.exit('PR policy failed: ' + message)


pr = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else os.environ['GITHUB_EVENT_PATH']).read_text())['pull_request']
# A ticket prefix such as [ALTER-65] is allowed before the conventional title.
title = re.sub(r'^\[[A-Z][A-Z0-9]*-[0-9]+\]\s+', '', pr['title'])
# commitlint.config.mjs holds the rules, the same ones that check.sh applies to commits.
lint = subprocess.run(['npx', '--no-install', 'commitlint'], cwd=root, input=title, capture_output=True, text=True)
if lint.returncode:
    fail('the title does not follow commitlint.config.mjs\n' + lint.stdout + lint.stderr)
kind = re.match(r'[a-z]+', title).group()
if not re.fullmatch(re.escape(kind) + r'/(?:[A-Z][A-Z0-9]*-[0-9]+-)?[a-z0-9]+(?:-[a-z0-9]+)*', pr['head']['ref']) or pr['base']['ref'] != 'main':
    fail(f'use a {kind}/kebab-case branch that matches the title type, and main as the base')
body = re.sub(r'<!--.*?-->', '', (pr.get('body') or '').replace('\r\n', '\n'), flags=re.S)
sections = {name.strip(): text.strip() for name, _, text in (block.partition('\n') for block in re.split(r'^##[ \t]+', body, flags=re.M)[1:])}
for name in ('Summary', 'Evidence', 'Merge Danger'):
    if not sections.get(name):
        fail(f'{name} must contain a description')
evidence = re.search(r'\*\*Before:\*\*(.*?)\*\*After:\*\*(.*)', sections['Evidence'], re.S)
if not evidence or not evidence[1].strip() or not evidence[2].strip():
    fail('Evidence requires nonempty Before and After descriptions')
danger = sections['Merge Danger']
if not re.search(r'^\*\*Door:\*\*[ \t]+(?:one-way|two-way)[ \t]*$', danger, re.M) \
        or not re.search(r'^\*\*Blast Radius:\*\*[ \t]+[A-Za-z][^\n]*$', danger, re.M):
    fail('Merge Danger requires Door: one-way/two-way and a Blast Radius')
print('PR policy passed')
