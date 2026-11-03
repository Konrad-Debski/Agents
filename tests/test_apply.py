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
        self.local(['codex', 'claude-code', 'cursor'])

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
        before = {p: p.stat().st_mtime_ns for p in self.home.rglob('*') if p.is_file()}
        state_before = (self.state / 'agents/managed.json').stat().st_mtime_ns
        self.run_apply()
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in before})
        self.assertEqual(state_before, (self.state / 'agents/managed.json').stat().st_mtime_ns)
        for path in (self.state / 'agents/backups').rglob('*'):
            if path.is_file():
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_name_collision_prevents_all_configuration_writes(self):
        self.write('.cursor/mcp.json', '{"mcpServers":{"context7":{"url":"https://personal.example/mcp"}}}')
        self.run_apply(success=False)
        self.assertFalse((self.home / '.codex/AGENTS.md').exists())
        self.assertFalse((self.home / '.claude.json').exists())

    def test_existing_instructions_are_not_overwritten(self):
        path = self.write('.codex/AGENTS.md', 'My existing instructions')
        self.run_apply(success=False)
        self.assertEqual(path.read_text(), 'My existing instructions')
        self.assertFalse(path.is_symlink())

    def test_manual_edit_of_managed_entry_is_preserved(self):
        self.run_apply()
        path = self.home / '.claude.json'
        data = json.loads(path.read_text())
        data['mcpServers']['context7']['command'] = 'hand-edited'
        path.write_text(json.dumps(data))
        before = path.read_bytes()
        self.run_apply(success=False)
        self.assertEqual(path.read_bytes(), before)

    def test_manual_edit_of_managed_toml_block_is_preserved(self):
        self.run_apply()
        path = self.home / '.codex/config.toml'
        path.write_text(path.read_text().replace('command = "npx"', 'command = "hand-edited"'))
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
        data['servers']['context7']['env_vars'] = ['PRIVATE_MCP_KEY']
        path.write_text(json.dumps(data))
        self.env['PRIVATE_MCP_KEY'] = 'secret-value-only-in-the-process'
        self.run_apply()
        codex = tomllib.loads((self.home / '.codex/config.toml').read_text())['mcp_servers']
        self.assertEqual(codex['private']['env_http_headers'], {'X-API-Key': 'PRIVATE_MCP_KEY'})
        claude = json.loads((self.home / '.claude.json').read_text())['mcpServers']
        cursor = json.loads((self.home / '.cursor/mcp.json').read_text())['mcpServers']
        self.assertEqual(claude['private']['headers'], {'X-API-Key': '${PRIVATE_MCP_KEY}'})
        self.assertEqual(cursor['context7']['env'], {'PRIVATE_MCP_KEY': '${env:PRIVATE_MCP_KEY}'})
        for base in (self.home, self.state):
            for file in base.rglob('*'):
                if file.is_file():
                    self.assertNotIn(self.env['PRIVATE_MCP_KEY'].encode(), file.read_bytes())

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

    def test_doctor_reports_missing_environment_without_exposing_values(self):
        path, data = self.servers()
        data['servers']['context7']['requires_env'] = ['MISSING_AGENT_TEST_KEY']
        path.write_text(json.dumps(data))
        self.env.pop('MISSING_AGENT_TEST_KEY', None)
        self.run_apply()
        result = self.run_apply(action='doctor', success=False)
        self.assertIn('MISSING_AGENT_TEST_KEY', result.stdout)


if __name__ == '__main__':
    unittest.main()
