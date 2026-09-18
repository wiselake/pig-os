"""공개 개인정보 처리방침 `/legal/privacy` — App Store 제출 필수 URL.

## 배경 (2026-08-26)

이 URL 이 서빙하던 것은 손으로 쓴 정적 HTML(2026-06-29 자)이었고 정본과 어긋나 있었다.
iOS 팀이 제출 준비 중 실측으로 잡았다:

    jhbae@wiselake.co.kr  ×3   ← **대표 개인 메일이 공개돼 있었다**
    FCM ×2 / Firebase ×4       ← 앱은 APNs 만 쓴다 (서드파티 SDK 0개)
    Wiselake Co.               ← 상호 오기
    보호책임자·사업자번호·법정보존 기간 없음

심사자가 앱 내 문구와 웹을 대조할 수 있는 부분이라 그대로 제출하면 위험했다.

★ 이 파일이 잠그는 것
  1) 렌더 결과에 **개인 메일·FCM·Firebase·상호 오기가 없다**
  2) PIPA §30 필수기재사항(보호책임자·담당부서·연락처)이 실제로 들어 있다
  3) 라우트가 ko·en 을 모두 서빙하고 Accept-Language 를 존중한다

★ 제거된 계약 (2026-09-03)
  이 파일은 원래 `public_privacy.*` 가 `publish_candidate/` 와 **바이트 동일**하도록
  강제했다. 그런데 publish_candidate 는 후보이고 `[OPEN]`·`[COUNSEL]` 이 남아 있는 것이
  정상인 작업물이다. 그 동일성을 강제한 결과 후보의 미완성이 그대로 공개본의 미완성이
  됐고, App Store 제출 URL 에 미해결 마커 24건이 노출됐다.
  → 게시 경계 계약은 `test_publication_gate.py` 로 옮겼다.
    올바른 계약은 "runtime == 승인된 PUBLISHED artifact" 이며,
    PUBLISHED artifact 가 등록되기 전까지는 격리(KNOWN_PUBLICATION_EXPOSURE)로 대신한다.
"""
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.services import public_notice

pytestmark = pytest.mark.anyio

_API = Path(__file__).resolve().parents[2]

# 다시 나타나면 안 되는 것들 — 전부 실제로 게시돼 있던 값이다.
_FORBIDDEN = ("jhbae@wiselake.co.kr", "gyomoon@wiselake.co.kr", "gyomoon@ezfarm.co.kr",
              "FCM", "Firebase", "Wiselake Co.")


# ── 1) 다시 나타나면 안 되는 값 ──────────────────────────────────────────────

@pytest.mark.parametrize("lang", ["ko", "en"])
def test_no_stale_or_private_values_in_render(lang):
    """★ 개인 메일·미사용 SDK·상호 오기가 렌더 결과에 없어야 한다."""
    html = public_notice.render(lang)
    found = [x for x in _FORBIDDEN if x in html]
    assert not found, f"{lang}: 제거된 값이 다시 나타났다 — {found}"


# ── 2) PIPA §30 필수기재사항 ─────────────────────────────────────────────────

def test_korean_notice_has_privacy_officer_block():
    """공란으로는 게시할 수 없는 항목 — 없으면 방침 자체가 위반이다."""
    html = public_notice.render("ko")
    for required in ("개인정보 보호책임자", "경영지원팀", "진교문",
                     "wiselake@wiselake.ai", "+82-31-421-3418"):
        assert required in html, f"PIPA §30 필수기재 누락: {required}"


def test_tables_actually_render():
    """표가 깨지면 항목·보유기간 고지가 통째로 뭉개진다 — 마크다운 tables 확장 확인."""
    for lang in ("ko", "en"):
        html = public_notice.render(lang)
        assert html.count("<table>") >= 8, f"{lang}: 표가 {html.count('<table>')}개뿐"
        assert "<th>" in html and "</td>" in html


# ── 3) 라우트 ────────────────────────────────────────────────────────────────

async def test_route_serves_both_languages(client: AsyncClient):
    for lang in ("ko", "en"):
        r = await client.get(f"/legal/privacy?lang={lang}")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("text/html")
        assert f'<html lang="{lang}"' in r.text


async def test_route_honors_accept_language(client: AsyncClient):
    r = await client.get("/legal/privacy", headers={"Accept-Language": "ko-KR,ko;q=0.9"})
    assert '<html lang="ko"' in r.text

    r = await client.get("/legal/privacy", headers={"Accept-Language": "fr-FR"})
    assert '<html lang="en"' in r.text, "미지원 언어는 영어로 떨어져야 한다"


async def test_route_never_500s_on_odd_input(client: AsyncClient):
    """스토어 심사자가 어떤 요청을 보내도 200 이어야 한다 — 방침 URL 이 죽으면 제출이 막힌다."""
    for q in ("", "?lang=", "?lang=zz", "?lang=../etc/passwd", "?lang=ko-KR"):
        r = await client.get(f"/legal/privacy{q}")
        assert r.status_code == 200, f"{q!r} → {r.status_code}"


def test_lang_normalization_rejects_path_traversal():
    """lang 이 파일 경로로 쓰이므로 정규화가 뚫리면 임의 파일을 읽는다."""
    for evil in ("../../etc/passwd", "ko/../../../secret", "..", "/etc/passwd"):
        assert public_notice.normalize_lang(evil) in public_notice.SUPPORTED
