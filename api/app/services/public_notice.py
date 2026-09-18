"""공개 개인정보 처리방침 렌더링 — `/legal/privacy`.

## 왜 만들었나 (2026-08-26)

App Store 제출에는 방침 URL 이 **필수 입력값**이다. 그런데 그 URL 이 서빙하던 것은
손으로 쓴 정적 HTML(2026-06-29 자)이었고, 정본과 어긋나 있었다:

    jhbae@wiselake.co.kr  ×3   ← **대표 개인 메일이 공개돼 있었다**
    FCM ×2 / Firebase ×4       ← 앱은 APNs 만 쓴다. 방침이 실제 동작과 달랐다
    Wiselake Co.               ← 상호 오기 (WiseLake Inc.)
    보호책임자·사업자번호·법정보존 기간 없음

심사자가 앱 내 문구와 웹을 대조할 수 있는 부분이라 그대로 제출하면 위험했다.

★ 그래서 **정본 마크다운을 런타임에 렌더링**한다. 손으로 쓴 HTML 을 다시 두지 않는다 —
  그게 어긋남의 원인이었다. 정본이 바뀌면 웹도 자동으로 따라간다.

## consent 원장과는 분리한다

`content/legal/privacy_notice.{ko,en}.md` 는 **동의 원장이 버전으로 추적**하는 문서다
(manifest.json → consent_ledger). 거기에 정본을 넣으면 notice_version 이 올라가
**기존 사용자에게 재동의 배너**가 뜬다 — 법무 검토가 필요한 별개 사안이다.

그래서 공개용은 `public_privacy.{ko,en}.md` 로 **따로 둔다.** 스토어 제출을 막는 것은
URL 하나이고, 재동의 흐름은 그것과 분리해서 다룬다.

## ★ 이 파일들을 publish_candidate 에서 복사해 오지 말 것 (2026-09-17)

예전 판은 "이 파일들은 `docs/legal/publish_candidate/` 정본의 사본이니 정본을 고치면
`cp` 로 갱신하라" 고 적었고, 테스트가 바이트 동일성을 강제했다. **그 지시가 사고의 경로였다.**
publish_candidate 는 승인 절차의 정본이지만 승인 전인 지금은 `[OPEN]`·`[COUNSEL]`·`[V]`
검토 마커가 24건 남아 있는 **작업 초안**이고, 그것을 그대로 복사하면 공개 URL 에 사내
검토 표기가 노출된다 — 2026-08-27 부터 실제로 그랬다 (KNOWN_PUBLICATION_EXPOSURE, 48건).

관계는 이렇다:

    승인 → publish_candidate 본문 확정 → 그때 서빙본 교체 → PUBLISHED
    승인 전 → 서빙본은 **정정본**(마커 0)이며 정본과 다른 것이 정상이다

`tests/integration/test_public_legal_no_internal_markers.py` 가 두 가지를 강제한다:
서빙본에 마커 0, 그리고 정본에 마커가 남아 있는 동안 서빙본이 정본과 같아지면 실패.
"""
from __future__ import annotations

import html as _html
from functools import lru_cache
from pathlib import Path

import markdown as _markdown

# app/services/public_notice.py → parents[2] = api/  (content/ 는 app/ 밖에 있다)
_CONTENT_DIR = Path(__file__).resolve().parents[2] / "content" / "legal"

# 정본이 쓰는 문법만 켠다. 표가 깨지면 고지가 깨지므로 tables 는 필수다.
_EXTENSIONS = ["tables", "sane_lists"]

SUPPORTED = ("ko", "en")
DEFAULT_LANG = "en"          # 글로벌 서비스 — 언어 미지정 기본은 영어

_CSS = """
:root { color-scheme: light dark; }
body { margin:0 auto; padding:2rem 1.25rem 4rem; max-width:52rem;
       font:16px/1.75 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,
       "Helvetica Neue","Apple SD Gothic Neo","Noto Sans KR",sans-serif;
       color:#1f2937; background:#fff; word-break:keep-all; }
@media (prefers-color-scheme: dark) { body { color:#e5e7eb; background:#0f172a; } }
h1 { font-size:1.6rem; line-height:1.35; margin:0 0 1.5rem; }
h2 { font-size:1.15rem; margin:2.25rem 0 .75rem; padding-top:.75rem;
     border-top:1px solid rgba(128,128,128,.25); }
h3 { font-size:1rem; margin:1.5rem 0 .5rem; }
table { width:100%; border-collapse:collapse; margin:1rem 0; font-size:.9rem;
        display:block; overflow-x:auto; }
th,td { border:1px solid rgba(128,128,128,.35); padding:.5rem .6rem;
        text-align:left; vertical-align:top; }
th { background:rgba(128,128,128,.12); font-weight:600; }
code { font-size:.9em; padding:.1em .3em; border-radius:3px;
       background:rgba(128,128,128,.15); }
blockquote { margin:1rem 0; padding:.6rem 1rem; border-left:3px solid rgba(128,128,128,.4);
             background:rgba(128,128,128,.07); }
a { color:#2563eb; } @media (prefers-color-scheme: dark) { a { color:#60a5fa; } }
.lang { margin:0 0 2rem; font-size:.85rem; }
.lang a { margin-right:.75rem; }
"""

_PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index,follow">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<p class="lang">{switcher}</p>
{body}
</body>
</html>
"""

_TITLES = {
    "ko": "개인정보 처리방침 — PigOS",
    "en": "Privacy Notice — PigOS",
}


def normalize_lang(raw: str | None) -> str:
    """`?lang=` 또는 Accept-Language 앞부분을 지원 언어로 정규화."""
    if not raw:
        return DEFAULT_LANG
    head = raw.split(",")[0].strip().lower().replace("_", "-")
    base = head.split("-")[0]
    return base if base in SUPPORTED else DEFAULT_LANG


@lru_cache(maxsize=len(SUPPORTED))
def render(lang: str) -> str:
    """정본 마크다운 → 완성된 HTML 페이지.

    lru_cache: 방침은 배포 사이에 바뀌지 않는다. 매 요청 파싱할 이유가 없다
    (30KB 문서라 파싱 비용이 작지 않다).
    """
    lang = lang if lang in SUPPORTED else DEFAULT_LANG
    src = (_CONTENT_DIR / f"public_privacy.{lang}.md").read_text(encoding="utf-8")
    body = _markdown.markdown(src, extensions=_EXTENSIONS, output_format="html")

    others = [x for x in SUPPORTED if x != lang]
    switcher = " ".join(
        f'<a href="/legal/privacy?lang={x}">{_html.escape("한국어" if x == "ko" else "English")}</a>'
        for x in others
    )
    return _PAGE.format(lang=lang, title=_html.escape(_TITLES[lang]),
                        css=_CSS, switcher=switcher, body=body)
