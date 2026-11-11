"""Validate the published skill catalog without changing user configuration."""
import json
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[2]
registered = json.loads((root / 'package.json').read_text())['skills']
errors = []
if not isinstance(registered, list) or not all(isinstance(name, str) for name in registered):
    sys.exit('package.json: skills must be a list of paths')
if len(registered) != len(set(registered)):
    errors.append('package.json: duplicate skills')
for name in registered:
    if not re.fullmatch(r'\./skills/[a-z0-9-]+', name) or not (root / name / 'SKILL.md').is_file():
        errors.append(f'Missing or invalid registered skill: {name}')
for path in (root / 'skills').iterdir():
    if f'./skills/{path.name}' not in registered:
        errors.append(f'Unregistered skill: {path.name}')
if errors:
    sys.exit('\n'.join(errors))
print(f'Skill catalog passed: {len(registered)} skills')
