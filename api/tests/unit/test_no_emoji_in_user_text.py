"""사용자 노출 문자열에 이모지·글리프가 없어야 한다 (백엔드 R7).

## 왜 백엔드에도 필요한가

프론트에는 이모지 가드가 있었는데(`src/tests/no-emoji-guard.test.ts`) 백엔드에는
없었다. 그 사이로 룰 엔진 심각도 라벨이 새어 있었다.

    severity_critical  "🔴 Critical" · "🔴 위험" · "🔴 严重" …  7개 언어
    severity_warning   "⚠ Warning"  · "⚠ 경고"   …
    severity_ok        "✓"

이 문자열은 `renderer.py:64` 에서 챗 응답 **본문**으로 그대로 나간다. 서버가 만든
텍스트라 클라이언트가 색·크기·정렬을 잡을 수 없고, 스크린리더는 글리프를 읽는다.
등급은 `StructuredResult.severity` 필드로도 내려가므로 표시 강조는 그쪽 몫이다.

## 어떻게 찾는가 — 파일 목록이 아니라 모양으로

프론트 가드는 원래 9개 파일 목록이었고, 목록 밖은 전부 샜다. 같은 실수를 피하려고
여기서는 **로케일 코드로 키가 붙은 dict 리터럴**을 AST 로 찾는다. 새 메시지 카탈로그를
어느 파일에 만들든 그 모양이면 자동으로 걸린다.
"""
from __future__ import annotations

import re

from tests.locale_catalogs import iter_locale_dicts

# picto 이모지 + 텍스트에 섞이던 글리프. ℹ(U+2139) 포함 — 이모지 범위 밖이라 놓치기 쉽다.
BANNED = re.compile(
    "[\U0001f300-\U0001faff\U0001f1e6-\U0001f1ff☀-➿"
    "ℹ✓✔✕✖★☆]"
)


def _catalog_strings() -> list[tuple[str, int, str]]:
    """(파일, 줄, 문자열) — 로케일 카탈로그 안의 문자열 값 전부.

    스캐너는 tests/locale_catalogs.py 와 공유한다. 파리티 가드와 다른 집합을
    검사하면 그 차이가 곧 구멍이 된다.
    """
    return [
        (cat.path, cat.lineno, value)
        for cat in iter_locale_dicts()
        for value in cat.values
    ]


def test_catalog_scan_is_not_empty() -> None:
    """스캔이 조용히 0건이 되면 가드가 통과하는 게 아니라 사라진 것이다."""
    assert len(_catalog_strings()) > 100


def test_no_emoji_in_localized_strings() -> None:
    offenders = [
        f"{rel}:{line}: {text[:60]}"
        for rel, line, text in _catalog_strings()
        if BANNED.search(text)
    ]
    assert offenders == [], "사용자 노출 문자열에 이모지/글리프가 있다:\n" + "\n".join(offenders)
