"""로케일 메시지 카탈로그를 소스에서 찾아내는 공용 스캐너.

`test_no_emoji_in_user_text.py`(글리프 금지)와 `test_locale_catalog_parity.py`
(로케일 파리티)가 같은 대상을 본다. 스캔 대상을 각자 정의하면 두 가드가 서로 다른
집합을 검사하게 되고, 그 차이가 곧 구멍이 된다.

★ 파일 목록이 아니라 **모양**으로 찾는다. 로케일 코드로 키가 붙은 dict 리터럴이면
새 파일이든 새 카탈로그든 자동으로 걸린다. 목록 방식이 어떻게 새는지는 프론트
이모지 가드가 9개 파일만 보고 있던 사례로 이미 확인했다.

※ `test_` 로 시작하지 않으므로 pytest 가 테스트 모듈로 수집하지 않는다.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"

# 탐지용 로케일 우주 — 제품이 어느 시점에 썼거나 쓸 수 있는 코드 전부.
# ★ 지원 여부와는 다른 개념이다. ru 는 여기 있지만 SUPPORTED_LOCALES 에는 없다
#   (아래 test_locale_catalog_parity 의 설명 참조).
KNOWN_LOCALES = frozenset({"en", "ko", "zh", "es", "vi", "th", "pt", "ru"})

# 로케일 코드 키가 이 개수 이상이면 메시지 카탈로그로 본다.
# 2 로 잡는 이유: {"en": …, "ko": …} 같은 최소 카탈로그도 놓치지 않기 위함.
_MIN_LOCALE_KEYS = 2


@dataclass(frozen=True)
class LocaleDict:
    """소스에서 발견한 로케일 카탈로그 dict 하나."""

    path: str          # app/ 기준 상대경로 (슬래시 표기)
    lineno: int
    locales: frozenset[str]        # 이 dict 가 가진 로케일 키
    values: tuple[str, ...]        # 문자열 값들


def iter_locale_dicts() -> list[LocaleDict]:
    found: list[LocaleDict] = []
    for path in sorted(APP.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - 파싱 불가 파일은 대상 아님
            continue
        rel = str(path.relative_to(APP.parent)).replace("\\", "/")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            keys = {
                k.value
                for k in node.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)
            }
            locales = keys & KNOWN_LOCALES
            if len(locales) < _MIN_LOCALE_KEYS:
                continue
            values = tuple(
                v.value
                for v in node.values
                if isinstance(v, ast.Constant) and isinstance(v.value, str)
            )
            found.append(LocaleDict(rel, node.lineno, frozenset(locales), values))
    return found
