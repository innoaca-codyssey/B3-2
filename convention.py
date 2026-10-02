from dataclasses import dataclass, asdict
import json
from pathlib import Path
import re


@dataclass(frozen=True)
class Convention:
    commit_prefixes: tuple[str, ...] = ('feat', 'fix', 'docs', 'refactor', 'test', 'chore')
    commit_title_limit: int = 50
    pr_title_limit: int = 64
    pr_title_prefix: str = ''
    tone: str = 'concise'

    def rules(self):
        return asdict(self)


def load(path):
    file = Path(path)
    if file.stat().st_size > 16384:
        raise ValueError('컨벤션 파일은 16KiB 이내로 작성하세요')
    data = json.loads(file.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or set(data) - set(Convention.__dataclass_fields__):
        raise ValueError('알 수 없는 컨벤션 필드입니다')
    rules = dict(Convention().rules(), **data)
    for field, maximum in [('commit_title_limit', 72), ('pr_title_limit', 80)]:
        value = rules[field]
        if type(value) is not int or not 10 <= value <= maximum:
            raise ValueError(f'{field}는 10~{maximum} 정수여야 합니다')
    prefixes = rules['commit_prefixes']
    if not isinstance(prefixes, (list, tuple)) or not 1 <= len(prefixes) <= 12 or any(not isinstance(p, str) or not re.fullmatch(r'[a-z]{2,16}', p) for p in prefixes):
        raise ValueError('commit_prefixes는 2~16자 소문자 prefix 목록입니다')
    if any(len(prefix) + 3 > rules['commit_title_limit'] for prefix in prefixes):
        raise ValueError('제목 제한에 prefix와 변경 내용이 들어갈 공간이 필요합니다')
    rules['commit_prefixes'] = tuple(prefixes)
    prefix = rules['pr_title_prefix']
    if not isinstance(prefix, str) or len(prefix) >= rules['pr_title_limit'] - 8 or any(ord(c)<32 or ord(c)==127 for c in prefix):
        raise ValueError('PR 제목 prefix 길이나 제어문자를 확인하세요')
    if rules['tone'] not in ('concise', 'formal'):
        raise ValueError('tone은 concise 또는 formal을 사용하세요')
    return Convention(**rules)
