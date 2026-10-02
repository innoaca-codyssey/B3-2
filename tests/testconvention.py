import json
from pathlib import Path
import tempfile
import unittest
from client import Completion
from convention import load
from drafts import FormatError, generate, parse, prompt
from privacy import Prepared


class ConventionTests(unittest.TestCase):
    def load_rules(self, values):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'rules.json'
            path.write_text(json.dumps(values))
            return load(path)

    def test_output_constraints_and_default_compatibility(self):
        rules = self.load_rules({'pr_title_prefix': '[B6-3]', 'commit_title_limit': 20})
        raw = json.dumps({'title': 'feat: ' + '가' * 80, 'body': ['변경']})
        self.assertEqual(len(parse(raw, 'commit', rules).title), 20)
        self.assertEqual(len(parse(raw, 'commit').title), 72)
        draft = parse(json.dumps({'title': '검색 추가', 'why': ['필요'], 'what': ['구현'], 'tests': ['검사']}), 'pr', rules)
        self.assertEqual(draft.title, '[B6-3] 검색 추가')
        self.assertEqual([heading for heading, _ in draft.sections], ['Why', 'What', 'How to Test'])

    def test_bad_configuration_before_network(self):
        for values in [{'unknown': 'x'}, {'commit_title_limit': True}, {'pr_title_limit': 81}, {'commit_prefixes': ['bad:']}, {'pr_title_prefix': 'a\nb'}, {'tone': 'unknown'}, {'commit_prefixes': ['abcdefghijklmnop'], 'commit_title_limit': 10}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.load_rules(values)

    def test_convention_repair_is_bounded(self):
        rules = self.load_rules({'commit_prefixes': ['feat']})
        class Stub:
            calls = 0
            def complete(self, messages):
                self.calls += 1
                prefix = 'fix' if self.calls == 1 else 'feat'
                return Completion(json.dumps({'title': prefix + ': 검색 구현', 'body': []}), 'stop', {})
        client = Stub()
        prepared = Prepared([], 0, 0, 0)
        messages = prompt('commit', prepared, '검사', rules)
        self.assertIn('commit_prefixes', messages[0]['content'])
        draft, _ = generate(client, messages, 'commit', rules)
        self.assertEqual(client.calls, 2)
        self.assertTrue(draft.title.startswith('feat:'))
        with self.assertRaises(FormatError):
            parse('{"title":"fix: 변경","body":[]}', 'commit', rules)
