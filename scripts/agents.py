#!/usr/bin/env python3
"""Shared agent configuration. Python 3.11+, standard library only."""
import argparse
import contextlib
import copy
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
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
ALLOWED_FILES = {'AGENTS.md', 'README.md', '.gitignore', '.gitmodules', 'package.json', 'package-lock.json', 'commitlint.config.mjs', 'install.sh'}
ALLOWED_DIRS = {'skills', 'mcp', 'adapters', 'scripts', 'docs', 'tests', '.upstream', '.github', '.githooks'}
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
        # VS Code gallery names such as io.github.upstash/context7 work in every harness.
        require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ._/-]*', name), f'Invalid MCP name: {name}')
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


def guard(staged=False, snapshot=None):
    """Check tracked files too: .gitignore cannot protect an already tracked secret."""
    if snapshot:
        for entry in git('ls-tree', '-rz', snapshot).split(b'\0'):
            if entry:
                metadata, raw = entry.split(b'\t', 1)
                mode, _, object_id = metadata.decode('ascii').split()
                check_path(os.fsdecode(raw), b'' if mode == '160000' else git('cat-file', 'blob', object_id))
        names = []
    elif staged:
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
    head = snapshot or 'HEAD'
    commits = git('rev-list', 'origin/main..' + head).decode().splitlines()
    for commit in commits:
        for raw in git('diff-tree', '-m', '--root', '--no-commit-id', '--name-only', '-r', '--diff-filter=ACMR', '-z', commit).split(b'\0'):
            if raw:
                name = os.fsdecode(raw)
                mode = git('--literal-pathspecs', 'ls-tree', commit, '--', name).split()[0]
                check_path(name, b'' if mode == b'160000' else git('show', commit + ':' + name))


def convert_oauth(oauth, harness, secrets=None):
    """OpenCode and Cursor reference the client secret; Codex accepts only its value, taken from .env."""
    secret = oauth.get('client_secret_env')
    scopes = oauth.get('scopes', [])
    metadata = oauth.get('auth_server_metadata_url')
    if harness == 'codex':
        value = (secrets or {}).get(secret)
        # Without the value in .env the whole oauth table stays local, because a managed table cannot be reopened.
        table = {'oauth': {'client_id': oauth['client_id']} | ({'client_secret': value} if value else {})}
        return ({'scopes': scopes} if scopes else {}) | ({} if secret and not value else table)
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


def convert(server, harness, secrets=None):
    result = convert_plain(server, harness)
    if server.get('oauth'):
        result |= convert_oauth(server['oauth'], harness, secrets)
    return result


def claude_secret_key(name, server):
    """Claude Code files a client secret under the server name and a digest of its connection."""
    connection = {'type': server['type'], 'url': server['url'], 'headers': server.get('headers', {})}
    return name + '|' + hashlib.sha256(json.dumps(connection, separators=(',', ':')).encode()).hexdigest()[:16]


def merge_claude_secrets(path, owned, wanted):
    """Change only our entries in Claude Code's plain-text credential store; its login tokens stay as they are."""
    before = snapshot(path)
    require(before[0] != 'link', f'{path}: the credential store is a symlink; merging requires a regular file')
    data = json.loads(before[1]) if before[0] == 'file' else {}
    require(isinstance(data, dict) and isinstance(data.get('mcpOAuthClientConfig', {}), dict), f'{path}: unexpected format')
    stored = data.get('mcpOAuthClientConfig', {})
    for key in owned:
        if key not in wanted:
            stored.pop(key, None)
    for key, value in wanted.items():
        stored[key] = stored.get(key, {}) | {'clientSecret': value}
    if stored:
        data['mcpOAuthClientConfig'] = stored
    else:
        data.pop('mcpOAuthClientConfig', None)
    if before[0] == 'file' and json.loads(before[1]) == data or before[0] == 'missing' and not data:
        return None
    return before, ('file', json_bytes(data), 0o600)


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


def toml_block(servers, skills=()):
    if not servers and not skills:
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
    for path in skills:
        lines.extend(['[[skills.config]]', 'path = ' + json.dumps(path), 'enabled = false'])
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


def merge_jsonc_servers(text, old, desired, read, label, ignored=()):
    text = text if text.strip() else '{}\n'
    current, section = read(text)

    def same(name, value):
        entry = current.get(name)
        return isinstance(entry, dict) and {k: v for k, v in entry.items() if k not in ignored} == value

    for name, value in old.items():
        if name in current:
            require(same(name, value), f'{label}: managed server {name} was changed by hand')
    # An identical entry added by hand, for example from the VS Code gallery, becomes managed.
    require(all(same(name, desired[name]) for name in (set(current) - set(old)) & set(desired)),
            f'{label}: MCP name collision')
    for name in old:
        if name not in desired:
            text = jsonc_property(text, section, name, remove=True)
    for name, value in desired.items():
        if not same(name, value):
            text = jsonc_property(text, section, name, value)
    expected = {key: value for key, value in current.items() if key not in old}
    expected |= {name: current[name] if same(name, value) else value for name, value in desired.items()}
    require(read(text)[0] == expected, f'{label}: invalid JSONC result')
    return text.encode()


def merge_opencode(text, old, desired):
    return merge_jsonc_servers(text, old, desired, opencode_servers, 'OpenCode')


def toml_header(line):
    """Return the key path and array flag of a TOML table header line, or None."""
    match = re.fullmatch(r'\s*(\[\[?)([^\[\]]+)(\]\]?)\s*(?:#.*)?\n?', line)
    if not match or len(match[1]) != len(match[3]):
        return None
    try:
        node = tomllib.loads(match[1] + match[2] + match[3])
    except tomllib.TOMLDecodeError:
        return None
    keys = []
    while isinstance(node, dict) and len(node) == 1:
        key, node = next(iter(node.items()))
        keys.append(key)
    return tuple(keys), match[1] == '[['


def recover_toml_block(path, text, old, old_skills):
    """Rebuild a managed block whose BEGIN line was dropped by a Codex rewrite.

    `codex mcp add` and `codex mcp remove` rewrite every [mcp_servers.*] table and lose the
    BEGIN comment, while the trailing END stays. Cut the managed tables out by state and
    append a fresh block, but only when nothing outside the managed values would change.
    """
    text = text.replace(END, '')
    sections, current = [], []
    for line in text.splitlines(keepends=True):
        if toml_header(line) and current:
            sections.append(current)
            current = []
        current.append(line)
    sections.append(current)

    def managed(section):
        header = toml_header(section[0])
        if not header:
            return False
        keys, array = header
        if array:
            return keys == ('skills', 'config') and tomllib.loads(''.join(section[1:])).get('path') in old_skills
        if len(keys) < 2 or keys[0] != 'mcp_servers' or keys[1] not in old:
            return False
        # A local [mcp_servers.NAME.oauth] table may hold the client secret of a managed server.
        return not (keys[2:3] == ('oauth',) and 'oauth' not in old[keys[1]])

    stripped = ''.join(line for section in sections if not managed(section) for line in section)
    before = tomllib.loads(text)
    expected = copy.deepcopy(before)
    servers = expected.pop('mcp_servers', {})
    rest = {}
    for name, value in servers.items():
        if name not in old:
            rest[name] = value
            continue
        if 'oauth' in value and 'oauth' not in old[name]:
            rest[name] = {'oauth': value.pop('oauth')}
        require(value == old[name], f'{path}: damaged markers and managed server {name} was changed by hand')
    require(set(old) <= set(servers), f'{path}: damaged markers and a managed server was removed by hand')
    if rest:
        expected['mcp_servers'] = rest
    entries = before.get('skills', {}).get('config', [])
    kept = [entry for entry in entries if entry.get('path') not in old_skills]
    require(len(entries) - len(kept) == len(old_skills), f'{path}: damaged markers and the managed skills were changed by hand')
    if old_skills:
        expected['skills']['config'] = kept
        if not kept:
            del expected['skills']['config']
        if not expected['skills']:
            del expected['skills']
    require(tomllib.loads(stripped) == expected,
            f'{path}: damaged markers; move the managed tables back between BEGIN and END by hand')
    block = toml_block(old, old_skills)
    return stripped.rstrip() + ('\n\n' if stripped.strip() and block else '') + block


def merge_mcp(path, fmt, old, desired, old_skills=(), skills=()):
    require(not path.is_symlink(), f'{path}: the configuration is a symlink; merging requires a regular file')
    text = path.read_text() if path.exists() else ''
    if fmt == 'opencode':
        return merge_opencode(text, old, desired)
    if fmt == 'vscode':
        # VS Code adds and updates these when a server comes from its MCP gallery.
        return merge_jsonc_servers(text, old, desired, vscode_servers, 'VS Code', {'gallery', 'version'})
    if fmt == 'toml':
        tomllib.loads(text)
        if text.count(BEGIN) == 0 and text.count(END) == 1:
            text = recover_toml_block(path, text, old, old_skills)
        require(text.count(BEGIN) == text.count(END) <= 1, f'{path}: damaged markers')
        managed = ''
        if BEGIN in text:
            start = text.index(BEGIN)
            stop = text.index(END) + len(END)
            require(stop > start, f'{path}: markers in reverse order')
            managed = text[start:stop]
            # Codex adds new tables above a trailing comment, so they land before END. Move them out.
            body = toml_block(old, old_skills)[:-len(END)]
            foreign = managed[len(body):-len(END)] if (old or old_skills) and managed.startswith(body) else ''
            managed = managed[:len(managed) - len(END) - len(foreign)] + END
            text = text[:start] + foreign + text[stop:]
        block = tomllib.loads(managed)
        require(not (set(block) - {'mcp_servers', 'skills'}), f'{path}: foreign settings inside the managed block; move them below its END line')
        require(block.get('mcp_servers', {}) == old, f'{path}: managed block was changed by hand or state is missing')
        expected_skills = {'config': [{'path': skill, 'enabled': False} for skill in old_skills]} if old_skills else {}
        require(block.get('skills', {}) == expected_skills, f'{path}: managed skills were changed by hand or state is missing')
        remaining = tomllib.loads(text).get('mcp_servers', {})
        # A local [mcp_servers.NAME.oauth] table may hold the client secret of a managed server.
        local = {name: remaining[name] for name in set(remaining) & set(desired)}
        require(all(set(value) == {'oauth'} and 'oauth' not in desired[name] for name, value in local.items()),
                f'{path}: MCP name collision')
        result = text.rstrip() + ('\n\n' if text.strip() and (desired or skills) else '') + toml_block(desired, skills)
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


def read_env(path):
    """Read KEY=VALUE lines from the repository's .env. Errors never echo values."""
    values = {}
    if not path.is_file():
        return values
    for number, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
        require(match, f'{path}: line {number} is not KEY=VALUE')
        value = match[2]
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1]
        # environment.d expands $ and backslashes, and these values must arrive unchanged.
        require(re.fullmatch(r'[^\s$\\"\'`]*', value), f'{path}: {match[1]} holds characters environment.d would change')
        # An empty line such as NAME= is a placeholder, not a value.
        if value:
            values[match[1]] = value
    return values


def secret_requests(servers):
    """Map each variable the registry refers to onto what it holds, so a person or an agent knows what to supply."""
    requests = {}
    for name, server in servers.items():
        for header, variable in server.get('header_env', {}).items():
            requests.setdefault(variable, []).append(f'{name}: value of the {header} HTTP header')
        oauth = server.get('oauth', {})
        if oauth.get('client_secret_env'):
            requests.setdefault(oauth['client_secret_env'], []).append(
                f'{name}: OAuth client secret of client ID {oauth["client_id"]}')
        for variable in server.get('env_vars', []) + server.get('requires_env', []):
            requests.setdefault(variable, []).append(f'{name}: environment variable of the server')
    return requests


def missing_secrets(servers):
    present = read_env(ROOT / '.env')
    return {variable: uses for variable, uses in secret_requests(servers).items() if variable not in present}


def add_secrets(prompt):
    """List the variables missing from .env and, in a terminal with --prompt, ask for them without echoing."""
    path = ROOT / '.env'
    missing = missing_secrets(registry())
    if not missing:
        print(f'Secrets: {path} holds every variable the registry uses.')
        return
    interactive = prompt and sys.stdin.isatty()
    added = {}
    for variable, uses in missing.items():
        print(f'Secret {variable} ({"; ".join(uses)})')
        if interactive:
            value = getpass.getpass(f'{variable} (input hidden, Enter skips): ').strip()
            require(re.fullmatch(r'[^\s$\\"\'`]*', value), f'{variable}: whitespace, quotes, $ and backslashes are not supported')
            if value:
                added[variable] = value
    if added:
        text = path.read_text() if path.exists() else '# Local secrets for ~/.agents. Git ignores this file and the guard blocks it.\n'
        text = text + ('' if text.endswith('\n') else '\n') + ''.join(f'{name}={value}\n' for name, value in added.items())
        atomic_write(path, text.encode(), 0o600)
        print(f'Saved {", ".join(added)} in {path}.')
    left = [variable for variable in missing if variable not in added]
    if left:
        print(f'Missing in {path}: {", ".join(left)}. Add one NAME=value line for each (file mode 600), '
              'then run: bash ~/.agents/scripts/apply.sh')


def server_variables(server):
    return set(server.get('requires_env', []) + server.get('env_vars', []) + list(server.get('header_env', {}).values())
               + ([server['oauth']['client_secret_env']] if server.get('oauth', {}).get('client_secret_env') else []))


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
    secrets = read_env(ROOT / '.env')
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
            # A plugin already provides these skills, so a link would duplicate them.
            plugin_skills = adapter.get('plugin_skills', [])
            for skill in sorted((ROOT / 'skills').iterdir()):
                if (skill / 'SKILL.md').is_file() and skill.name not in plugin_skills:
                    link(base / 'skills' / skill.name, skill)
        desired = {key: convert(server, name, secrets) for key, server in servers.items()
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
        # Disable only shared files; the plugin's separate copies stay enabled.
        skills = [str(ROOT / 'skills' / skill / 'SKILL.md') for skill in adapter.get('plugin_skills', [])] if name == 'codex' else []
        old_skills = previous['mcp'].get(key, {}).get('skills', [])
        content = merge_mcp(config_path, adapter['format'], old, desired, old_skills, skills)
        claude_secrets = {}
        for server in desired:
            oauth = servers[server].get('oauth', {})
            if 'client_secret_env' not in oauth:
                continue
            variable = oauth['client_secret_env']
            if name == 'codex' and not tomllib.loads(content.decode())['mcp_servers'][server].get('oauth', {}).get('client_secret'):
                notices.append(f'Codex: put the client secret of {server} in ~/.agents/.env, or outside the managed block in {config_path} add a '
                               f'[mcp_servers.{json.dumps(server)}.oauth] section with client_id = "{oauth["client_id"]}" '
                               f'and client_secret, then run: codex mcp login {shlex.quote(server)}')
            if name == 'vscode' and server not in old:
                notices.append(f'VS Code: in {config_path} use Set Client Secret above oauth.clientId of {server} once on this computer')
            # Claude Code keeps the secret in its credential store; the plain-text store exists only on Linux.
            if name == 'claude-code' and variable in secrets and sys.platform == 'linux':
                claude_secrets[claude_secret_key(server, desired[server])] = secrets[variable]
            elif name == 'claude-code' and not any(entry.startswith(server + '|') for entry in
                                                   load_json(base / '.credentials.json', {}).get('mcpOAuthClientConfig', {})):
                # The CLI accepts only letters, digits, - and _, while the configuration file takes any name.
                if sys.platform == 'linux' or not re.fullmatch(r'[A-Za-z0-9_-]+', server):
                    notices.append(f'Claude Code: put the client secret of {server} in ~/.agents/.env and run apply.sh again')
                else:
                    notices.append(f'Claude Code: save the OAuth secret once per computer: claude mcp remove -s user {server}; '
                                   f'claude mcp add -s user --transport http --client-id {oauth["client_id"]} --client-secret '
                                   f'{server} {servers[server]["url"]}; then run apply.sh again')
        before = snapshot(config_path)
        if before[0] != 'missing' or desired or skills:
            if before[1] != content:
                changes[config_path] = (before, ('file', content, 0o600))
        following['mcp'][key] = {'format': adapter['format'], 'servers': desired}
        if name == 'claude-code':
            credentials = base / '.credentials.json'
            owned_keys = previous.get('credentials', {}).get(str(credentials), [])
            if claude_secrets or owned_keys:
                change = merge_claude_secrets(credentials, owned_keys, claude_secrets)
                if change:
                    changes[credentials] = change
            if claude_secrets:
                following.setdefault('credentials', {})[str(credentials)] = sorted(claude_secrets)
        if skills:
            following['mcp'][key]['skills'] = skills

    # GUI harnesses do not read .env; the systemd user session passes these variables to them.
    exported = {name: secrets[name] for name in sorted(set().union(*map(server_variables, servers.values()))) if name in secrets}
    env_file = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'environment.d/60-agents.conf'
    owned = previous.get('env')
    if owned and (owned != str(env_file) or not exported) and snapshot(Path(owned))[0] != 'missing':
        changes[Path(owned)] = (snapshot(Path(owned)), ('missing', None, None))
    if exported and sys.platform == 'linux':
        before = snapshot(env_file)
        require(before[0] == 'missing' or owned == str(env_file), f'{env_file}: foreign file; move its settings elsewhere')
        content = ('# Managed by ~/.agents from its .env file. Edit .env and run apply.sh.\n'
                   + ''.join(f'{name}={value}\n' for name, value in exported.items())).encode()
        if before[1] != content:
            changes[env_file] = (before, ('file', content, 0o600))
            notices.append('Session environment: log out and back in so harnesses started from the desktop see ' + ', '.join(exported))
        following['env'] = str(env_file)
    elif exported:
        notices.append('Set these variables from ~/.agents/.env in the harness environment: ' + ', '.join(exported))

    for key, owned_keys in previous.get('credentials', {}).items():
        if key not in following.get('credentials', {}):
            change = merge_claude_secrets(Path(key), owned_keys, {})
            if change:
                changes[Path(key)] = change

    # Remove only entries whose ownership and current contents still match.
    for key, entry in previous['mcp'].items():
        if key not in following['mcp']:
            path = Path(key)
            before = snapshot(path)
            content = merge_mcp(path, entry['format'], entry['servers'], {}, entry.get('skills', []))
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
                hint = '; it is in .env, so log out and back in' if variable in read_env(ROOT / '.env') else ''
                problems.append(f'{name}: missing variable {variable}{hint}')
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
    for variable, uses in missing_secrets(servers).items():
        notices.append(f'Secret {variable} is missing in {ROOT / ".env"} ({"; ".join(uses)}); run: python3 ~/.agents/scripts/agents.py secrets --prompt')
    for line in notices + problems:
        print(line)
    require(not problems, 'Diagnostics found the problems listed above')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['apply', 'doctor', 'guard', 'validate', 'secrets'])
    parser.add_argument('--prompt', action='store_true', help='secrets: ask for missing values in a terminal')
    parser.add_argument('--dry-run', action='store_true')
    guard_mode = parser.add_mutually_exclusive_group()
    guard_mode.add_argument('--staged', action='store_true')
    guard_mode.add_argument('--snapshot')
    args = parser.parse_args()
    try:
        if args.action == 'guard':
            guard(args.staged, args.snapshot)
        elif args.action == 'secrets':
            add_secrets(args.prompt)
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
