#!/usr/bin/env python3
"""Shared agent configuration. Python 3.11+, standard library only."""
import argparse
import contextlib
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
BEGIN = '# BEGIN agents managed MCP\n'
END = '# END agents managed MCP\n'
ALLOWED_FILES = {'AGENTS.md', 'README.md', '.gitignore', '.gitmodules', 'package.json'}
ALLOWED_DIRS = {'skills', 'mcp', 'adapters', 'scripts', 'docs', 'tests', '.upstream'}
SECRET_NAME = re.compile(r'(^|/)(\.env(?:\..*)?|credentials(?:\..*)?|auth\.json|id_rsa|id_ed25519|.*\.pem|.*\.key)$', re.I)
LOCAL_NAME = re.compile(r'(^|/)(?:\.cache|__pycache__)(?:/|$)|\.(?:log|tar|zip|gz|pyc|pyo)$', re.I)
SECRET_VALUE = re.compile(rb'-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----|\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{32,})\b')


class ConfigError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ConfigError(message)


def load_json(path, default=None):
    if not path.exists():
        require(default is not None, f'Brak pliku {path}')
        return copy.deepcopy(default)
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f'{path}: wymagany obiekt JSON')
    return value


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


def registry():
    data = load_json(ROOT / 'mcp/servers.json')
    require(data.get('version') == 1 and isinstance(data.get('servers'), dict), 'Nieobsługiwany rejestr MCP')
    for name, server in data['servers'].items():
        require(re.fullmatch(r'[A-Za-z0-9_-]+', name), f'Niepoprawna nazwa MCP: {name}')
        require(isinstance(server, dict), f'{name}: wymagana definicja serwera')
        transport = server.get('transport')
        fields = {'transport', 'harnesses', 'requires_env'}
        if transport == 'stdio':
            fields |= {'command', 'args', 'env_vars'}
            require(isinstance(server.get('command'), str) and server['command'], f'{name}: brak command')
            require(not server['command'].startswith(('/', '~')), f'{name}: command musi być przenośne')
        elif transport == 'http':
            fields |= {'url', 'header_env'}
            require(isinstance(server.get('url'), str), f'{name}: brak url')
            url = urlsplit(server['url'])
            require(url.scheme in {'https', 'http'} and url.hostname and not url.username
                    and not url.password and not url.query and not url.fragment,
                    f'{name}: URL bez danych logowania, parametrów i fragmentu')
            headers = server.get('header_env', {})
            require(isinstance(headers, dict) and all(isinstance(k, str) and isinstance(v, str)
                    and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', v) for k, v in headers.items()),
                    f'{name}: header_env musi wskazywać nazwy zmiennych')
        else:
            raise ConfigError(f'{name}: obsługiwane transporty to stdio i http')
        require(not (set(server) - fields), f'{name}: nieznane pola konfiguracji')
        for key in ('args', 'env_vars', 'requires_env', 'harnesses'):
            values = server.get(key, [])
            require(isinstance(values, list) and all(isinstance(v, str) for v in values), f'{name}: {key} musi być listą napisów')
            if key in {'env_vars', 'requires_env'}:
                require(all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', v) for v in values), f'{name}: niepoprawna nazwa zmiennej')
        if 'harnesses' in server:
            require(set(server['harnesses']) <= {'codex', 'claude-code', 'cursor'}, f'{name}: nieznany harness')
    return data['servers']


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def check_path(name, blob):
    first = name.split('/')[0]
    require(name in ALLOWED_FILES or first in ALLOWED_DIRS, f'Poza zakresem synchronizacji: {name}')
    require(not SECRET_NAME.search(name), f'Plik lokalny lub sekret poza synchronizacją: {name}')
    require(not LOCAL_NAME.search(name), f'Plik wygenerowany poza synchronizacją: {name}')
    require(not SECRET_VALUE.search(blob), f'Podejrzenie sekretu w {name}; usuń go przed synchronizacją')


def guard(staged=False):
    """Check tracked files too: .gitignore cannot protect an already tracked secret."""
    if staged:
        names = git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z').split(b'\0')
    else:
        names = git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0')
    for raw in set(names) - {b''}:
        name = os.fsdecode(raw)
        path = ROOT / name
        if staged:
            mode = git('ls-files', '-s', '--', name).split()[0]
            blob = b'' if mode == b'160000' else git('show', ':' + name)
        else:
            blob = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes() if path.is_file() else b''
        check_path(name, blob)
    # A manually committed secret must not be pushed just because it was later deleted.
    commits = git('rev-list', 'origin/main..HEAD').decode().splitlines()
    for commit in commits:
        for raw in git('diff-tree', '--root', '--no-commit-id', '--name-only', '-r', '--diff-filter=ACMR', '-z', commit).split(b'\0'):
            if raw:
                name = os.fsdecode(raw)
                mode = git('ls-tree', commit, '--', name).split()[0]
                check_path(name, b'' if mode == b'160000' else git('show', commit + ':' + name))


def convert(server, harness):
    if server['transport'] == 'stdio':
        result = {'command': server['command'], 'args': server.get('args', [])}
        names = server.get('env_vars', [])
        if harness == 'codex':
            if names:
                result['env_vars'] = names
        else:
            result['type'] = 'stdio'
            if names:
                result['env'] = {v: '${env:' + v + '}' if harness == 'cursor' else '${' + v + '}' for v in names}
    else:
        result = {'url': server['url']}
        headers = server.get('header_env', {})
        if harness == 'codex':
            if headers:
                result['env_http_headers'] = headers
        else:
            result['type'] = 'http'
            if headers:
                result['headers'] = {k: '${env:' + v + '}' if harness == 'cursor' else '${' + v + '}' for k, v in headers.items()}
    return result


def toml_block(servers):
    if not servers:
        return ''
    lines = [BEGIN.rstrip()]
    for name, server in servers.items():
        lines.append('[mcp_servers.' + json.dumps(name) + ']')
        for key, value in server.items():
            if isinstance(value, dict):
                text = '{ ' + ', '.join(json.dumps(k) + ' = ' + json.dumps(v) for k, v in value.items()) + ' }'
            else:
                text = json.dumps(value, ensure_ascii=False)
            lines.append(key + ' = ' + text)
    return '\n'.join(lines) + '\n' + END


def merge_mcp(path, fmt, old, desired):
    require(not path.is_symlink(), f'{path}: konfiguracja jest symlinkiem; scalenie wymaga zwykłego pliku')
    text = path.read_text() if path.exists() else ''
    if fmt == 'toml':
        tomllib.loads(text)
        require(text.count(BEGIN) == text.count(END) <= 1, f'{path}: uszkodzone znaczniki')
        managed = ''
        if BEGIN in text:
            start = text.index(BEGIN)
            stop = text.index(END) + len(END)
            require(stop > start, f'{path}: odwrócone znaczniki')
            managed = text[start:stop]
            text = text[:start] + text[stop:]
        require(tomllib.loads(managed).get('mcp_servers', {}) == old, f'{path}: ręcznie zmieniony blok zarządzany lub brak stanu')
        remaining = tomllib.loads(text).get('mcp_servers', {})
        require(not (set(remaining) & set(desired)), f'{path}: kolizja nazwy MCP')
        result = text.rstrip() + ('\n\n' if text.strip() and desired else '') + toml_block(desired)
        require(tomllib.loads(result).get('mcp_servers', {}) == {**remaining, **desired}, f'{path}: niepoprawny wynik TOML')
        return result.encode()
    data = json.loads(text) if text.strip() else {}
    require(isinstance(data, dict), f'{path}: wymagany obiekt JSON')
    current = data.get('mcpServers', {})
    require(isinstance(current, dict), f'{path}: mcpServers musi być obiektem')
    for name, value in old.items():
        require(current.get(name) == value, f'{path}: ręcznie zmieniony zarządzany serwer {name}')
        del current[name]
    require(not (set(current) & set(desired)), f'{path}: kolizja nazwy MCP')
    if current or desired or 'mcpServers' in data:
        data['mcpServers'] = {**current, **desired}
    return json_bytes(data)


def atomic_write(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.agents-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def snapshot(path):
    if path.is_symlink():
        return ('link', os.readlink(path), None)
    require(not path.exists() or path.is_file(), f'{path}: kolizja z katalogiem')
    return ('file', path.read_bytes(), path.stat().st_mode & 0o777) if path.exists() else ('missing', None, None)


def install_snapshot(path, value):
    kind, content, mode = value
    if kind == 'file':
        atomic_write(path, content, mode)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.unlink(missing_ok=True)
        if kind == 'link':
            path.symlink_to(content)


def locations():
    home = Path.home()
    config = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'agents'
    state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state')) / 'agents'
    return home, config, state


def prepare():
    home, config, state_dir = locations()
    local = load_json(config / 'local.json', {})
    require(not (set(local) - {'harnesses', 'disabled_servers'}), 'Nieznane pola local.json')
    adapters = {p.parent.name: load_json(p) for p in sorted((ROOT / 'adapters').glob('*/adapter.json'))}
    selected = local.get('harnesses', [name for name, adapter in adapters.items()
                       if (home / adapter['directory']).exists() or shutil.which(adapter['command'])])
    require(isinstance(selected, list) and all(name in adapters for name in selected), 'Nieznany harness w local.json')
    disabled = local.get('disabled_servers', [])
    require(isinstance(disabled, list) and all(isinstance(s, str) for s in disabled), 'disabled_servers musi być listą nazw')
    servers = registry()
    previous = load_json(state_dir / 'managed.json', {'version': 1, 'mcp': {}, 'links': {}})
    require(previous.get('version') == 1, 'Nieobsługiwany stan adapterów')
    following = {'version': 1, 'mcp': {}, 'links': {}}
    changes = {}
    notices = []

    def link(destination, source):
        path = Path(destination)
        value = str(source)
        before = snapshot(path)
        if before[0] == 'link':
            require(os.path.abspath(path.parent / before[1]) == value, f'{path}: obcy symlink; zachowaj i scal go ręcznie')
        elif before[0] == 'file':
            require(source.is_file() and before[1] == source.read_bytes(), f'{path}: istniejące instrukcje; scal je z AGENTS.md i zachowaj lokalną kopię przed usunięciem pliku')
        if before != ('link', value, None):
            changes[path] = (before, ('link', value, None))
        following['links'][str(path)] = value

    for name in sorted(set(selected)):
        adapter = adapters[name]
        if name == 'codex':
            base = Path(os.environ.get('CODEX_HOME', home / '.codex')).expanduser().absolute()
            config_path = base / 'config.toml'
            instruction = base / 'AGENTS.md'
        elif name == 'claude-code':
            base = Path(os.environ.get('CLAUDE_CONFIG_DIR', home / '.claude')).expanduser().absolute()
            config_path = base / '.claude.json' if os.environ.get('CLAUDE_CONFIG_DIR') else home / '.claude.json'
            instruction = base / 'CLAUDE.md'
        else:
            base = home / adapter['directory']
            config_path = home / adapter['mcp']
            instruction = None
        if instruction:
            link(instruction, ROOT / 'AGENTS.md')
        else:
            notices.append('Cursor: w Customize > Rules dodaj: Read and follow ~/.agents/AGENTS.md before every task.')
        if adapter['skills'] == 'native':
            # In the canonical checkout these are already ordinary repository files.
            if (home / '.agents/skills').resolve() != (ROOT / 'skills').resolve():
                link(home / '.agents/skills', ROOT / 'skills')
        else:
            for skill in sorted((ROOT / 'skills').iterdir()):
                if (skill / 'SKILL.md').is_file():
                    link(base / 'skills' / skill.name, skill)
        desired = {key: convert(server, name) for key, server in servers.items()
                   if key not in disabled and name in server.get('harnesses', selected)}
        key = str(config_path)
        old = previous['mcp'].get(key, {}).get('servers', {})
        content = merge_mcp(config_path, adapter['format'], old, desired)
        before = snapshot(config_path)
        if before[0] != 'missing' or desired:
            if before[1] != content:
                changes[config_path] = (before, ('file', content, 0o600))
        following['mcp'][key] = {'format': adapter['format'], 'servers': desired}

    # Remove only entries whose ownership and current contents still match.
    for key, entry in previous['mcp'].items():
        if key not in following['mcp']:
            path = Path(key)
            before = snapshot(path)
            content = merge_mcp(path, entry['format'], entry['servers'], {})
            if before[1] != content:
                changes[path] = (before, ('file', content, 0o600))
    for key, target in previous['links'].items():
        if key not in following['links']:
            path = Path(key)
            before = snapshot(path)
            require(before == ('link', target, None) or before[0] == 'missing', f'{path}: zmienione zarządzane dowiązanie')
            if before[0] != 'missing':
                changes[path] = (before, ('missing', None, None))
    return changes, following, notices, selected, servers, disabled


def apply(dry_run):
    _, _, state_dir = locations()
    lock = contextlib.nullcontext()
    if not dry_run:
        state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = (state_dir / 'apply.lock').open('a')
    with lock as handle:
        if handle is not None:
            fcntl.flock(handle, fcntl.LOCK_EX)
        changes, following, notices, selected, _, _ = prepare()
        for path in changes:
            print(('Plan: ' if dry_run else 'Zmieniam: ') + str(path))
        for notice in notices:
            print(notice)
        print('Harnessy: ' + (', '.join(selected) or 'brak, ustaw harnesses w local.json'))
        if dry_run:
            return
        state_path = state_dir / 'managed.json'
        content = json_bytes(following)
        before = snapshot(state_path)
        if before[1] != content:
            changes[state_path] = (before, ('file', content, 0o600))
        applied = []
        backup_dir = state_dir / 'backups' / str(time.time_ns())
        try:
            for path, (before, after) in changes.items():
                require(snapshot(path) == before, f'{path}: plik zmienił się podczas wdrażania; ponów')
                if before[0] != 'missing':
                    backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
                    backup = backup_dir / hashlib.sha256(str(path).encode()).hexdigest()
                    # Store the link as data, never follow it when making a backup.
                    atomic_write(backup, json_bytes({'path': str(path), 'kind': before[0],
                                                    'mode': before[2], 'content_hex': before[1].hex() if isinstance(before[1], bytes) else None,
                                                    'target': before[1] if before[0] == 'link' else None}))
                applied.append(path)
                install_snapshot(path, after)
        except Exception:
            for path in reversed(applied):
                install_snapshot(path, changes[path][0])
            raise


def doctor():
    changes, _, notices, selected, servers, disabled = prepare()
    problems = []
    print('Repozytorium: ' + str(ROOT))
    print('Harnessy: ' + (', '.join(selected) or 'brak'))
    for name, server in servers.items():
        if name in disabled or not set(selected).intersection(server.get('harnesses', selected)):
            continue
        if server['transport'] == 'stdio' and not shutil.which(server['command']):
            problems.append(f'{name}: brak programu {server["command"]}')
        for variable in sorted(set(server.get('requires_env', []) + server.get('env_vars', []) + list(server.get('header_env', {}).values()))):
            if not os.environ.get(variable):
                problems.append(f'{name}: brak zmiennej {variable}')
    for path in changes:
        problems.append(f'{path}: wymaga apply.sh')
    for skill in (ROOT / 'skills').iterdir():
        for path in (skill, skill / 'SKILL.md'):
            if path.is_symlink() and not path.exists():
                problems.append(f'{path}: zerwane dowiązanie; zainicjalizuj submoduły')
    if sys.platform == 'linux' and shutil.which('systemctl'):
        result = subprocess.run(['systemctl', '--user', 'is-active', '--quiet', 'agents-sync.timer'], capture_output=True)
        print('Timer: ' + ('aktywny' if result.returncode == 0 else 'nieaktywny'))
    print('T3: korzysta z konfiguracji uruchamianego harnessu; sprawdź MCP w nowej sesji. Integracje zarządzane przez T3 pozostają lokalne.')
    for line in notices + problems:
        print(line)
    require(not problems, 'Diagnostyka wykryła problemy wymienione powyżej')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['apply', 'doctor', 'guard', 'validate'])
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--staged', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'guard':
            guard(args.staged)
        elif args.action == 'validate':
            registry()
        elif args.action == 'doctor':
            doctor()
        else:
            apply(args.dry_run)
    except (ConfigError, OSError, ValueError, subprocess.CalledProcessError) as error:
        # Do not echo malformed configuration: it can contain local credentials.
        message = str(error) if isinstance(error, ConfigError) else type(error).__name__ + ': sprawdź pliki konfiguracji i dostęp do nich'
        print('Błąd: ' + message, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
