from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from changes import GitChanges
from client import APIError, ChatClient
from drafts import FormatError, generate, parse, prompt
from privacy import prepare, redact


ROOT = Path(__file__).resolve().parent.parent


@contextmanager
def server(responses):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requests.append((self.path, body))
            response = responses[min(len(requests) - 1, len(responses) - 1)]
            status = response.get('status', 200)
            self.send_response(status)
            if status == 302:
                self.send_header('Location', '/redirect-target')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            if 'raw' in response:
                output = response['raw'].encode()
            else:
                output = json.dumps({'choices': [{'message': {'content': response.get('text', '')}, 'finish_reason': response.get('finish_reason', 'stop')}], 'usage': {'prompt_tokens': 30, 'completion_tokens': 40}}).encode()
            self.wfile.write(output)
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{httpd.server_port}/v1', requests
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


class GitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.com')
        (self.path / 'app.py').write_text('value = 1\n')
        self.git('add', 'app.py')
        self.git('commit', '-m', 'initial')
        self.repository = GitChanges(self.path)

    def tearDown(self):
        self.temporary.cleanup()

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.path, check=True, capture_output=True)

    def cli(self, *args, key='unit-token'):
        environment = dict(os.environ, AI_API_KEY=key)
        return subprocess.run([sys.executable, str(ROOT / 'main.py'), *args], cwd=self.path, env=environment, capture_output=True, text=True)

    def test_staged_unstaged_and_untracked_content(self):
        (self.path / 'app.py').write_text('value = 2\n')
        self.git('add', 'app.py')
        (self.path / 'app.py').write_text('value = 3\n')
        (self.path / 'new file.py').write_text('added = True\n')
        changes = self.repository.scan()
        self.assertEqual(len(changes), 2)
        content = '\n'.join(self.repository.diff(change) for change in changes)
        self.assertIn('+value = 2', content)
        self.assertIn('+value = 3', content)
        self.assertIn('+added = True', content)

    def test_rename_and_unicode_path(self):
        self.git('mv', 'app.py', '새 파일.py')
        change = self.repository.scan()[0]
        self.assertEqual(change.path, '새 파일.py')
        self.assertEqual(change.previous, 'app.py')
        self.assertIn('rename to', self.repository.diff(change))

    def test_clean_missing_key_and_root_requirement(self):
        clean = self.cli('commit')
        self.assertEqual(clean.returncode, 0)
        self.assertIn('변경 사항이 없습니다', clean.stdout)
        self.assertIn('요청 횟수: 0', clean.stdout)
        missing = self.cli('commit', key='')
        self.assertEqual(missing.returncode, 1)
        self.assertIn('AI_API_KEY', missing.stdout)
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaises(ValueError):
                GitChanges(Path(other))

    def test_safe_mode_excludes_before_reading_and_limits_lines(self):
        (self.path / '.env').write_text('secret=hidden\n')
        (self.path / 'large.py').write_text('item = 1\n' * 300)
        (self.path / 'app.py').write_text('value = 9\n')
        loaded = []
        def loader(change):
            loaded.append(change.path)
            return self.repository.diff(change)
        output = prepare(self.repository.scan(), loader, True, 10, 20)
        self.assertNotIn('.env', loaded)
        self.assertEqual(output.excluded, 1)
        self.assertLessEqual(sum(len(f['diff'].splitlines()) for f in output.files), 20)
        self.assertGreater(output.omitted_lines, 0)

    def test_safe_mode_file_limit(self):
        for name in ['a.txt', 'b.txt', 'c.txt']:
            (self.path / name).write_text('new\n')
        output = prepare(self.repository.scan(), self.repository.diff, True, 2, 200)
        self.assertEqual(len(output.files), 2)
        self.assertEqual(output.excluded, 1)

    def test_cli_parameters_and_pr_structure(self):
        (self.path / 'app.py').write_text('value = 2\n')
        text = json.dumps({'title': '값 갱신', 'why': ['새 값 필요'], 'what': ['app.py 수정'], 'tests': ['값 확인']})
        with server([{'text': text}]) as (url, requests):
            result = self.cli('pr', '--base-url', url, '--model', 'pickle-general', '--temperature', '0.7', '--max-tokens', '500', '--safe-mode')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0][0], '/v1/chat/completions')
        self.assertEqual(requests[0][1]['model'], 'pickle-general')
        self.assertEqual(requests[0][1]['temperature'], 0.7)
        self.assertEqual(requests[0][1]['max_tokens'], 500)
        for name in ['Why', 'What', 'How to Test']:
            self.assertIn('## ' + name, result.stdout)

    def test_cli_argument_errors_no_traceback(self):
        for options in [['--temperature', 'nan'], ['--temperature', '3'], ['--max-tokens', '0'], ['--timeout', '-1']]:
            result = self.cli('commit', *options)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stdout + result.stderr)


class PrivacyTests(unittest.TestCase):
    def test_tokens_email_assignments_and_partial_private_key(self):
        content = 'pickle-0123456789abcdefghijklmnop test@example.com API_KEY="abcdef"\n-----BEGIN RSA PRIVATE KEY-----\nabc123\n'
        output, count = redact(content)
        for raw in ['pickle-0123456789abcdefghijklmnop', 'test@example.com', 'abcdef', 'abc123']:
            self.assertNotIn(raw, output)
        self.assertGreaterEqual(count, 4)


class FormatTests(unittest.TestCase):
    def test_title_cap_and_fenced_json(self):
        draft = parse('```json\n' + json.dumps({'title': '가' * 100, 'body': ['app.py 수정']}) + '\n```', 'commit')
        self.assertEqual(len(draft.title), 72)
        self.assertEqual(draft.title_before, 100)
        self.assertIn('- app.py 수정', draft.render('commit'))
        pr = parse(json.dumps({'title': '나' * 100, 'why': ['이유'], 'what': ['변경'], 'tests': ['검사']}), 'pr')
        self.assertEqual(len(pr.title), 80)

    def test_invalid_json_missing_section_and_empty_bullet(self):
        for text in ['not JSON', '{}', '[]', json.dumps({'title': 'a', 'why': [], 'what': ['a'], 'tests': ['a']}), json.dumps({'title': 'a', 'why': ['- '], 'what': ['a'], 'tests': ['a']})]:
            with self.assertRaises(FormatError):
                parse(text, 'pr')

    def test_regeneration_once_and_no_third_call(self):
        good = json.dumps({'title': 'fix: 값 수정', 'body': ['app.py 수정']})
        with server([{'text': 'invalid'}, {'text': good}]) as (url, requests):
            client = ChatClient(url, 'pickle-general', 'unit-token', 0.2, 500, 2)
            draft, usage = generate(client, [{'role': 'user', 'content': 'change'}], 'commit')
            self.assertEqual(len(requests), 2)
            self.assertIn('수정', draft.title)
        with server([{'text': 'invalid'}]) as (url, requests):
            client = ChatClient(url, 'pickle-general', 'unit-token', 0.2, 500, 2)
            with self.assertRaises(FormatError):
                generate(client, [{'role': 'user', 'content': 'change'}], 'commit')
            self.assertEqual(len(requests), 2)

    def test_http_failure_invalid_response_and_redirect(self):
        for response in [{'status': 401, 'raw': '{"error":"bad token"}'}, {'raw': 'broken'}, {'text': ''}, {'status': 302}]:
            with server([response]) as (url, requests):
                client = ChatClient(url, 'pickle-general', 'unit-token', 0.2, 500, 2)
                with self.assertRaises(APIError):
                    client.complete([{'role': 'user', 'content': 'change'}])
                self.assertEqual(len(requests), 1)


if __name__ == '__main__':
    unittest.main()
