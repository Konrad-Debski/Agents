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
ALLOWED_FILES = {'AGENTS.md', 'README.md', '.gitignore', '.gitmodules', 'package.json', 'package-lock.json', 'install.sh'}
ALLOWED_DIRS = {'skills', 'mcp', 'adapters', 'scripts', 'docs', 'tests', '.upstream', '.github'}
SECRET_NAME = re.compile(r'(^|/)(\.env(?:\..*)?|credentials(?:\..*)?|auth\.json|id_rsa|id_ed25519|.*\.pem|.*\.key)$', re.I)
LOCAL_NAME = re.compile(r'(^|/)(?:\.cache|__pycache__)(?:/|$)|\.(?:log|tar|zip|gz|pyc|pyo)$', re.I)
SECRET_VALUE = re.compile(rb'-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----|\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{32,})\b')
MANUAL_INSTRUCTIONS = {
    'cursor': 'Cursor: in Customize > Rules add: Read and follow ~/.agents/AGENTS.md before every task.',
    'vscode': 'VS Code: for the Local harness, in Chat: Open Customizations > Instructions add a User instruction with the text: Read and follow ~/.agents/AGENTS.md before every task.',
}


class ConfigError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ConfigError(message)


def load_json(path, default=None):
    if not path.exists():
        require(default is not None, f'Missing file {path}')
        return copy.deepcopy(default)
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f'{path}: a JSON object is required')
    return value


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


def registry():
    data = load_json(ROOT / 'mcp/servers.json')
    require(data.get('version') == 1 and isinstance(data.get('servers'), dict), 'Unsupported MCP registry')
    for name, server in data['servers'].items():
        require(re.fullmatch(r'[A-Za-z0-9_-]+', name), f'Invalid MCP name: {name}')
        require(isinstance(server, dict), f'{name}: a server definition is required')
        transport = server.get('transport')
        fields = {'transport', 'harnesses', 'requires_env'}
        if transport == 'stdio':
            fields |= {'command', 'args', 'env_vars'}
            require(isinstance(server.get('command'), str) and server['command'], f'{name}: missing command')
            require(not server['command'].startswith(('/', '~')), f'{name}: command must be portable')
        elif transport == 'http':
            fields |= {'url', 'header_env', 'oauth'}
            require(isinstance(server.get('url'), str), f'{name}: missing url')
            oauth = server.get('oauth', {'client_id': ''})
            require(isinstance(oauth, dict) and isinstance(oauth.get('client_id'), str)
                    and not (set(oauth) - {'client_id', 'client_secret_env', 'scopes', 'auth_server_metadata_url'}),
                    f'{name}: oauth requires client_id and accepts client_secret_env, scopes, auth_server_metadata_url')
            secret_env = oauth.get('client_secret_env', '_')
            require(isinstance(secret_env, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', secret_env),
                    f'{name}: client_secret_env must name a variable')
            scopes = oauth.get('scopes', [])
            require(isinstance(scopes, list) and all(isinstance(v, str) and v and not re.search(r'\s', v) for v in scopes),
                    f'{name}: scopes must be a list of strings without whitespace')
            require(str(oauth.get('auth_server_metadata_url', 'https://')).startswith('https://'),
                    f'{name}: auth_server_metadata_url must use https')
            url = urlsplit(server['url'])
            require(url.scheme in {'https', 'http'} and url.hostname and not url.username
                    and not url.password and not url.query and not url.fragment,
                    f'{name}: the URL must have no credentials, query or fragment')
            headers = server.get('header_env', {})
            require(isinstance(headers, dict) and all(isinstance(k, str) and isinstance(v, str)
                    and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', v) for k, v in headers.items()),
                    f'{name}: header_env must name variables')
        else:
            raise ConfigError(f'{name}: supported transports are stdio and http')
        require(not (set(server) - fields), f'{name}: unknown configuration fields')
        for key in ('args', 'env_vars', 'requires_env', 'harnesses'):
            values = server.get(key, [])
            require(isinstance(values, list) and all(isinstance(v, str) for v in values), f'{name}: {key} must be a list of strings')
            if key in {'env_vars', 'requires_env'}:
                require(all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', v) for v in values), f'{name}: invalid variable name')
        if 'harnesses' in server:
            require(set(server['harnesses']) <= {'codex', 'claude-code', 'cursor', 'opencode', 'vscode'}, f'{name}: unknown harness')
    return data['servers']


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def check_path(name, blob):
    first = name.split('/')[0]
    require(name in ALLOWED_FILES or first in ALLOWED_DIRS, f'Outside the synchronization scope: {name}')
    require(not SECRET_NAME.search(name), f'Local file or secret excluded from synchronization: {name}')
    require(not LOCAL_NAME.search(name), f'Generated file excluded from synchronization: {name}')
    require(not SECRET_VALUE.search(blob), f'Possible secret in {name}; remove it before synchronizing')


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


def convert_oauth(oauth, harness):
    """Only OpenCode and Cursor can reference the client secret; the others keep it locally."""
    secret = oauth.get('client_secret_env')
    scopes = oauth.get('scopes', [])
    metadata = oauth.get('auth_server_metadata_url')
    if harness == 'codex':
        # A managed table cannot be reopened, so a client with a secret leaves the whole oauth table local.
        return ({'scopes': scopes} if scopes else {}) | ({} if secret else {'oauth': {'client_id': oauth['client_id']}})
    if harness == 'cursor':
        return {'auth': {'CLIENT_ID': oauth['client_id']} | ({'CLIENT_SECRET': '${env:' + secret + '}'} if secret else {})
                | ({'scopes': scopes} if scopes else {})}
    if harness == 'vscode':
        return {'oauth': {'clientId': oauth['client_id']}}
    if harness == 'opencode':
        return {'oauth': {'client_id': oauth['client_id']} | ({'client_secret': '{env:' + secret + '}'} if secret else {})
                | ({'scope': ' '.join(scopes)} if scopes else {})
                | ({'auth_server_metadata_url': metadata} if metadata else {})}
    return {'oauth': {'clientId': oauth['client_id']} | ({'scopes': ' '.join(scopes)} if scopes else {})
            | ({'authServerMetadataUrl': metadata} if metadata else {})}


def within(part, whole):
    return isinstance(part, dict) and isinstance(whole, dict) and all(key in whole and (within(value, whole[key]) if isinstance(value, dict)
                                           else value == whole[key]) for key, value in part.items())


def convert(server, harness):
    result = convert_plain(server, harness)
    if server.get('oauth'):
        result |= convert_oauth(server['oauth'], harness)
    return result


def convert_plain(server, harness):
    if harness == 'opencode':
        if server['transport'] == 'stdio':
            result = {'type': 'local', 'command': [server['command'], *server.get('args', [])]}
            if server.get('env_vars'):
                result['environment'] = {v: '{env:' + v + '}' for v in server['env_vars']}
        else:
            result = {'type': 'remote', 'url': server['url']}
            if server.get('header_env'):
                result['headers'] = {k: '{env:' + v + '}' for k, v in server['header_env'].items()}
        return result
    if server['transport'] == 'stdio':
        result = {'command': server['command'], 'args': server.get('args', [])}
        names = server.get('env_vars', [])
        if harness == 'codex':
            if names:
                result['env_vars'] = names
        else:
            result['type'] = 'stdio'
            if names:
                result['env'] = {v: '${env:' + v + '}' if harness in {'cursor', 'vscode'} else '${' + v + '}' for v in names}
    else:
        result = {'url': server['url']}
        headers = server.get('header_env', {})
        if harness == 'codex':
            if headers:
                result['env_http_headers'] = headers
        else:
            result['type'] = 'http'
            if headers:
                result['headers'] = {k: '${env:' + v + '}' if harness in {'cursor', 'vscode'} else '${' + v + '}' for k, v in headers.items()}
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


class JsoncNode:
    def __init__(self, value, start, end, properties=None):
        self.value, self.start, self.end = value, start, end
        self.properties = properties or []


def parse_jsonc(text):
    """Parse JSON with comments/trailing commas and retain exact property spans."""
    decoder = json.JSONDecoder()
    position = 1 if text.startswith('\ufeff') else 0

    def skip():
        nonlocal position
        while position < len(text):
            if text[position] in ' \t\r\n':
                position += 1
            elif text.startswith('//', position):
                end = text.find('\n', position)
                position = len(text) if end < 0 else end
            elif text.startswith('/*', position):
                end = text.find('*/', position + 2)
                require(end >= 0, 'JSONC: unclosed comment')
                position = end + 2
            else:
                break

    def read():
        nonlocal position
        skip()
        start = position
        require(position < len(text), 'JSONC: incomplete document')
        opening = text[position]
        if opening not in '{[':
            value, position = decoder.raw_decode(text, position)
            require(value is None or isinstance(value, (str, int, float, bool)), 'JSONC: invalid value')
            require(not isinstance(value, float) or value not in (float('inf'), float('-inf')) and value == value,
                    'JSONC: invalid number')
            return JsoncNode(value, start, position)
        closing = '}' if opening == '{' else ']'
        value = {} if opening == '{' else []
        properties = []
        position += 1
        skip()
        while position < len(text) and text[position] != closing:
            key_start = position
            if opening == '{':
                require(text[position] == '"', 'JSONC: a key must be a string')
                key, position = decoder.raw_decode(text, position)
                require(key not in value, 'JSONC: duplicate key')
                skip()
                require(position < len(text) and text[position] == ':', 'JSONC: missing colon')
                position += 1
            node = read()
            if opening == '{':
                value[key] = node.value
            else:
                value.append(node.value)
            skip()
            comma = position if position < len(text) and text[position] == ',' else None
            if opening == '{':
                properties.append((key, key_start, node, comma))
            if comma is None:
                break
            position += 1
            skip()
        require(position < len(text) and text[position] == closing, 'JSONC: invalid closing bracket')
        position += 1
        return JsoncNode(value, start, position, properties)

    node = read()
    skip()
    require(position == len(text) and isinstance(node.value, dict), 'JSONC: a single object is required')
    return node


def jsonc_property(text, section, key, value=None, remove=False):
    root = parse_jsonc(text)
    section = (section,) if isinstance(section, str) else section or ()
    node = root
    for index, part in enumerate(section):
        child = next((prop[2] for prop in node.properties if prop[0] == part), None)
        if child is None:
            if remove:
                return text
            nested = {key: value}
            for remaining in reversed(section[index + 1:]):
                nested = {remaining: nested}
            return jsonc_property(text, section[:index], part, nested)
        node = child
    require(isinstance(node.value, dict), 'JSONC: a section must be an object')
    for index, prop in enumerate(node.properties):
        name, start, child, comma = prop
        if name != key:
            continue
        if remove:
            end = child.end
            if comma is not None:
                end = comma + 1
            elif index:
                previous_comma = node.properties[index - 1][3]
                return text[:previous_comma] + text[previous_comma + 1:start] + text[end:]
            return text[:start] + text[end:]
        indent = '  ' * (len(section) + 1)
        rendered = json.dumps(value, indent=2, ensure_ascii=False).replace('\n', '\n' + indent)
        return text[:child.start] + rendered + text[child.end:]
    if remove:
        return text
    indent = '  ' * (len(section) + 1)
    rendered = json.dumps(value, indent=2, ensure_ascii=False).replace('\n', '\n' + indent)
    addition = '\n' + indent + json.dumps(key) + ': ' + rendered + (',' if node.properties else '') + '\n'
    return text[:node.start + 1] + addition + text[node.start + 1:]


def opencode_servers(text):
    mcp = parse_jsonc(text).value.get('mcp', {})
    require(isinstance(mcp, dict), 'OpenCode: mcp must be an object')
    # New files use v2; existing nonempty flat maps keep v1 compatibility.
    native = not mcp or any(key in mcp and not (isinstance(mcp[key], dict) and
                     ('type' in mcp[key] or 'enabled' in mcp[key])) for key in ('servers', 'timeout'))
    if native:
        require(not (set(mcp) - {'servers', 'timeout'}), 'OpenCode: mixed or unknown mcp format')
        servers = mcp.get('servers', {})
        require(isinstance(servers, dict), 'OpenCode: mcp.servers must be an object')
        return servers, ('mcp', 'servers')
    return mcp, ('mcp',)


def vscode_servers(text):
    servers = parse_jsonc(text).value.get('servers', {})
    require(isinstance(servers, dict), 'VS Code: servers must be an object')
    return servers, ('servers',)


def merge_jsonc_servers(text, old, desired, read, label):
    text = text if text.strip() else '{}\n'
    current, section = read(text)
    for name, value in old.items():
        if name in current:
            require(current.get(name) == value, f'{label}: managed server {name} was changed by hand')
    require(not ((set(current) - set(old)) & set(desired)), f'{label}: MCP name collision')
    for name in old:
        if name not in desired:
            text = jsonc_property(text, section, name, remove=True)
    for name, value in desired.items():
        if current.get(name) != value:
            text = jsonc_property(text, section, name, value)
    expected = {key: value for key, value in current.items() if key not in old} | desired
    require(read(text)[0] == expected, f'{label}: invalid JSONC result')
    return text.encode()


def merge_opencode(text, old, desired):
    return merge_jsonc_servers(text, old, desired, opencode_servers, 'OpenCode')


def merge_mcp(path, fmt, old, desired):
    require(not path.is_symlink(), f'{path}: the configuration is a symlink; merging requires a regular file')
    text = path.read_text() if path.exists() else ''
    if fmt == 'opencode':
        return merge_opencode(text, old, desired)
    if fmt == 'vscode':
        return merge_jsonc_servers(text, old, desired, vscode_servers, 'VS Code')
    if fmt == 'toml':
        tomllib.loads(text)
        require(text.count(BEGIN) == text.count(END) <= 1, f'{path}: damaged markers')
        managed = ''
        if BEGIN in text:
            start = text.index(BEGIN)
            stop = text.index(END) + len(END)
            require(stop > start, f'{path}: markers in reverse order')
            managed = text[start:stop]
            text = text[:start] + text[stop:]
        require(tomllib.loads(managed).get('mcp_servers', {}) == old, f'{path}: managed block was changed by hand or state is missing')
        remaining = tomllib.loads(text).get('mcp_servers', {})
        # A local [mcp_servers.NAME.oauth] table may hold the client secret of a managed server.
        local = {name: remaining[name] for name in set(remaining) & set(desired)}
        require(all(set(value) == {'oauth'} and 'oauth' not in desired[name] for name, value in local.items()),
                f'{path}: MCP name collision')
        result = text.rstrip() + ('\n\n' if text.strip() and desired else '') + toml_block(desired)
        expected = {**remaining, **{name: value | local.get(name, {}) for name, value in desired.items()}}
        require(tomllib.loads(result).get('mcp_servers', {}) == expected, f'{path}: invalid TOML result')
        return result.encode()
    data = json.loads(text) if text.strip() else {}
    require(isinstance(data, dict), f'{path}: a JSON object is required')
    current = data.get('mcpServers', {})
    require(isinstance(current, dict), f'{path}: mcpServers must be an object')
    for name, value in old.items():
        if name in current:
            # `claude mcp add --client-secret` rewrites the entry in a reduced form; restore it.
            require(current.get(name) == value or within(current[name], desired.get(name)),
                    f'{path}: managed server {name} was changed by hand')
        current.pop(name, None)
    require(not (set(current) & set(desired)), f'{path}: MCP name collision')
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
    require(not path.exists() or path.is_file(), f'{path}: collision with a directory')
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


def adapter_directory(name, adapter, home):
    if name == 'opencode':
        return Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'opencode'
    if name == 'vscode':
        # Electron places VS Code user data in $XDG_CONFIG_HOME, falling back to ~/.config.
        return Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'Code/User'
    return home / adapter['directory']


def prepare():
    home, config, state_dir = locations()
    local = load_json(config / 'local.json', {})
    require(not (set(local) - {'harnesses', 'disabled_servers', 'disabled_servers_by_harness'}), 'Unknown fields in local.json')
    adapters = {p.parent.name: load_json(p) for p in sorted((ROOT / 'adapters').glob('*/adapter.json'))}
    selected = local.get('harnesses', [name for name, adapter in adapters.items()
                       if adapter_directory(name, adapter, home).exists() or shutil.which(adapter['command'])])
    require(isinstance(selected, list) and all(name in adapters for name in selected), 'Unknown harness in local.json')
    disabled = local.get('disabled_servers', [])
    require(isinstance(disabled, list) and all(isinstance(s, str) for s in disabled), 'disabled_servers must be a list of names')
    scoped_disabled = local.get('disabled_servers_by_harness', {})
    require(isinstance(scoped_disabled, dict) and all(
        name in adapters and isinstance(names, list) and all(isinstance(s, str) for s in names)
        for name, names in scoped_disabled.items()),
        'disabled_servers_by_harness must map harnesses to lists of names')
    servers = registry()
    previous = load_json(state_dir / 'managed.json', {'version': 1, 'mcp': {}, 'links': {}})
    require(previous.get('version') == 1, 'Unsupported adapter state')
    following = {'version': 1, 'mcp': {}, 'links': {}}
    changes = {}
    notices = []

    def link(destination, source):
        path = Path(destination)
        value = str(source)
        before = snapshot(path)
        if before[0] == 'link':
            require(os.path.abspath(path.parent / before[1]) == value, f'{path}: foreign symlink; keep it and merge it by hand')
        elif before[0] == 'file':
            require(source.is_file() and before[1] == source.read_bytes(), f'{path}: existing instructions; merge them into AGENTS.md and keep a local copy before deleting the file')
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
        elif name == 'opencode':
            base = adapter_directory(name, adapter, home)
            config_path = base / ('opencode.jsonc' if (base / 'opencode.jsonc').exists() else 'opencode.json')
            instruction = base / adapter['instructions']
            for variable in ('OPENCODE_CONFIG', 'OPENCODE_CONFIG_DIR', 'OPENCODE_CONFIG_CONTENT'):
                if os.environ.get(variable):
                    notices.append(f'OpenCode: {variable} can override the global configuration; the adapter does not change this extra layer.')
        elif name == 'vscode':
            base = adapter_directory(name, adapter, home)
            config_path = base / 'mcp.json'
            instruction = None
        else:
            base = home / adapter['directory']
            config_path = home / adapter['mcp']
            instruction = None
        if instruction:
            link(instruction, ROOT / 'AGENTS.md')
        else:
            notices.append(MANUAL_INSTRUCTIONS[name])
        if adapter['skills'] == 'native':
            # In the canonical checkout these are already ordinary repository files.
            canonical = (home / '.agents/skills').resolve() == (ROOT / 'skills').resolve() and not (home / '.agents/skills').is_symlink()
            if not canonical:
                link(home / '.agents/skills', ROOT / 'skills')
        else:
            for skill in sorted((ROOT / 'skills').iterdir()):
                if (skill / 'SKILL.md').is_file():
                    link(base / 'skills' / skill.name, skill)
        desired = {key: convert(server, name) for key, server in servers.items()
                   if key not in disabled and key not in scoped_disabled.get(name, [])
                   and name in server.get('harnesses', selected)}
        key = str(config_path)
        old = previous['mcp'].get(key, {}).get('servers', {})
        if name == 'opencode':
            other = base / ('opencode.json' if config_path.suffix == '.jsonc' else 'opencode.jsonc')
            if other.exists():
                owned = previous['mcp'].get(str(other), {}).get('servers', {})
                remaining, _ = opencode_servers(merge_mcp(other, 'opencode', owned, {}).decode())
                require(not (set(remaining) & set(desired)), f'{other}: MCP collision in the second OpenCode file')
        content = merge_mcp(config_path, adapter['format'], old, desired)
        for server in desired:
            oauth = servers[server].get('oauth', {})
            if 'client_secret_env' not in oauth:
                continue
            if name == 'codex' and not tomllib.loads(content.decode())['mcp_servers'][server].get('oauth', {}).get('client_secret'):
                notices.append(f'Codex: outside the managed block in {config_path}, add a [mcp_servers.{server}.oauth] section '
                               f'with client_id = "{oauth["client_id"]}" and client_secret, then run: codex mcp login {server}')
            # Claude Code keeps the secret in its credential store; the plain-text store exists only on Linux.
            if name == 'claude-code' and not any(entry.startswith(server + '|') for entry in
                                                 load_json(base / '.credentials.json', {}).get('mcpOAuthClientConfig', {})):
                notices.append(f'Claude Code: save the OAuth secret once per computer: claude mcp remove -s user {server}; '
                               f'claude mcp add -s user --transport http --client-id {oauth["client_id"]} --client-secret '
                               f'{server} {servers[server]["url"]}; then run apply.sh again')
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
            require(before == ('link', target, None) or before[0] == 'missing', f'{path}: managed link was changed')
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
            print(('Plan: ' if dry_run else 'Changing: ') + str(path))
        for notice in notices:
            print(notice)
        print('Harnesses: ' + (', '.join(selected) or 'none, set harnesses in local.json'))
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
                require(snapshot(path) == before, f'{path}: the file changed during apply; try again')
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
    _, config, _ = locations()
    scoped_disabled = load_json(config / 'local.json', {}).get('disabled_servers_by_harness', {})
    problems = []
    print('Repository: ' + str(ROOT))
    print('Harnesses: ' + (', '.join(selected) or 'none'))
    for name, server in servers.items():
        if name in disabled or not any(
                harness in server.get('harnesses', selected)
                and name not in scoped_disabled.get(harness, []) for harness in selected):
            continue
        if server['transport'] == 'stdio' and not shutil.which(server['command']):
            problems.append(f'{name}: missing program {server["command"]}')
        secret = server.get('oauth', {}).get('client_secret_env')
        # Only these harnesses read the client secret from the environment.
        referenced = [secret] if secret and any(
            harness in server.get('harnesses', selected) and name not in scoped_disabled.get(harness, [])
            for harness in {'cursor', 'opencode'} & set(selected)) else []
        for variable in sorted(set(server.get('requires_env', []) + server.get('env_vars', []) + referenced
                                   + list(server.get('header_env', {}).values()))):
            if not os.environ.get(variable):
                problems.append(f'{name}: missing variable {variable}')
    for path in changes:
        problems.append(f'{path}: needs apply.sh')
    for skill in (ROOT / 'skills').iterdir():
        for path in (skill, skill / 'SKILL.md'):
            if path.is_symlink() and not path.exists():
                problems.append(f'{path}: broken link; initialize the submodules')
    if sys.platform == 'linux' and shutil.which('systemctl'):
        result = subprocess.run(['systemctl', '--user', 'is-active', '--quiet', 'agents-sync.timer'], capture_output=True)
        print('Timer: ' + ('active' if result.returncode == 0 else 'inactive'))
    print('T3: uses the configuration of the harness it launches; check MCP in a new session. Integrations managed by T3 stay local.')
    for line in notices + problems:
        print(line)
    require(not problems, 'Diagnostics found the problems listed above')


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
        message = str(error) if isinstance(error, ConfigError) else type(error).__name__ + ': check the configuration files and access to them'
        print('Error: ' + message, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
