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
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
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
        return changes

    def diff(self, change: Change) -> str:
        options = ['--no-color', '--no-ext-diff', '--no-textconv']
        if change.status == '??':
            return self._git(['diff', '--no-index', *options, '--', '/dev/null', change.path], allowed=(0, 1))
        paths = [change.path] + ([change.previous] if change.previous else [])
        staged = self._git(['diff', '--cached', *options, '--', *paths])
        unstaged = self._git(['diff', *options, '--', *paths])
        return staged + unstaged
