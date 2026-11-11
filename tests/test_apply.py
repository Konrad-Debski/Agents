"""Exercise adapters against real files in an isolated HOME."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agents-apply-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / 'home'
        self.repo = self.home / '.agents'
        self.repo.mkdir(parents=True)
        for directory in ('scripts', 'adapters', 'mcp'):
            shutil.copytree(ROOT / directory, self.repo / directory)
        (self.repo / 'AGENTS.md').write_text('Shared instructions\n')
        skill = self.repo / 'skills/example'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('Example skill\n')
        self.config = self.base / 'config'
        self.state = self.base / 'state'
        self.env = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.config),
                        XDG_STATE_HOME=str(self.state))
        self.env.pop('CODEX_HOME', None)
        self.env.pop('CLAUDE_CONFIG_DIR', None)
        for variable in ('OPENCODE_CONFIG', 'OPENCODE_CONFIG_DIR', 'OPENCODE_CONFIG_CONTENT'):
            self.env.pop(variable, None)
        self.env['CONTEXT7_AUTHORIZATION'] = 'Bearer test-context7-key'
        self.env['GOOGLE_SHEETS_MCP_CLIENT_SECRET'] = 'test-sheets-client-secret'
        self.local(['codex', 'claude-code', 'cursor', 'opencode', 'vscode'])

    def local(self, harnesses, disabled=None):
        path = self.config / 'agents/local.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'harnesses': harnesses, 'disabled_servers': disabled or []}))

    def write(self, relative, text):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def run_apply(self, *options, success=True, action='apply'):
        result = subprocess.run(['python3', str(self.repo / 'scripts/agents.py'), action, *options],
                                env=self.env, capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def servers(self):
        path = self.repo / 'mcp/servers.json'
        return path, json.loads(path.read_text())

    def test_dry_run_writes_no_state_or_harness_configuration(self):
        self.run_apply('--dry-run')
        self.assertFalse(self.state.exists())
        self.assertFalse((self.home / '.codex').exists())
        self.assertFalse((self.home / '.claude.json').exists())
        self.assertFalse((self.config / 'opencode').exists())

    def test_all_adapters_preserve_settings_and_repeat_without_writes(self):
        codex = self.write('.codex/config.toml', '# Personal comment\nmodel = "my-model"\n[mcp_servers.personal]\ncommand = "custom"\n')
        claude = self.write('.claude.json', '{"oauthAccount": {"local": "keep"}, "mcpServers": {"personal": {"command": "custom"}}}')
        self.run_apply()
        self.assertEqual(tomllib.loads(codex.read_text())['model'], 'my-model')
        self.assertIn('# Personal comment', codex.read_text())
        self.assertIn('personal', tomllib.loads(codex.read_text())['mcp_servers'])
        self.assertEqual(json.loads(claude.read_text())['oauthAccount'], {'local': 'keep'})
        self.assertEqual((self.home / '.codex/AGENTS.md').resolve(), self.repo / 'AGENTS.md')
        self.assertEqual((self.home / '.claude/skills/example').resolve(), self.repo / 'skills/example')
        self.assertFalse((self.home / '.cursor/skills').exists())
        self.assertEqual((self.config / 'opencode/AGENTS.md').resolve(), self.repo / 'AGENTS.md')
        self.assertFalse((self.config / 'opencode/skills').exists())
        opencode = self.config / 'opencode/opencode.json'
        opencode_before = opencode.stat().st_mtime_ns
        vscode = self.config / 'Code/User/mcp.json'
        vscode_before = vscode.stat().st_mtime_ns
        before = {p: p.stat().st_mtime_ns for p in self.home.rglob('*') if p.is_file()}
        state_before = (self.state / 'agents/managed.json').stat().st_mtime_ns
        self.run_apply()
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in before})
        self.assertEqual(state_before, (self.state / 'agents/managed.json').stat().st_mtime_ns)
        self.assertEqual(opencode_before, opencode.stat().st_mtime_ns)
        self.assertEqual(vscode_before, vscode.stat().st_mtime_ns)
        for path in (self.state / 'agents/backups').rglob('*'):
            if path.is_file():
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_name_collision_prevents_all_configuration_writes(self):
        self.write('.cursor/mcp.json', '{"mcpServers":{"context7":{"url":"https://personal.example/mcp"}}}')
        self.run_apply(success=False)
        self.assertFalse((self.home / '.codex/AGENTS.md').exists())
        self.assertFalse((self.home / '.claude.json').exists())

    def test_claude_adds_new_symlinked_skills_and_reads_upstream_updates(self):
        self.local(['claude-code'])
        self.run_apply()
        upstream = self.repo / '.upstream/vendor/skills/new-skill'
        upstream.mkdir(parents=True)
        (upstream / 'SKILL.md').write_text('First upstream version\n')
        source = self.repo / 'skills/new-skill'
        source.symlink_to('../.upstream/vendor/skills/new-skill', target_is_directory=True)

        self.run_apply()
        installed = self.home / '.claude/skills/new-skill'
        self.assertTrue(installed.is_symlink())
        self.assertEqual(os.readlink(installed), str(source))
        self.assertEqual((installed / 'SKILL.md').read_text(), 'First upstream version\n')
        before = installed.lstat().st_mtime_ns

        (upstream / 'SKILL.md').write_text('Updated upstream version\n')
        self.assertEqual((installed / 'SKILL.md').read_text(), 'Updated upstream version\n')
        self.run_apply()
        self.assertEqual(installed.lstat().st_mtime_ns, before)

    def test_new_claude_skill_preserves_a_personal_skill_with_the_same_name(self):
        self.local(['claude-code'])
        self.run_apply()
        personal = self.write('.claude/skills/new-skill/SKILL.md', 'Personal skill\n')
        source = self.repo / 'skills/new-skill'
        source.mkdir()
        (source / 'SKILL.md').write_text('Shared skill\n')

        self.run_apply(success=False)
        self.assertEqual(personal.read_text(), 'Personal skill\n')
        self.assertFalse(personal.parent.is_symlink())

    def test_existing_instructions_are_not_overwritten(self):
        path = self.write('.codex/AGENTS.md', 'My existing instructions')
        self.run_apply(success=False)
        self.assertEqual(path.read_text(), 'My existing instructions')
        self.assertFalse(path.is_symlink())

    def test_manual_edit_of_managed_entry_is_preserved(self):
        self.run_apply()
        path = self.home / '.claude.json'
        data = json.loads(path.read_text())
        data['mcpServers']['context7']['url'] = 'https://hand-edited.example/mcp'
        path.write_text(json.dumps(data))
        before = path.read_bytes()
        self.run_apply(success=False)
        self.assertEqual(path.read_bytes(), before)

    def test_manual_edit_of_managed_toml_block_is_preserved(self):
        self.run_apply()
        path = self.home / '.codex/config.toml'
        path.write_text(path.read_text().replace('https://mcp.context7.com/mcp', 'https://hand-edited.example/mcp'))
        before = path.read_bytes()
        self.run_apply(success=False)
        self.assertEqual(path.read_bytes(), before)

    def test_removal_cleans_only_owned_servers_and_links(self):
        personal = self.write('.claude/skills/personal/SKILL.md', 'Personal')
        self.write('.claude.json', '{"mcpServers":{"personal":{"command":"custom"}}}')
        self.run_apply()
        shutil.rmtree(self.repo / 'skills/example')
        path, data = self.servers()
        del data['servers']['context7']
        path.write_text(json.dumps(data))
        self.run_apply()
        self.assertFalse((self.home / '.claude/skills/example').is_symlink())
        self.assertTrue(personal.exists())
        self.assertNotIn('context7', json.loads((self.home / '.claude.json').read_text())['mcpServers'])
        self.local([])
        self.run_apply()
        self.assertEqual(set(json.loads((self.home / '.claude.json').read_text())['mcpServers']), {'personal'})
        self.assertFalse((self.home / '.codex/AGENTS.md').is_symlink())

    def test_env_references_never_materialize_secret_values(self):
        path, data = self.servers()
        data['servers']['private'] = {'transport': 'http', 'url': 'https://example.com/mcp',
                                      'header_env': {'X-API-Key': 'PRIVATE_MCP_KEY'}}
        data['servers']['localTool'] = {'transport': 'stdio', 'command': 'my-mcp-server',
                                        'args': ['serve'], 'env_vars': ['PRIVATE_MCP_KEY']}
        path.write_text(json.dumps(data))
        self.env['PRIVATE_MCP_KEY'] = 'secret-value-only-in-the-process'
        self.run_apply()
        codex = tomllib.loads((self.home / '.codex/config.toml').read_text())['mcp_servers']
        self.assertEqual(codex['private']['env_http_headers'], {'X-API-Key': 'PRIVATE_MCP_KEY'})
        claude = json.loads((self.home / '.claude.json').read_text())['mcpServers']
        cursor = json.loads((self.home / '.cursor/mcp.json').read_text())['mcpServers']
        self.assertEqual(claude['private']['headers'], {'X-API-Key': '${PRIVATE_MCP_KEY}'})
        self.assertEqual(codex['localTool']['env_vars'], ['PRIVATE_MCP_KEY'])
        self.assertEqual(claude['localTool']['env'], {'PRIVATE_MCP_KEY': '${PRIVATE_MCP_KEY}'})
        self.assertEqual(cursor['localTool']['env'], {'PRIVATE_MCP_KEY': '${env:PRIVATE_MCP_KEY}'})
        opencode = json.loads((self.config / 'opencode/opencode.json').read_text())['mcp']['servers']
        self.assertEqual(opencode['localTool']['command'], ['my-mcp-server', 'serve'])
        self.assertEqual(opencode['localTool']['environment'], {'PRIVATE_MCP_KEY': '{env:PRIVATE_MCP_KEY}'})
        self.assertEqual(opencode['private'], {'type': 'remote', 'url': 'https://example.com/mcp',
                                             'headers': {'X-API-Key': '{env:PRIVATE_MCP_KEY}'}})
        for base in (self.home, self.state, self.config):
            for file in base.rglob('*'):
                if file.is_file():
                    self.assertNotIn(self.env['PRIVATE_MCP_KEY'].encode(), file.read_bytes())
                    self.assertNotIn(self.env['CONTEXT7_AUTHORIZATION'].encode(), file.read_bytes())

    def test_context7_migrates_managed_stdio_to_http_for_all_adapters(self):
        path, data = self.servers()
        remote = data['servers']['context7']
        data['servers']['context7'] = {'transport': 'stdio', 'command': 'npx',
                                       'args': ['-y', '@upstash/context7-mcp']}
        path.write_text(json.dumps(data))
        self.run_apply()
        data['servers']['context7'] = remote
        path.write_text(json.dumps(data))
        self.run_apply()

        url = 'https://mcp.context7.com/mcp'
        codex = tomllib.loads((self.home / '.codex/config.toml').read_text())['mcp_servers']['context7']
        self.assertEqual(codex, {'url': url})
        for harness, filename in (
                ('claude-code', '.claude.json'), ('cursor', '.cursor/mcp.json')):
            with self.subTest(harness=harness):
                server = json.loads((self.home / filename).read_text())['mcpServers']['context7']
                self.assertEqual(server, {'type': 'http', 'url': url})
        self.assertEqual(self.vscode_servers()['context7'], {'type': 'http', 'url': url})
        opencode = json.loads((self.config / 'opencode/opencode.json').read_text())['mcp']['servers']['context7']
        self.assertEqual(opencode, {'type': 'remote', 'url': url})
        result = self.run_apply('--dry-run')
        self.assertNotIn('Plan:', result.stdout)

    def test_context7_works_without_authorization_environment(self):
        self.env.pop('CONTEXT7_AUTHORIZATION')
        self.run_apply()
        result = self.run_apply(action='doctor')
        self.assertNotIn('CONTEXT7_AUTHORIZATION', result.stdout)

    def test_context7_explicit_authorization_uses_environment_reference(self):
        path, data = self.servers()
        data['servers']['context7']['header_env'] = {'Authorization': 'CONTEXT7_AUTHORIZATION'}
        path.write_text(json.dumps(data))
        self.run_apply()
        codex = tomllib.loads((self.home / '.codex/config.toml').read_text())['mcp_servers']['context7']
        self.assertEqual(codex['env_http_headers'], {'Authorization': 'CONTEXT7_AUTHORIZATION'})
        self.assertEqual(self.vscode_servers()['context7']['headers'],
                         {'Authorization': '${env:CONTEXT7_AUTHORIZATION}'})
        self.env.pop('CONTEXT7_AUTHORIZATION')
        result = self.run_apply(action='doctor', success=False)
        self.assertIn('context7: missing variable CONTEXT7_AUTHORIZATION', result.stdout)

    def test_deleted_managed_json_entries_are_recreated(self):
        self.run_apply()
        for path, section in ((self.home / '.claude.json', ('mcpServers',)),
                              (self.config / 'Code/User/mcp.json', ('servers',)),
                              (self.config / 'opencode/opencode.json', ('mcp', 'servers'))):
            data = json.loads(path.read_text())
            servers = data
            for key in section:
                servers = servers[key]
            del servers['context7']
            path.write_text(json.dumps(data))
        self.run_apply()
        self.assertIn('context7', self.vscode_servers())
        self.assertIn('context7', json.loads((self.home / '.claude.json').read_text())['mcpServers'])
        self.assertIn('context7', json.loads((self.config / 'opencode/opencode.json').read_text())['mcp']['servers'])

    def test_harness_specific_disable_preserves_personal_remote_context7(self):
        self.run_apply()
        path = self.config / 'Code/User/mcp.json'
        data = json.loads(path.read_text())
        del data['servers']['context7']
        personal = {'type': 'http', 'url': 'https://mcp.context7.com/mcp',
                    'headers': {'Authorization': '${input:Authorization}'}}
        data['servers']['io.github.upstash/context7'] = personal
        path.write_text(json.dumps(data))
        local = self.config / 'agents/local.json'
        data = json.loads(local.read_text())
        data['disabled_servers_by_harness'] = {'vscode': ['context7', 'figma', 'google-sheets-official'], 'opencode': ['context7']}
        local.write_text(json.dumps(data))
        self.run_apply()
        self.assertEqual(self.vscode_servers(), {'io.github.upstash/context7': personal})
        self.assertNotIn('context7', json.loads((self.config / 'opencode/opencode.json').read_text())['mcp']['servers'])
        self.assertIn('context7', json.loads((self.home / '.claude.json').read_text())['mcpServers'])
        self.assertIn('context7', tomllib.loads((self.home / '.codex/config.toml').read_text())['mcp_servers'])
        self.run_apply(action='doctor')

    def test_doctor_skips_requirements_disabled_for_all_selected_harnesses(self):
        self.local(['vscode'])
        path, data = self.servers()
        data['servers']['context7']['requires_env'] = ['MISSING_AGENT_TEST_KEY']
        path.write_text(json.dumps(data))
        local = self.config / 'agents/local.json'
        data = json.loads(local.read_text())
        data['disabled_servers_by_harness'] = {'vscode': ['context7']}
        local.write_text(json.dumps(data))
        self.env.pop('MISSING_AGENT_TEST_KEY', None)
        self.run_apply()
        self.run_apply(action='doctor')

    def test_invalid_harness_specific_disable_prevents_writes(self):
        local = self.config / 'agents/local.json'
        for invalid in ([], {'unknown': ['context7']}, {'codex': 'context7'}, {'codex': [1]}):
            with self.subTest(invalid=invalid):
                local.write_text(json.dumps({'harnesses': ['codex'], 'disabled_servers_by_harness': invalid}))
                self.run_apply(success=False)
                self.assertFalse((self.home / '.codex/config.toml').exists())

    def test_invalid_registry_prevents_writes(self):
        path, data = self.servers()
        data['servers']['private'] = {'transport': 'http', 'url': 'https://example.com/mcp?token=secret'}
        path.write_text(json.dumps(data))
        self.run_apply(success=False)
        self.assertFalse((self.home / '.claude.json').exists())

    def test_custom_harness_directories(self):
        self.env['CODEX_HOME'] = str(self.home / 'custom-codex')
        self.env['CLAUDE_CONFIG_DIR'] = str(self.home / 'custom-claude')
        self.run_apply()
        self.assertTrue((self.home / 'custom-codex/config.toml').exists())
        self.assertTrue((self.home / 'custom-claude/.claude.json').exists())
        self.assertFalse((self.home / '.claude.json').exists())

    def test_failed_write_rolls_back_all_preceding_writes(self):
        spec = importlib.util.spec_from_file_location('agents_test', self.repo / 'scripts/agents.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = module.install_snapshot
        calls = 0

        def failing(path, value):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError('simulated disk failure')
            return original(path, value)

        with mock.patch.dict(os.environ, self.env, clear=True), mock.patch.object(module, 'install_snapshot', side_effect=failing):
            with self.assertRaises(OSError):
                module.apply(False)
        self.assertFalse((self.home / '.claude.json').exists())
        self.assertFalse((self.home / '.claude/CLAUDE.md').is_symlink())
        self.assertFalse((self.state / 'agents/managed.json').exists())

    def test_oauth_server_reaches_every_harness_without_materializing_the_secret(self):
        self.run_apply()
        url, client = 'https://sheetsmcp.googleapis.com/mcp/v1', json.loads(
            (self.repo / 'mcp/servers.json').read_text())['servers']['google-sheets-official']['oauth']['client_id']
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.readonly']
        metadata = 'https://accounts.google.com/.well-known/openid-configuration'
        codex = tomllib.loads((self.home / '.codex/config.toml').read_text())['mcp_servers']
        self.assertEqual(codex['google-sheets-official'], {'url': url, 'scopes': scopes})
        claude = json.loads((self.home / '.claude.json').read_text())['mcpServers']
        self.assertEqual(claude['google-sheets-official'], {'type': 'http', 'url': url, 'oauth': {
            'clientId': client, 'scopes': ' '.join(scopes), 'authServerMetadataUrl': metadata}})
        cursor = json.loads((self.home / '.cursor/mcp.json').read_text())['mcpServers']
        self.assertEqual(cursor['google-sheets-official'], {'type': 'http', 'url': url, 'auth': {
            'CLIENT_ID': client, 'CLIENT_SECRET': '${env:GOOGLE_SHEETS_MCP_CLIENT_SECRET}', 'scopes': scopes}})
        opencode = json.loads((self.config / 'opencode/opencode.json').read_text())['mcp']['servers']
        self.assertEqual(opencode['google-sheets-official'], {'type': 'remote', 'url': url, 'oauth': {
            'client_id': client, 'client_secret': '{env:GOOGLE_SHEETS_MCP_CLIENT_SECRET}', 'scope': ' '.join(scopes),
            'auth_server_metadata_url': metadata}})
        vscode = json.loads((self.config / 'Code/User/mcp.json').read_text())['servers']
        self.assertEqual(vscode['google-sheets-official'], {'type': 'http', 'url': url, 'oauth': {'clientId': client}})
        for base in (self.home, self.state, self.config):
            for file in base.rglob('*'):
                if file.is_file():
                    self.assertNotIn(self.env['GOOGLE_SHEETS_MCP_CLIENT_SECRET'].encode(), file.read_bytes())

    def test_codex_keeps_local_oauth_table_next_to_managed_server(self):
        self.local(['codex'])
        codex = self.write('.codex/config.toml', '[mcp_servers.google-sheets-official.oauth]\nclient_id = "local"\nclient_secret = "local-secret"\n')
        result = self.run_apply()
        self.assertNotIn('client_secret', result.stdout)
        server = tomllib.loads(codex.read_text())['mcp_servers']['google-sheets-official']
        self.assertEqual(server['oauth'], {'client_id': 'local', 'client_secret': 'local-secret'})
        self.assertEqual(server['url'], 'https://sheetsmcp.googleapis.com/mcp/v1')
        self.run_apply()
        codex.write_text('[mcp_servers.google-sheets-official]\nurl = "https://personal.example/mcp"\n')
        self.run_apply(success=False)

    def test_codex_and_claude_report_missing_local_oauth_secret(self):
        self.local(['codex', 'claude-code'])
        result = self.run_apply()
        self.assertIn('[mcp_servers.google-sheets-official.oauth]', result.stdout)
        self.assertIn('claude mcp add -s user', result.stdout)
        self.write('.claude/.credentials.json', '{"mcpOAuthClientConfig": {"google-sheets-official|0123": {"clientSecret": "x"}}}')
        self.assertNotIn('claude mcp add', self.run_apply().stdout)

    def test_claude_entry_reduced_by_cli_is_restored(self):
        self.local(['claude-code'])
        self.run_apply()
        path = self.home / '.claude.json'
        data = json.loads(path.read_text())
        expected = dict(data['mcpServers']['google-sheets-official'])
        data['mcpServers']['google-sheets-official'] = {'type': 'http', 'url': expected['url'],
                                                        'oauth': {'clientId': expected['oauth']['clientId']}}
        path.write_text(json.dumps(data))
        self.run_apply()
        self.assertEqual(json.loads(path.read_text())['mcpServers']['google-sheets-official'], expected)

    def test_doctor_requires_oauth_secret_only_for_harnesses_reading_environment(self):
        self.env.pop('GOOGLE_SHEETS_MCP_CLIENT_SECRET')
        self.local(['codex', 'claude-code', 'vscode'])
        self.run_apply()
        self.assertNotIn('GOOGLE_SHEETS_MCP_CLIENT_SECRET', self.run_apply(action='doctor').stdout)
        self.local(['opencode'])
        self.run_apply()
        self.assertIn('GOOGLE_SHEETS_MCP_CLIENT_SECRET', self.run_apply(action='doctor', success=False).stdout)

    def test_invalid_oauth_definition_prevents_writes(self):
        path, data = self.servers()
        data['servers']['google-sheets-official']['oauth']['client_secret'] = 'literal'
        path.write_text(json.dumps(data))
        self.run_apply(success=False)
        self.assertFalse((self.home / '.claude.json').exists())

    def test_validate_rejects_non_string_oauth_environment_reference(self):
        path, data = self.servers()
        for invalid in (True, None, 42):
            with self.subTest(invalid=invalid):
                data['servers']['probe'] = {'transport': 'http', 'url': 'https://example.com/mcp',
                    'oauth': {'client_id': 'client', 'client_secret_env': invalid}}
                path.write_text(json.dumps(data))
                result = self.run_apply(action='validate', success=False)
                self.assertIn('client_secret_env', result.stderr)

    def test_doctor_reports_missing_environment_without_exposing_values(self):
        path, data = self.servers()
        data['servers']['context7']['requires_env'] = ['MISSING_AGENT_TEST_KEY']
        path.write_text(json.dumps(data))
        self.env.pop('MISSING_AGENT_TEST_KEY', None)
        self.run_apply()
        result = self.run_apply(action='doctor', success=False)
        self.assertIn('MISSING_AGENT_TEST_KEY', result.stdout)

    def opencode_config(self, content, filename='opencode.json'):
        path = self.config / 'opencode' / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_opencode_json_preserves_personal_settings_and_mcp(self):
        self.local(['opencode'])
        original = '{"provider":{"custom":{"apiKey":"{env:PRIVATE_KEY}"}},"mcp":{"personal":{"type":"remote","url":"https://example.com/personal"}}}'
        path = self.opencode_config(original)
        self.run_apply()
        result = json.loads(path.read_text())
        self.assertEqual(result['provider'], json.loads(original)['provider'])
        self.assertEqual(result['mcp']['personal'], json.loads(original)['mcp']['personal'])
        self.assertEqual(result['mcp']['context7']['type'], 'remote')
        self.assertNotIn('openaiDeveloperDocs', result['mcp'])
        self.local([])
        self.run_apply()
        self.assertEqual(json.loads(path.read_text()), json.loads(original))
        self.assertFalse((self.config / 'opencode/AGENTS.md').is_symlink())

    def test_opencode_jsonc_preserves_comments_trailing_commas_and_strings(self):
        self.local(['opencode'])
        personal = '"personal": {"type": "remote", "url": "https://example.com/a//b",},'
        path = self.opencode_config('''// Keep this header
{
  /* Keep provider formatting */ "provider": {"custom": {"apiKey": "{env:PRIVATE_KEY}"},},
  "mcp": {
    // Keep personal server comment
    ''' + personal + '''
  },
}
''', 'opencode.jsonc')
        self.run_apply()
        for preserved in ('// Keep this header', '/* Keep provider formatting */',
                          '// Keep personal server comment', personal,
                          '"provider": {"custom": {"apiKey": "{env:PRIVATE_KEY}"},},'):
            self.assertIn(preserved, path.read_text())
        before = path.read_bytes()
        self.run_apply()
        self.assertEqual(before, path.read_bytes())
        self.assertFalse((self.config / 'opencode/opencode.json').exists())
        self.local([])
        self.run_apply()
        self.assertNotIn('context7', path.read_text())
        self.assertIn(personal, path.read_text())

    def test_opencode_v2_jsonc_preserves_timeouts_and_personal_servers(self):
        self.local(['opencode'])
        personal = '"personal": {"type":"remote", "url":"https://example.com/personal", "disabled":true}'
        timeout = '"timeout": {"startup": 10000, "catalog": 5000}'
        path = self.opencode_config('\ufeff{/* Header */ "mcp": {' + timeout +
                                    ', "servers": {/* Personal comment */ ' + personal + ',}},}', 'opencode.jsonc')
        self.run_apply()
        for preserved in ('\ufeff{/* Header */', timeout, personal, '/* Personal comment */'):
            self.assertIn(preserved, path.read_text())
        before = path.read_bytes()
        self.run_apply()
        self.assertEqual(before, path.read_bytes())
        self.local([])
        self.run_apply()
        self.assertNotIn('context7', path.read_text())
        self.assertIn(timeout, path.read_text())
        self.assertIn(personal, path.read_text())

    def test_opencode_v2_collision_in_second_file_is_detected(self):
        self.local(['opencode'])
        first = self.opencode_config('{"mcp":{"servers":{"context7":{"type":"local","command":["custom"]}}}}')
        second = self.opencode_config('{/* Secondary config */}', 'opencode.jsonc')
        before = (first.read_bytes(), second.read_bytes())
        self.run_apply(success=False)
        self.assertEqual(before, (first.read_bytes(), second.read_bytes()))

    def test_opencode_removes_managed_entries_in_different_positions(self):
        self.local(['opencode'])
        servers_path, shared = self.servers()
        shared['servers']['probe'] = {'transport': 'http', 'url': 'https://example.com/probe'}
        servers_path.write_text(json.dumps(shared))
        path = self.opencode_config('{"mcp":{"servers":{"personal":{"type":"remote","url":"https://example.com"}}}}')
        self.run_apply()
        data = json.loads(path.read_text())
        servers = data['mcp']['servers']
        # Exercise removal both before and after an unmanaged property.
        data['mcp']['servers'] = {'context7': servers['context7'], 'personal': servers['personal'],
                                  'probe': servers['probe']}
        path.write_text(json.dumps(data))
        self.local([])
        self.run_apply()
        self.assertEqual(set(json.loads(path.read_text())['mcp']['servers']), {'personal'})

    def test_opencode_name_collision_in_second_config_prevents_writes(self):
        self.local(['opencode'])
        first = self.opencode_config('{"mcp":{"context7":{"type":"remote","url":"https://personal.example/mcp"}}}')
        second = self.opencode_config('{/* Higher precedence */ "model": "personal/model"}', 'opencode.jsonc')
        first_before, second_before = first.read_bytes(), second.read_bytes()
        result = self.run_apply(success=False)
        self.assertIn('second OpenCode file', result.stderr)
        self.assertEqual((first_before, second_before), (first.read_bytes(), second.read_bytes()))
        self.assertFalse((self.config / 'opencode/AGENTS.md').exists())

    def test_opencode_migrates_owned_entries_when_jsonc_is_created(self):
        self.local(['opencode'])
        first = self.opencode_config('{"mcp":{"personal":{"type":"remote","url":"https://example.com/personal"}}}')
        self.run_apply()
        second = self.opencode_config('{/* Keep */ "model":"personal/model"}', 'opencode.jsonc')
        self.run_apply()
        self.assertEqual(set(json.loads(first.read_text())['mcp']), {'personal'})
        self.assertIn('context7', second.read_text())
        before = (first.read_bytes(), second.read_bytes())
        self.run_apply()
        self.assertEqual(before, (first.read_bytes(), second.read_bytes()))

    def test_opencode_detects_managed_edits_before_any_writes(self):
        self.local(['opencode'])
        self.run_apply()
        path = self.config / 'opencode/opencode.json'
        data = json.loads(path.read_text())
        data['mcp']['servers']['context7']['url'] = 'https://hand-edited.example/mcp'
        path.write_text(json.dumps(data))
        before = path.read_bytes()
        self.run_apply(success=False)
        self.assertEqual(before, path.read_bytes())

    def test_opencode_filters_harness_and_disabled_servers(self):
        self.local(['opencode'], ['context7', 'figma', 'google-sheets-official'])
        path, data = self.servers()
        data['servers']['codexOnly'] = {'transport':'http', 'url':'https://example.com/codex', 'harnesses':['codex']}
        data['servers']['openaiDeveloperDocs']['harnesses'] = ['opencode']
        path.write_text(json.dumps(data))
        self.run_apply()
        self.assertEqual(set(json.loads((self.config / 'opencode/opencode.json').read_text())['mcp']['servers']), {'openaiDeveloperDocs'})

    def test_opencode_autodetection_uses_xdg_directory(self):
        self.opencode_config('{}')
        local = self.config / 'agents/local.json'
        local.write_text('{}')
        # Exclude the actual harness binaries installed on the test host.
        self.env['PATH'] = ''
        result = subprocess.run([shutil.which('python3'), str(self.repo / 'scripts/agents.py'), 'apply'],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Harnesses: opencode', result.stdout)
        self.assertTrue((self.config / 'opencode/AGENTS.md').is_symlink())

    def test_opencode_additional_layers_are_reported_without_their_contents(self):
        self.local(['opencode'])
        self.env['OPENCODE_CONFIG_CONTENT'] = '{"mcp":{"private":"sensitive-value"}}'
        result = self.run_apply()
        self.assertIn('OPENCODE_CONFIG_CONTENT', result.stdout)
        self.assertNotIn('sensitive-value', result.stdout + result.stderr)

    def test_opencode_rejects_malformed_jsonc_without_writing_instructions(self):
        self.local(['opencode'])
        for invalid in ('{"mcp": {/* unfinished}', '{"mcp": {}, "mcp": {}}',
                        '{"mcp": 123}', '{"mcp": {"x": 1} garbage}', '{"x": NaN}'):
            with self.subTest(invalid=invalid):
                path = self.opencode_config(invalid, 'opencode.jsonc')
                self.run_apply(success=False)
                self.assertEqual(path.read_text(), invalid)
                self.assertFalse((self.config / 'opencode/AGENTS.md').exists())

    def vscode_config(self, content):
        path = self.config / 'Code/User/mcp.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def vscode_servers(self):
        spec = importlib.util.spec_from_file_location('agents_test', self.repo / 'scripts/agents.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.parse_jsonc((self.config / 'Code/User/mcp.json').read_text()).value['servers']

    def test_vscode_mcp_preserves_personal_servers_inputs_and_comments(self):
        self.local(['vscode'])
        personal = '"Google Sheets": {"type": "http", "url": "https://example.com/sheets", "oauth": {"clientId": "client",},},'
        path = self.vscode_config('''// Personal VS Code settings
{
  "inputs": [{"id": "Authorization", "type": "promptString", "password": true,},],
  "servers": {
    // Keep personal server comment
    ''' + personal + '''
    "personal": {"type": "http", "url": "https://example.com/mcp", "headers": {"Authorization": "${input:Authorization}"},},
  },
}
''')
        self.run_apply()
        for preserved in ('// Personal VS Code settings', '"inputs": [{"id": "Authorization"',
                          '// Keep personal server comment', personal, '"Authorization": "${input:Authorization}"'):
            self.assertIn(preserved, path.read_text())
        servers = self.vscode_servers()
        self.assertEqual(servers['context7'], {'type': 'http', 'url': 'https://mcp.context7.com/mcp'})
        before = path.read_bytes()
        self.run_apply()
        self.assertEqual(before, path.read_bytes())
        self.local([])
        self.run_apply()
        self.assertEqual(set(self.vscode_servers()), {'personal', 'Google Sheets'})
        for preserved in ('// Personal VS Code settings', '// Keep personal server comment', personal):
            self.assertIn(preserved, path.read_text())
        self.assertNotIn('context7', path.read_text())

    def test_vscode_uses_environment_references_for_secrets(self):
        self.local(['vscode'])
        path, data = self.servers()
        data['servers']['private'] = {'transport': 'http', 'url': 'https://example.com/mcp',
                                      'header_env': {'X-API-Key': 'PRIVATE_MCP_KEY'}}
        data['servers']['localTool'] = {'transport': 'stdio', 'command': 'my-mcp-server',
                                        'env_vars': ['PRIVATE_MCP_KEY']}
        path.write_text(json.dumps(data))
        self.env['PRIVATE_MCP_KEY'] = 'secret-value-only-in-the-process'
        self.run_apply()
        servers = self.vscode_servers()
        self.assertEqual(servers['localTool'], {'type': 'stdio', 'command': 'my-mcp-server', 'args': [],
                                                'env': {'PRIVATE_MCP_KEY': '${env:PRIVATE_MCP_KEY}'}})
        self.assertEqual(servers['private'], {'type': 'http', 'url': 'https://example.com/mcp',
                                              'headers': {'X-API-Key': '${env:PRIVATE_MCP_KEY}'}})
        for base in (self.home, self.state, self.config):
            for file in base.rglob('*'):
                if file.is_file():
                    self.assertNotIn(self.env['PRIVATE_MCP_KEY'].encode(), file.read_bytes())

    def test_vscode_creates_configuration_with_manual_instruction_notice(self):
        self.local(['vscode'])
        result = self.run_apply()
        self.assertIn('VS Code: for the Local harness', result.stdout)
        self.assertNotIn('Cursor:', result.stdout)
        self.assertFalse((self.config / 'Code/User/AGENTS.md').exists())
        self.assertFalse((self.home / '.cursor/mcp.json').exists())
        self.assertEqual((self.home / '.agents/skills').resolve(), self.repo / 'skills')
        self.assertEqual(set(self.vscode_servers()), {'context7', 'figma', 'google-sheets-official'})

    def test_native_skills_link_from_another_home_is_stable(self):
        self.local(['vscode'])
        self.env['HOME'] = str(self.base / 'other-home')
        self.run_apply()
        link = self.base / 'other-home/.agents/skills'
        self.assertEqual(link.resolve(), self.repo / 'skills')
        before = link.lstat().st_mtime_ns
        self.run_apply()
        self.assertEqual(before, link.lstat().st_mtime_ns)
        self.assertTrue(link.is_symlink())
        self.run_apply(action='doctor')

    def test_entry_already_removed_by_hand_does_not_block_its_removal(self):
        self.local(['vscode'])
        servers_path, shared = self.servers()
        shared['servers']['openaiDeveloperDocs']['harnesses'] = ['vscode']
        servers_path.write_text(json.dumps(shared))
        self.run_apply()
        path = self.config / 'Code/User/mcp.json'
        data = json.loads(path.read_text())
        del data['servers']['openaiDeveloperDocs']
        path.write_text(json.dumps(data))
        shared['servers']['openaiDeveloperDocs']['harnesses'] = ['codex']
        servers_path.write_text(json.dumps(shared))
        self.run_apply()
        self.assertEqual(set(self.vscode_servers()), {'context7', 'figma', 'google-sheets-official'})

    def test_narrowing_server_harnesses_removes_only_managed_entries_elsewhere(self):
        self.write('.claude.json', '{"mcpServers": {"personal": {"command": "custom"}}}')
        self.run_apply()
        path, data = self.servers()
        data['servers']['openaiDeveloperDocs']['harnesses'] = ['codex']
        path.write_text(json.dumps(data))
        self.run_apply()
        claude = json.loads((self.home / '.claude.json').read_text())['mcpServers']
        self.assertEqual(set(claude), {'personal', 'context7', 'figma', 'google-sheets-official'})
        self.assertNotIn('openaiDeveloperDocs', json.loads((self.home / '.cursor/mcp.json').read_text())['mcpServers'])
        self.assertNotIn('openaiDeveloperDocs', json.loads((self.config / 'opencode/opencode.json').read_text())['mcp']['servers'])
        self.assertNotIn('openaiDeveloperDocs', self.vscode_servers())
        codex = tomllib.loads((self.home / '.codex/config.toml').read_text())['mcp_servers']
        self.assertEqual(codex['openaiDeveloperDocs'], {'url': 'https://developers.openai.com/mcp'})

    def test_vscode_agent_plugins_are_not_read_or_modified(self):
        plugins = self.write('.vscode/agent-plugins/installed.json', '{"plugin": true}')
        self.local(['vscode'])
        self.run_apply()
        self.assertEqual(plugins.read_text(), '{"plugin": true}')
        self.assertFalse((self.home / '.vscode/skills').exists())
        self.assertFalse(any(p.is_symlink() for p in (self.home / '.vscode').rglob('*')))

    def test_vscode_name_collision_prevents_all_configuration_writes(self):
        self.local(['codex', 'vscode'])
        path = self.vscode_config('{"servers": {"context7": {"type": "http", "url": "https://personal.example/mcp"}}}')
        before = path.read_bytes()
        result = self.run_apply(success=False)
        self.assertIn('VS Code: MCP name collision', result.stderr)
        self.assertEqual(before, path.read_bytes())
        self.assertFalse((self.home / '.codex/config.toml').exists())

    def test_vscode_detects_managed_edits_before_any_writes(self):
        self.local(['vscode'])
        self.run_apply()
        path = self.config / 'Code/User/mcp.json'
        path.write_text(path.read_text().replace('https://mcp.context7.com/mcp', 'https://hand-edited.example/mcp'))
        before = path.read_bytes()
        self.run_apply(success=False)
        self.assertEqual(before, path.read_bytes())

    def test_vscode_rejects_malformed_jsonc_without_writing_other_harnesses(self):
        self.local(['codex', 'vscode'])
        cases = (('{"servers": {/* unfinished}', 'JSONC'),
                 ('{"servers": 123}', 'VS Code: servers must be an object'),
                 ('{"servers": {}, "servers": {}}', 'JSONC'))
        for invalid, message in cases:
            with self.subTest(invalid=invalid):
                path = self.vscode_config(invalid)
                result = self.run_apply(success=False)
                self.assertIn(message, result.stderr)
                self.assertEqual(path.read_text(), invalid)
                self.assertFalse((self.home / '.codex/config.toml').exists())

    def test_vscode_removal_keeps_personal_servers_only(self):
        self.local(['vscode'])
        path = self.vscode_config('{"servers":{"personal":{"type":"stdio","command":"custom"}}}')
        self.run_apply()
        self.local([])
        self.run_apply()
        self.assertEqual(json.loads(path.read_text()), {'servers': {'personal': {'type': 'stdio', 'command': 'custom'}}})

    def test_removing_last_managed_server_preserves_personal_inline_comment(self):
        self.local(['vscode'])
        registry, _ = self.servers()
        probe = {'type': 'http', 'url': 'https://example.com/probe'}
        registry.write_text(json.dumps({'version': 1, 'servers': {
            'probe': {'transport': 'http', 'url': probe['url']}}}))
        self.run_apply()
        personal = '"personal": {"type":"stdio","command":"custom"}'
        path = self.vscode_config('{"servers": {' + personal + ', // Personal server note\n'
                                  '"probe": ' + json.dumps(probe) + '}}')
        self.local([])
        self.run_apply()
        self.assertIn(personal + ' // Personal server note', path.read_text())
        self.assertNotIn('"probe"', path.read_text())

    def test_jsonc_rejects_non_json_whitespace_without_writing_configuration(self):
        self.local(['vscode'])
        for whitespace in ('\u00a0', '\v', '\x1f'):
            with self.subTest(whitespace=repr(whitespace)):
                original = '{"servers": {},' + whitespace + '"personal": 1}'
                path = self.vscode_config(original)
                self.run_apply(success=False)
                self.assertEqual(path.read_text(), original)
                self.assertFalse((self.state / 'agents/managed.json').exists())

    def test_vscode_autodetection_uses_xdg_directory(self):
        (self.config / 'Code/User').mkdir(parents=True)
        (self.config / 'agents/local.json').write_text('{}')
        # Exclude the actual harness binaries installed on the test host.
        self.env['PATH'] = ''
        result = subprocess.run([shutil.which('python3'), str(self.repo / 'scripts/agents.py'), 'apply'],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Harnesses: vscode', result.stdout)
        self.assertIn('context7', (self.config / 'Code/User/mcp.json').read_text())


if __name__ == '__main__':
    unittest.main()
