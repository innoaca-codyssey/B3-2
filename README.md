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

## 안전 모드 ON

```bash
$ python3 /Users/yejun/GitHub/Codyssey/B3/B3-2/submission/main.py commit --safe-mode --max-tokens 600 --context '평균 예외 처리와 설정 예제 추가입니다. 설정 값은 테스트용 가짜 데이터입니다.'
[INFO] Git status: 4개 파일 변경
[INFO] 전송 파일: 3, 제외: 1, 마스킹: 3, 생략 행: 0
[INFO] model=pickle-general temperature=0.2 max_tokens=600
[INFO] API 요청 횟수: 1
[INFO] tokens: prompt=546 completion=77
[DONE] 형식 검증 완료
--- Commit Message ---
feat: 평균 함수 예외 처리 및 설정 파일 추가

- average.py: 빈 리스트 입력 시 0을 반환하도록 예외 처리 추가
- profile.py: 테스트용 설정 파일 추가 (API 키 및 연락처)
- __pycache__: 컴파일된 바이트코드 파일 포함
```

가짜 토큰과 이메일이 있는 같은 예제에서 .env는 제외하고 diff 문자열을 마스킹했습니다. 아래 설정 값은 실습용 가짜 데이터이며 실제 발급 키는 포함하지 않았습니다.

## 안전 모드 OFF

```bash
$ python3 /Users/yejun/GitHub/Codyssey/B3/B3-2/submission/main.py commit --max-tokens 600 --context '평균 예외 처리와 설정 예제 추가입니다. 설정 값은 테스트용 가짜 데이터입니다.'
[INFO] Git status: 4개 파일 변경
[INFO] 전송 파일: 4, 제외: 0, 마스킹: 0, 생략 행: 0
[INFO] model=pickle-general temperature=0.2 max_tokens=600
[INFO] API 요청 횟수: 1
[INFO] tokens: prompt=642 completion=68
[DONE] 형식 검증 완료
--- Commit Message ---
평균 계산 예외 처리 및 설정 파일 추가

- average.py: 빈 리스트 입력 시 0을 반환하도록 예외 처리 추가
- .env: 테스트용 API 키 설정 파일 추가
- profile.py: 샘플 프로필 데이터 파일 추가
```

OFF에서는 .env까지 포함해 4개 파일을 보내고 치환하지 않았습니다. ON에서는 3개 파일을 전송하고 1개 제외, 3회 치환했습니다. 예제 실행으로 생긴 __pycache__도 status에 포함되어 초안에 나타났으므로 Git ignore 정책과 생성 내용을 검토해야 합니다.

## 변경 없음과 키 누락

```bash
$ python3 main.py commit
[INFO] 변경 사항이 없습니다
[INFO] API 요청 횟수: 0
exit=0

$ env -u AI_API_KEY python3 main.py commit
[ERROR] AI_API_KEY가 없습니다. 환경변수를 설정하세요
[힌트] 저장소 루트, API 환경변수, URL/모델, 입력 옵션을 확인하세요
[INFO] API 요청 횟수: 0
exit=1

```

변경이 없으면 API를 호출하지 않고 0으로 종료합니다. 키가 없으면 원인과 힌트를 출력하고 1로 종료합니다.

## 실제 인증 실패

```bash
$ AI_API_KEY=invalid-b3-2-test python3 /Users/yejun/GitHub/Codyssey/B3/B3-2/submission/main.py commit --safe-mode --max-tokens 600
[INFO] Git status: 4개 파일 변경
[INFO] 전송 파일: 3, 제외: 1, 마스킹: 3, 생략 행: 0
[INFO] model=pickle-general temperature=0.2 max_tokens=600
[ERROR] API HTTP 401: {"error":{"code":"invalid_api_key","message":"API Key가 올바르지 않습니다. 콘솔에서 발급한 Key인지 확인해주세요.","type":"authentication_error"}}

[힌트] 저장소 루트, API 환경변수, URL/모델, 입력 옵션을 확인하세요
[INFO] API 요청 횟수: 1
exit=1
```

유효하지 않은 테스트 값을 별도로 지정해 HTTP 401을 확인했습니다. 인증 실패는 재생성하지 않으며 한 번의 요청 후 1로 종료합니다. 저장된 정상 키는 변경하지 않았습니다.

## 옵션과 안전 모드 정책

```bash
python3 main.py commit --help
python3 main.py pr --safe-mode --model pickle-general --temperature 0.2 --max-tokens 1200
python3 main.py commit --safe-mode --max-files 5 --max-lines 100 --context '변경 배경'
```

Git 저장소마다 루트에서 실행해야 합니다. 도구 파일이 다른 경로에 있으면 `python3 /경로/B3-2/main.py pr --safe-mode`처럼 호출합니다. 코드와 환경변수가 준비되면 추가 pip 설치는 필요하지 않습니다.

| 옵션 | 기본값 | 용도 |
|---|---|---|
| --base-url | AI_BASE_URL 또는 https://llm.pcl.kr/v1 | OpenAI 호환 API 주소 |
| --model | AI_MODEL 또는 pickle-general | 요청 모델 |
| --temperature | 0.2 | 0~2의 샘플링 설정 |
| --max-tokens | 1200 | 최대 출력 토큰 |
| --timeout | 60 | 요청별 대기 초 |
| --safe-mode | OFF | 경로 제외, 마스킹과 입력 제한 |
| --max-files | 10 | 안전 모드의 최대 전송 파일 수 |
| --max-lines | 200 | 안전 모드의 전체 diff 최대 행 수 |
| --context | 추가 배경 없음 | 사용자가 알려주는 변경 이유 |

안전 모드는 .env/.env.*, .pem/.key, credentials, credentials.json, .git-credentials, id_rsa/id_ed25519, secrets.json과 .aws/.ssh 안의 경로를 읽기 전에 제외합니다. pickle-/sk-/ghp_/github_pat_ 토큰, AWS Access Key ID, 이메일, 키/비밀번호 할당과 개인키 블록을 마스킹합니다. 이름 변경은 이전 경로도 검사합니다. 마스킹은 행을 제한하기 전에 적용하며, 로그의 마스킹 수는 치환 횟수입니다.

파일 수와 diff 행 수를 제한하면 입력량을 줄일 수 있지만 생략된 변경이 초안에서 빠질 수 있습니다. 바이너리는 Git이 출력한 변경 표시만 전달합니다. 이 정책이 모든 개인정보 형식을 인식하는 것은 아니므로 실제 입력 범위와 결과를 검토해야 합니다.

## 코드 흐름과 형식 검증

changes.py는 Git status를 읽고 작업 트리/인덱스의 diff를 함께 수집합니다. 비추적 파일은 git diff --no-index로 비교합니다. Git 출력의 파일 경로는 셸 문자열에 끼워 넣지 않고 subprocess의 인자 목록으로 전달합니다. privacy.py는 전송할 경로, 문자열과 분량을 결정합니다.

client.py는 모델, messages, temperature, max_tokens를 JSON으로 만들고 Bearer 인증 헤더와 함께 /chat/completions에 POST합니다. 응답의 choices[0].message.content를 읽습니다. HTTP 오류는 상태 코드와 서버 원인, 연결 오류는 원인과 해결 힌트를 출력합니다. API Key는 환경변수에서만 읽으며 URI나 프롬프트에 넣지 않습니다.

drafts.py는 용도별 JSON 스키마와 상태/diff, 추가 배경으로 프롬프트를 구성하고 결과를 검증합니다. 커밋은 제목과 선택 본문, PR은 title/why/what/tests를 요구합니다. PR의 세 섹션에는 비어 있지 않은 불릿이 있어야 합니다. main.py는 옵션과 메시지, 종료 코드를 담당합니다. Git 수집과 HTTP 호출을 분리해 저장소나 서버 없이 각각 검사할 수 있습니다.

제목은 한 줄로 정리하고 커밋 72자, PR 80자를 넘으면 후처리로 제한합니다. 커밋 제목 50자는 권장값으로 넘으면 안내합니다. 빈 필드나 잘린 JSON, 누락 섹션은 임의 문장으로 채우지 않고 한 번 재생성합니다. 정상 입력은 요청 1회, 형식 재생성은 최대 2회입니다. 네트워크와 인증 실패는 재시도하지 않습니다.

temperature를 낮추면 표현의 변동을 줄이는 방향이고 높이면 더 다양한 표현을 선택할 수 있습니다. max_tokens는 출력 상한이며 토큰과 글자 수는 다릅니다. 파라미터를 CLI로 받아 같은 diff에서 조건을 바꿔 비교할 수 있습니다. 이 서버에서는 max_tokens=64와 600의 종료/생성 차이를 확인했습니다. 요청 형식과 파라미터 의미는 [OpenAI Chat Completions 문서](https://developers.openai.com/api/reference/cli/resources/chat/subresources/completions/methods/create)를 참고했습니다.

초안에는 변경 배경이나 실행할 검사를 추정한 문장이 포함될 수 있습니다. 실제로 수행하지 않은 검사가 성공했다는 표현, 빠진 변경, 환경에 맞지 않는 명령을 확인해야 합니다. 이 예제에서도 python 명령을 python3로 수정했습니다. 실제 팀에 적용한다면 전송 경로 허용 목록과 프로젝트별 ignore/검사 명령을 먼저 설정해 입력 범위와 테스트 제안을 일치시키겠습니다.

검사는 다음과 같이 실행합니다.

```bash
python3 -m unittest discover -s tests -v
```
