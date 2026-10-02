from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass
class Change:
    status: str
    path: str
    previous: str | None = None


class GitChanges:
    """status와 diff만 실행해 작업 트리와 인덱스 변경을 수집합니다."""
    def __init__(self, directory: Path, diff_base: str | None = None):
        self.directory = directory.resolve()
        if diff_base and (diff_base.startswith('-') or any(ord(c) < 32 for c in diff_base)):
            raise ValueError('비교 기준 ref 형식을 확인하세요')
        self.diff_base = diff_base
        if not (self.directory / '.git').exists():
            raise ValueError('Git 저장소 루트에서 실행하세요')

    def _git(self, arguments: list[str], allowed=(0,)) -> str:
        result = subprocess.run(['git', *arguments], cwd=self.directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode not in allowed:
            detail = result.stderr.decode('utf-8', errors='replace').strip()
            raise ValueError('Git 명령 실패: ' + detail)
        return result.stdout.decode('utf-8', errors='replace')

    def scan(self) -> list[Change]:
        entries = self._git(['status', '--porcelain=v1', '-z', '--untracked-files=all']).split('\0')
        changes = []
        index = 0
        while index < len(entries) and entries[index]:
            entry = entries[index]
            status, path = entry[:2], entry[3:]
            index += 1
            previous = None
            if 'R' in status or 'C' in status:
                previous = entries[index]
                index += 1
            changes.append(Change(status, path, previous))
        if self.diff_base:
            tokens = self._git(['diff', '--name-status', '-z', '--no-ext-diff', '--no-textconv', self.diff_base, '--']).split('\0')
            tracked = []
            index = 0
            while index < len(tokens) and tokens[index]:
                status, path = tokens[index:index+2]
                index += 2
                previous = None
                if status[0] in ('R', 'C'):
                    previous, path = path, tokens[index]
                    index += 1
                tracked.append(Change(status[0] + ' ', path, previous))
            changes = tracked + [change for change in changes if change.status == '??']
        return changes

    def diff(self, change: Change) -> str:
        options = ['--no-color', '--no-ext-diff', '--no-textconv']
        if change.status == '??':
            return self._git(['diff', '--no-index', *options, '--', '/dev/null', change.path], allowed=(0, 1))
        if self.diff_base:
            paths = [change.path] + ([change.previous] if change.previous else [])
            return self._git(['diff', *options, self.diff_base, '--', *paths])
        paths = [change.path] + ([change.previous] if change.previous else [])
        staged = self._git(['diff', '--cached', *options, '--', *paths])
        unstaged = self._git(['diff', *options, '--', *paths])
        return staged + unstaged
