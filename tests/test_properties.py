"""Generated adapter scenarios exercised through the apply command."""
import json
import unittest

from hypothesis import given, settings, strategies as st

import test_apply


class AdapterProperties(unittest.TestCase):
    @settings(max_examples=15, deadline=None, database=None)
    @given(st.text(alphabet=st.characters(blacklist_categories=('Cs',)), max_size=40), st.booleans())
    def test_removing_managed_servers_preserves_private_json_and_inline_comments(self, argument, trailing):
        fixture = test_apply.ApplyTests()
        fixture.setUp()
        try:
            fixture.local(['vscode'])
            registry, _ = fixture.servers()
            registry.write_text(json.dumps({'version': 1, 'servers': {
                'probe': {'transport': 'http', 'url': 'https://example.com/probe'}}}))
            fixture.run_apply()
            personal = {'type': 'stdio', 'command': 'custom', 'args': [argument]}
            rendered = json.dumps(personal, ensure_ascii=True)
            probe = json.dumps({'type': 'http', 'url': 'https://example.com/probe'})
            path = fixture.vscode_config('{"servers":{"personal":' + rendered + ', // Keep private note\n'
                                         '"probe":' + probe + (',' if trailing else '') + '}}')
            fixture.local([])
            fixture.run_apply()
            result = path.read_text()
            suffix = (',' if trailing else '') + ' // Keep private note\n}}'
            self.assertEqual(result, '{"servers":{"personal":' + rendered + suffix)
            # Remove the known JSONC suffix before checking the remaining JSON independently.
            self.assertEqual(json.loads(result.removesuffix(suffix) + '}}'),
                             {'servers': {'personal': personal}})
        finally:
            fixture.doCleanups()
