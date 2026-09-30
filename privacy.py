from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import Callable
from changes import Change


def sensitive_path(path: str) -> bool:
    parts = PurePosixPath(path.lower()).parts
    name = parts[-1] if parts else ''
    return (
        name == '.env' or name.startswith('.env.')
        or name.endswith(('.pem', '.key'))
        or name in ('credentials', 'credentials.json', '.git-credentials', 'id_rsa', 'id_ed25519', 'secrets.json')
        or any(part in ('.aws', '.ssh') for part in parts)
    )


def redact(text: str, known_secret: str = '') -> tuple[str, int]:
    """알려진 키와 토큰, 이메일, 개인키를 마스킹합니다."""
    count = 0
    if known_secret and known_secret in text:
        count += text.count(known_secret)
        text = text.replace(known_secret, '[REDACTED]')
    patterns = [
        (r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)', '[REDACTED PRIVATE KEY]'),
        (r'\b(?:pickle-|sk-|ghp_|github_pat_)[A-Za-z0-9_-]{12,}', '[REDACTED TOKEN]'),
        (r'\bAKIA[A-Z0-9]{16}\b', '[REDACTED AWS KEY]'),
        (r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}', '[REDACTED EMAIL]'),
        (r'''(?i)(\b(?:api[_-]?key|access[_-]?token|password|secret)\b\s*[:=]\s*["']?)([^\s,"';]+)''', r'\1[REDACTED]'),
    ]
    for pattern, replacement in patterns:
        text, matches = re.subn(pattern, replacement, text)
        count += matches
    return text, count


@dataclass
class Prepared:
    files: list[dict]
    excluded: int
    redactions: int
    omitted_lines: int


def prepare(changes: list[Change], load_diff: Callable[[Change], str], safe: bool, max_files: int, max_lines: int, known_secret: str = '') -> Prepared:
    files = []
    excluded = redactions = omitted = used_lines = 0
    for change in changes:
        if safe and (sensitive_path(change.path) or change.previous and sensitive_path(change.previous)):
            excluded += 1
            continue
        if safe and len(files) >= max_files:
            excluded += 1
            continue
        diff = load_diff(change)
        path, previous = change.path, change.previous
        if safe:
            diff, n = redact(diff, known_secret)
            path, p = redact(path, known_secret)
            previous, q = redact(previous or '', known_secret)
            redactions += n + p + q
            lines = diff.splitlines(keepends=True)
            available = max(0, max_lines - used_lines)
            omitted += max(0, len(lines) - available)
            diff = ''.join(lines[:available])
            used_lines += min(len(lines), available)
        if diff.strip():
            files.append({'status': change.status, 'path': path, 'previous_path': previous, 'diff': diff})
    return Prepared(files, excluded, redactions, omitted)
