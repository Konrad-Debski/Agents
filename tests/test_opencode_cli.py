"""Optional schema check using an installed OpenCode 2 private process."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import test_apply


class OpenCodeCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = shutil.which('opencode')
        if not cls.binary:
            raise unittest.SkipTest('OpenCode is not installed')
        result = subprocess.run([cls.binary, '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode or not re.search(r'\bv?2\.', result.stdout):
            raise unittest.SkipTest('Private-process validation requires OpenCode 2')

    def setUp(self):
        self.fixture = test_apply.ApplyTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.local(['opencode'])
        path, data = self.fixture.servers()
        data['servers']['probe'] = {'transport': 'http', 'url': 'https://example.com/probe'}
        path.write_text(json.dumps(data))

    def validate(self, legacy=False, jsonc=False):
        fixture = self.fixture
        if legacy:
            fixture.opencode_config('{"mcp":{"personal":{"type":"remote","url":"https://example.com/personal","enabled":false}}}')
        elif jsonc:
            fixture.opencode_config('// Keep this comment\n{"mcp":{"timeout":{"startup":10000},"servers":{}}}', 'opencode.jsonc')
        fixture.run_apply()
        filename = 'opencode.jsonc' if jsonc else 'opencode.json'
        path = fixture.config / 'opencode' / filename
        # Disable connections in the disposable config; validate without a model or live MCP.
        if jsonc:
            # Generated entries retain the JSONC header; inserting a v2 disabled flag is valid.
            text = path.read_text().replace('"type": "remote",', '"type": "remote", "disabled": true,')
            text = text.replace('"type": "local",', '"type": "local", "disabled": true,')
            path.write_text(text)
        else:
            config = json.loads(path.read_text())
            servers = config['mcp'] if legacy else config['mcp']['servers']
            for server in servers.values():
                server['enabled' if legacy else 'disabled'] = legacy is False
            path.write_text(json.dumps(config))
        env = dict(fixture.env, XDG_DATA_HOME=str(fixture.base / 'data'),
                   XDG_CACHE_HOME=str(fixture.base / 'cache'))
        result = subprocess.run([self.binary, 'debug', 'config', '--standalone'],
                                cwd=fixture.home, env=env, capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stderr)
        documents = [entry for entry in json.loads(result.stdout) if entry.get('type') == 'document']
        document = next(entry for entry in documents if Path(entry['path']) == path)
        servers = document['info']['mcp']['servers']
        self.assertEqual(servers['context7']['command'], ['npx', '-y', '@upstash/context7-mcp'])
        self.assertEqual(servers['probe']['type'], 'remote')
        self.assertTrue(all(server['disabled'] for server in servers.values()))
        if legacy:
            self.assertIn('personal', servers)
        if jsonc:
            self.assertEqual(document['info']['mcp']['timeout']['startup'], 10000)
            self.assertTrue(path.read_text().startswith('// Keep this comment'))

    def test_native_v2_config_is_accepted_by_opencode(self):
        self.validate()

    def test_jsonc_v2_config_is_accepted_by_opencode(self):
        self.validate(jsonc=True)

    def test_preserved_v1_config_is_accepted_by_opencode(self):
        self.validate(legacy=True)


if __name__ == '__main__':
    unittest.main()
