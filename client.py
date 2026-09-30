from dataclasses import dataclass
import json
import socket
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.error import HTTPError, URLError
from privacy import redact


class APIError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


@dataclass
class Completion:
    text: str
    finish_reason: str | None
    usage: dict


class ChatClient:
    def __init__(self, base_url: str, model: str, key: str, temperature: float, max_tokens: int, timeout: float):
        parsed = urlsplit(base_url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('base URL 형식을 확인하세요')
        if parsed.scheme == 'http' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('원격 API는 HTTPS 주소를 사용하세요')
        self.url = base_url.rstrip('/') + '/chat/completions'
        self.model, self.key = model, key
        self.temperature, self.max_tokens, self.timeout = temperature, max_tokens, timeout
        self.calls = 0
        self.opener = build_opener(NoRedirect())

    def complete(self, messages: list[dict]) -> Completion:
        body = {'model': self.model, 'messages': messages, 'temperature': self.temperature, 'max_tokens': self.max_tokens, 'stream': False}
        request = Request(self.url, data=json.dumps(body, ensure_ascii=False).encode('utf-8'), headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'})
        self.calls += 1
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                data = json.load(response)
        except HTTPError as error:
            try:
                detail = error.read(4096).decode('utf-8', errors='replace')
            finally:
                error.close()
            detail, _ = redact(detail, self.key)
            raise APIError(f'API HTTP {error.code}: {detail[:500]}') from error
        except (URLError, TimeoutError, socket.timeout) as error:
            raise APIError(f'API 연결 실패: {error}') from error
        except (ValueError, UnicodeError) as error:
            raise APIError('API가 올바른 JSON 응답을 반환하지 않았습니다') from error
        try:
            choice = data['choices'][0]
            text = choice['message']['content']
            if not isinstance(text, str) or not text.strip():
                raise ValueError('empty content')
            usage = data.get('usage') or {}
            if not isinstance(usage, dict):
                raise ValueError('invalid usage')
            return Completion(text, choice.get('finish_reason'), usage)
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise APIError('API 응답에 choices[0].message.content 텍스트가 없습니다') from error
