import argparse
import math
import os
from pathlib import Path
from changes import GitChanges
from convention import load
from client import APIError, ChatClient
from drafts import FormatError, generate, prompt
from privacy import prepare, redact


def positive(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('양수 정수를 입력하세요')
    return number


def temperature(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 2:
        raise argparse.ArgumentTypeError('temperature는 0~2를 사용하세요')
    return number


def timeout(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('timeout은 양수 초를 사용하세요')
    return number


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description='Git 변경으로 커밋 메시지와 PR 초안을 생성합니다')
    commands = root.add_subparsers(dest='command', required=True)
    for name in ['commit', 'pr']:
        p = commands.add_parser(name)
        p.add_argument('--base-url', default=os.getenv('AI_BASE_URL', 'https://llm.pcl.kr/v1'))
        p.add_argument('--model', default=os.getenv('AI_MODEL', 'pickle-general'))
        p.add_argument('--temperature', type=temperature, default=0.2)
        p.add_argument('--max-tokens', type=positive, default=1200)
        p.add_argument('--timeout', type=timeout, default=60)
        p.add_argument('--safe-mode', action='store_true')
        p.add_argument('--max-files', type=positive, default=10)
        p.add_argument('--max-lines', type=positive, default=200)
        p.add_argument('--context', default='추가 배경 없음')
        p.add_argument('--convention', help='JSON 컨벤션 설정 파일')
        p.add_argument('--diff-base', help='브랜치의 커밋된 변경까지 비교할 기준 ref')
    return root


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    key = os.getenv('AI_API_KEY', '')
    client = None
    try:
        convention = load(args.convention) if args.convention else None
        repository = GitChanges(Path.cwd(), args.diff_base)
        if not key.strip():
            raise ValueError('AI_API_KEY가 없습니다. 환경변수를 설정하세요')
        client = ChatClient(args.base_url, args.model, key, args.temperature, args.max_tokens, args.timeout)
        changes = repository.scan()
        if not changes:
            print('[INFO] 변경 사항이 없습니다')
            print('[INFO] API 요청 횟수: 0')
            return 0
        label = 'Git comparison' if args.diff_base else 'Git status'
        print(f'[INFO] {label}: {len(changes)}개 파일 변경')
        prepared = prepare(changes, repository.diff, args.safe_mode, args.max_files, args.max_lines, key)
        print(f'[INFO] 전송 파일: {len(prepared.files)}, 제외: {prepared.excluded}, 마스킹: {prepared.redactions}, 생략 행: {prepared.omitted_lines}')
        if not prepared.files:
            print('[INFO] 전송할 diff가 없습니다. 안전 모드의 제외 경로나 Git 변경을 확인하세요')
            print('[INFO] API 요청 횟수: 0')
            return 0
        context = redact(args.context, key)[0] if args.safe_mode else args.context
        print(f'[INFO] model={args.model} temperature={args.temperature} max_tokens={args.max_tokens}')
        draft, usage = generate(client, prompt(args.command, prepared, context, convention), args.command, convention)
        if draft.title_before != len(draft.title):
            print(f'[INFO] 제목 길이 조정: {draft.title_before} -> {len(draft.title)}')
        if args.command == 'commit' and len(draft.title) > 50:
            print('[INFO] 커밋 제목이 권장 길이 50자를 넘습니다. 검토 후 다듬으세요')
        print(f'[INFO] API 요청 횟수: {client.calls}')
        if usage:
            print(f'[INFO] tokens: prompt={usage.get("prompt_tokens", "unknown")} completion={usage.get("completion_tokens", "unknown")}')
        print('[DONE] 형식 검증 완료')
        print(draft.render(args.command))
        return 0
    except (ValueError, APIError, FormatError, OSError) as error:
        message = redact(str(error), key)[0]
        print('[ERROR] ' + message)
        print('[힌트] 저장소 루트, API 환경변수, URL/모델, 입력 옵션을 확인하세요')
        print(f'[INFO] API 요청 횟수: {client.calls if client else 0}')
        return 1
    except KeyboardInterrupt:
        print('\n[ERROR] 실행을 취소했습니다')
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
