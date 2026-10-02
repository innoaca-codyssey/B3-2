from pathlib import Path
import subprocess
import tempfile
import unittest
from changes import GitChanges


class BaseDiffTests(unittest.TestCase):
    def test_committed_changes_rename_and_untracked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def git(*args):
                return subprocess.run(['git', *args], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()
            git('init', '-b', 'main'); git('config', 'user.name', 'Tester'); git('config', 'user.email', 'test@example.com')
            (root/'old.txt').write_text('base\n' * 20)
            git('add', '.'); git('commit', '-m', 'base')
            ref = git('rev-parse', 'HEAD')
            git('mv', 'old.txt', 'new.txt')
            with (root/'new.txt').open('a') as file: file.write('committed change\n')
            git('commit', '-am', 'change')
            (root/'extra.txt').write_text('untracked\n')
            repository = GitChanges(root, ref)
            changes = repository.scan()
            self.assertEqual(len(changes), 2)
            tracked = next(c for c in changes if c.path == 'new.txt')
            self.assertEqual(tracked.previous, 'old.txt')
            self.assertIn('+committed change', repository.diff(tracked))
            extra = next(c for c in changes if c.path == 'extra.txt')
            self.assertIn('+untracked', repository.diff(extra))
            self.assertEqual([c.path for c in GitChanges(root).scan()], ['extra.txt'])

    def test_invalid_ref_is_not_a_git_option(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root/'.git').mkdir()
            for ref in ['--output=outside', 'main\nHEAD']:
                with self.assertRaises(ValueError): GitChanges(root, ref)
