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
