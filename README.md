# B3-2: 내가 고친 코드 설명을 AI가 대신 써주는 도우미 만들기

Git의 status와 diff를 수집해 커밋 메시지와 PR 초안을 생성하는 Python CLI입니다. OpenAI 호환 Chat Completions API를 사용하고, 생성된 제목 길이와 PR의 Why/What/How to Test 구조를 검증합니다.

## 설치와 실행

Python 3.10 이상에서 표준 라이브러리만 사용합니다. Git 저장소 루트에서 실행합니다.

```bash
export AI_BASE_URL=https://llm.pcl.kr/v1
export AI_MODEL=pickle-general
export AI_API_KEY='발급받은 키'
python3 main.py commit --safe-mode
python3 main.py pr --safe-mode
```

API Key는 환경변수에서 읽습니다. 모델, temperature와 최대 출력 토큰은 명령 옵션으로 지정할 수 있습니다. 결과는 터미널에서 검토하고 복사해 사용합니다.

## 실행 환경

```bash
$ python3 --version
Python 3.14.7
$ git --version
git version 2.50.1 (Apple Git-155)
```

macOS arm64에서 실행했습니다. 추가 패키지는 설치하지 않습니다.

## API 연결 확인

```bash
GET https://llm.pcl.kr/v1/models
HTTP 200
requested_model=pickle-general
available=True
```

지정 모델을 반환하는 models 엔드포인트에 인증한 결과입니다. 생성 요청은 /chat/completions로 전송합니다.

## 변경 수집과 오류 처리 검증

```bash
$ python3 -W error::ResourceWarning -m unittest discover -s tests -v
test_http_failure_invalid_response_and_redirect (testdrafts.FormatTests.test_http_failure_invalid_response_and_redirect) ... ok
test_invalid_json_missing_section_and_empty_bullet (testdrafts.FormatTests.test_invalid_json_missing_section_and_empty_bullet) ... ok
test_regeneration_once_and_no_third_call (testdrafts.FormatTests.test_regeneration_once_and_no_third_call) ... ok
test_title_cap_and_fenced_json (testdrafts.FormatTests.test_title_cap_and_fenced_json) ... ok
test_clean_missing_key_and_root_requirement (testdrafts.GitTests.test_clean_missing_key_and_root_requirement) ... ok
test_cli_argument_errors_no_traceback (testdrafts.GitTests.test_cli_argument_errors_no_traceback) ... ok
test_cli_parameters_and_pr_structure (testdrafts.GitTests.test_cli_parameters_and_pr_structure) ... ok
test_rename_and_unicode_path (testdrafts.GitTests.test_rename_and_unicode_path) ... ok
test_safe_mode_excludes_before_reading_and_limits_lines (testdrafts.GitTests.test_safe_mode_excludes_before_reading_and_limits_lines) ... ok
test_safe_mode_file_limit (testdrafts.GitTests.test_safe_mode_file_limit) ... ok
test_staged_unstaged_and_untracked_content (testdrafts.GitTests.test_staged_unstaged_and_untracked_content) ... ok
test_tokens_email_assignments_and_partial_private_key (testdrafts.PrivacyTests.test_tokens_email_assignments_and_partial_private_key) ... ok

----------------------------------------------------------------------
Ran 12 tests in 4.975s

OK
```

단계별 diff, 비추적 파일, 이름 변경과 Unicode 경로를 검사했습니다. 안전 모드의 읽기 전 제외와 전송 제한, 제목 길이, 필수 PR 불릿, HTTP 오류와 재생성 최대 두 번을 확인했습니다.

## 실제 커밋 메시지 생성

```bash
$ set -a; source ../.env; set +a; python3 main.py commit --safe-mode
[INFO] Git status: 6개 파일 변경
[INFO] 전송 파일: 3, 제외: 0, 마스킹: 6, 생략 행: 364
[INFO] model=pickle-general temperature=0.2 max_tokens=1200
[INFO] API 요청 횟수: 1
[INFO] tokens: prompt=2516 completion=96
[DONE] 형식 검증 완료
--- Commit Message ---
feat: Git 변경 감지, API 클라이언트, 초안 생성 모듈 추가

- changes.py: Git 저장소의 상태 및 diff를 수집하는 GitChanges 클래스 구현
- client.py: LLM API와 통신하는 ChatClient 및 응답 파싱 클래스 구현
- drafts.py: 초안 데이터 모델 및 JSON 파싱/렌더링 유틸리티 구현
```

이번에 작성한 소스 변경에서 생성한 결과입니다. 200행 제한으로 일부 파일만 전송되었으므로 메시지는 해당 입력에서 확인된 모듈을 요약합니다. 입력이 생략되면 전체 변경을 대표하는지 추가로 검토해야 합니다.

## 실제 PR 초안 생성

```bash
$ python3 /Users/yejun/GitHub/Codyssey/B3/B3-2/submission/main.py pr --safe-mode --max-tokens 600 --context '빈 목록의 평균 계산에서 0으로 나누는 오류를 방지합니다'
[INFO] Git status: 1개 파일 변경
[INFO] 전송 파일: 1, 제외: 0, 마스킹: 0, 생략 행: 0
[INFO] model=pickle-general temperature=0.2 max_tokens=600
[INFO] API 요청 횟수: 1
[INFO] tokens: prompt=322 completion=129
[DONE] 형식 검증 완료
--- PR Title ---
fix: 빈 리스트 평균 계산 시 0으로 나누기 오류 방지

--- PR Body ---

## Why
- 빈 리스트의 합을 0으로 나누면 ZeroDivisionError가 발생함

## What
- average 함수에 빈 리스트 체크 로직 추가
- 빈 리스트일 경우 0을 반환하도록 수정

## How to Test
- python -c "from average import average; print(average([]))"
- python -c "from average import average; print(average([1, 2, 3]))"
```

빈 목록에서 평균을 계산할 때 0으로 나누던 예제 변경을 입력으로 사용했습니다. PR 제목과 Why/What/How to Test에 각각 불릿이 있는 구조를 한 번의 호출로 생성했습니다.

## 제안한 검사 실행

```bash
$ cat average.py
def average(values):
    if not values:
        return 0
    return sum(values) / len(values)
exit=0
$ zsh -c 'python -c "from average import average; print(average([]))"'
zsh:1: command not found: python
exit=127
$ python3 -c 'from average import average; print(average([]))'
0
exit=0
$ python3 -c 'from average import average; print(average([1, 2, 3]))'
2.0
exit=0
```

이 환경에서는 python 명령이 없어 생성된 검사 명령을 python3로 수정했습니다. 같은 예제에서 빈 목록은 0, 세 원소의 평균은 2.0을 반환했습니다. 초안의 명령은 실행 환경과 대조해 검토해야 합니다.

## 최대 출력 토큰 비교

```bash
$ python3 /Users/yejun/GitHub/Codyssey/B3/B3-2/submission/main.py pr --safe-mode --max-tokens 64 --context '빈 목록의 평균 계산에서 0으로 나누는 오류를 방지합니다'
[INFO] Git status: 1개 파일 변경
[INFO] 전송 파일: 1, 제외: 0, 마스킹: 0, 생략 행: 0
[INFO] model=pickle-general temperature=0.2 max_tokens=64
[ERROR] 형식 검증 실패: 최대 토큰 수에 도달해 출력이 잘렸습니다. --max-tokens와 입력 변경량을 확인하세요
[힌트] 저장소 루트, API 환경변수, URL/모델, 입력 옵션을 확인하세요
[INFO] API 요청 횟수: 2
exit=1
```

같은 diff와 배경에서 max_tokens만 600에서 64로 바꿨습니다. 600에서는 129토큰의 PR을 생성했고, 64에서는 출력이 잘려 최대 두 번 재생성 후 오류로 종료했습니다. 토큰 상한은 형식을 완성할 공간에도 영향을 줍니다.
