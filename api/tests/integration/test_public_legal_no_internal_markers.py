"""공개 서빙되는 법무 문서에 사내 작업 표기가 남아 있으면 FAIL.

이 테스트가 격리(`KNOWN_PUBLICATION_EXPOSURE`)를 대체한다.

격리는 **현재 오염 상태를 정확히 고정**하는 장치였다. 정확한 개수(48건)와 sha 를
명세에 박아 두고 그 밖의 모든 변화를 실패시켰다. 오염을 관리하기 위한 것이지
오염을 없애기 위한 것이 아니다.

정정이 끝나면 그 장치는 필요 없다. 필요한 것은 **"1건이라도 있으면 FAIL"** 이다.

--- 검사 범위 ------------------------------------------------------------
게이트 없이 공개 서빙되는 문서만 0 을 강제한다.

    api/content/legal/public_privacy.{ko,en}.md
        → api.pigos.io/legal/privacy 로 누구나 볼 수 있다. 항상 0.

가입 동의 화면(`/consent/signup-plan`)이 서빙하는 초안 문서는 다르다.

    master_terms.* · privacy_notice.* · addendum_*.md
        → 전부 status: DRAFT_LAWYER_PENDING. 본문 자체가 [PLACEHOLDER] 골격이다.
          이들에게 지금 0 을 요구하면 승인되지 않은 문안을 채워 넣게 만든다.
          대신 **status 가 DRAFT 를 벗는 순간 0** 이어야 한다 — 그것이 진짜 불변식이다.
          "manifest 는 PUBLISHED 인데 본문은 placeholder" 사고를 이 규칙이 막는다.

--- 금지 토큰 -------------------------------------------------------------
wildcard·정규식 allowlist 를 두지 않는다. 명시 목록만 관리한다.
정상 markdown 링크의 대괄호를 오탐하지 않도록 여는 토큰을 구체적으로 적는다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_API = Path(__file__).resolve().parents[2]
_LEGAL = _API / "content" / "legal"
_MANIFEST = _LEGAL / "manifest.json"

# 공개 URL 로 게이트 없이 서빙되는 파일 — 항상 0
PUBLIC_SERVED = ("public_privacy.ko.md", "public_privacy.en.md")

# 사내 작업 표기. 새 종류를 만들면 여기에 추가한다.
FORBIDDEN: dict[str, re.Pattern[str]] = {
    "COUNSEL": re.compile(r"\[COUNSEL\b[^\]]*\]"),
    "OPEN": re.compile(r"\[OPEN\b[^\]]*\]"),
    "V_MARKER": re.compile(r"\[V\s*[—―–-][^\]]*\]"),
    "V_PROCESS": re.compile(r"V\s*프로세스|\bV[- ]process\b", re.I),
    "OPERATIONAL_CAVEAT": re.compile(r"\[(?:운영|operational)\b[^\]]*\]"),
    "EMPTY_BRACKET": re.compile(r"\[ \]"),
    "PLACEHOLDER": re.compile(r"PLACEHOLDER"),
    "TODO": re.compile(r"\bTODO\b"),
    "TBD": re.compile(r"\bTBD\b"),
    "TEMPLATE_VAR": re.compile(r"\{\{[^}]*\}\}"),
    "KO_PENDING_PHRASE": re.compile(r"실측 확인 필요|운영 확정|변호사 확정 전"),
    "EN_PENDING_PHRASE": re.compile(r"actual verification required|to be confirmed operationally|pending legal counsel", re.I),
    # 사내 문서 경로가 공개본에 새어 나가는 것도 같은 종류의 사고다.
    # ★ 내부 작업 디렉터리 이름을 리터럴로 적지 않는다 — 그 리터럴을 테스트 파일에
    #   두면 test_publication_gate.test_tests_do_not_pin_runtime_to_publish_candidate
    #   가 "테스트가 후보 경로를 정본으로 고정한다" 로 오탐한다. 대신 경로 모양으로
    #   잡는다. 그 편이 더 넓다 — 사내 법무 디렉터리 참조 전부를 막는다.
    "INTERNAL_DOC_PATH": re.compile(r"(?:docs/legal|api/content/legal)/[A-Za-z0-9_./-]+"),
    "INTERNAL_DOC_REF": re.compile(
        r"TERMS_DISPLAY_SPEC|CONSENT_SPEC|CONSENT_AND_DATA_USE"
        r"|DECISION_REGISTER|LAWYER_BRIEF|DRAFT_LAWYER_PENDING"
    ),
}


def _read(p: Path) -> str:
    return p.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _hits(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for name, pat in FORBIDDEN.items():
        found = pat.findall(text)
        if found:
            out[name] = [f if isinstance(f, str) else str(f) for f in found][:5]
    return out


def _fmt(path: Path, hits: dict[str, list[str]]) -> str:
    lines = [f"{path.name} 에 사내 작업 표기가 남아 있다:"]
    for k, v in sorted(hits.items()):
        lines.append(f"  {k:22s} {len(v)}건 예: {v[0][:90]!r}")
    lines.append("")
    lines.append("공개본에는 확정된 문장만 둔다. 값이 없으면 그 문장을 빼거나,")
    lines.append("'검토 중이며 확정 시 개정·고지한다'로 상태를 밝히는 조항으로 바꾼다.")
    lines.append("★ 확정되지 않은 보유기간을 임의로 만들어 채우지 않는다.")
    return "\n".join(lines)


# ★ 2026-09-16: xfail 을 제거했다. V-11 이 실측으로 닫히면서 소스 마커가 0 이 됐고,
#   strict xfail 이 설계대로 XPASS 로 울려 이 자리를 알려주었다.
#
#   ☞ 그 xfail 의 주석은 "그때 이 xfail 을 지우고 **격리 문서를 삭제한다**" 였는데,
#     뒤쪽 절반은 아직 하지 않는다. 소스 마커 0 과 공개 URL 마커 0 은 다르다 —
#     api.pigos.io/legal/privacy 는 배포 전까지 정정 전 본문을 서빙한다.
#     격리 종료는 **프로덕션 엔드포인트에서** 마커 0 이 확인된 뒤다
#     (KNOWN_PUBLICATION_EXPOSURE "상단 정의").
#
#   즉 지금부터 이 테스트가 소스의 enforcer 이고, 격리 문서는 프로덕션의 enforcer 다.
@pytest.mark.parametrize("name", PUBLIC_SERVED)
def test_publicly_served_notice_has_no_internal_markers(name: str) -> None:
    """게이트 없이 공개되는 문서 — 1건이라도 있으면 FAIL."""
    p = _LEGAL / name
    assert p.exists(), f"{name} 이 없다"
    hits = _hits(_read(p))
    assert not hits, _fmt(p, hits)


def test_approved_documents_have_no_internal_markers() -> None:
    """DRAFT 를 벗은 문서는 본문도 확정본이어야 한다.

    manifest status 만 올리고 본문이 placeholder 로 남는 사고를 막는다.
    """
    manifest = json.loads(_read(_MANIFEST))
    failures: list[str] = []
    for doc_id, meta in manifest.get("documents", {}).items():
        status = str(meta.get("status", ""))
        if status.startswith("DRAFT"):
            continue  # 초안 단계에서는 표기가 정상이다
        for lang, fname in (meta.get("langs") or {}).items():
            p = _LEGAL / fname
            if not p.exists():
                failures.append(f"{doc_id}[{lang}] 파일 없음: {fname}")
                continue
            hits = _hits(_read(p))
            if hits:
                failures.append(f"{doc_id}[{lang}] status={status}\n{_fmt(p, hits)}")
    assert not failures, "\n\n".join(failures)


def test_draft_documents_are_still_marked_draft_in_manifest() -> None:
    """위 테스트가 공회전하지 않는지 확인 — 초안이 실제로 DRAFT 로 표시돼 있어야 한다."""
    manifest = json.loads(_read(_MANIFEST))
    docs = manifest.get("documents", {})
    assert docs, "manifest 에 문서가 없다"
    assert any(str(m.get("status", "")).startswith("DRAFT") for m in docs.values()), (
        "모든 문서가 DRAFT 를 벗었다면 test_approved_documents_... 가 전부 검사해야 한다. "
        "이 테스트를 지우고 그쪽이 도는지 확인하라."
    )


# ── 재오염 방지 — 정본 초안에서 다시 복사해 오는 경로 ────────────────────────────
#
# `docs/legal/publish_candidate/` 는 **승인 절차의 정본**이다: 승인 → 그 본문 교체 → PUBLISHED.
# 그런데 승인 전인 지금 그 정본에는 검토 마커 24건이 그대로 있다. 옛 테스트와
# `public_notice.py` 의 docstring 은 "정본을 고쳤으면 cp 로 사본을 갱신하라" 고 적어두었다 —
# 그 지시를 따르는 순간 공개본이 48건으로 되돌아간다. 2026-09-17 하루 전에도 그 경로가
# 열려 있었다.
#
# 이 테스트는 정본을 고치지 않는다(승인 전 본문 편집 금지). 대신 **정본에 마커가 남아 있는
# 동안 서빙본이 정본과 같아지는 것**을 실패로 만든다. 정본이 승인·정정되어 마커 0 이 되면
# 이 조건은 자연히 해제된다.

_CANDIDATE = {
    "public_privacy.ko.md": _API.parent / "docs" / "legal" / "publish_candidate" / "PIGOS_GLOBAL_PRIVACY_NOTICE.md",
    "public_privacy.en.md": _API.parent / "docs" / "legal" / "publish_candidate" / "en" / "PIGOS_GLOBAL_PRIVACY_NOTICE_EN.md",
}


@pytest.mark.parametrize("name", PUBLIC_SERVED)
def test_served_copy_is_not_resynced_from_a_marked_candidate(name: str) -> None:
    """정본에 마커가 있는 한, 서빙본을 정본으로 덮어쓰면 실패한다."""
    served = (_LEGAL / name).read_text(encoding="utf-8").replace("\r\n", "\n")
    cand_path = _CANDIDATE[name]
    if not cand_path.exists():
        pytest.skip(f"{cand_path} 없음 — 이 체크아웃에는 정본 초안이 없다")
    candidate = cand_path.read_text(encoding="utf-8").replace("\r\n", "\n")

    cand_markers = sum(len(v) for v in _hits(candidate).values())
    if cand_markers == 0:
        return  # 정본이 깨끗하다 — 같아져도 문제없다

    assert served != candidate, (
        f"{name} 이 publish_candidate 와 바이트 동일하다 — 정본에는 검토 마커가 {cand_markers}건 "
        f"남아 있다. 'cp publish_candidate → public_privacy' 로 되돌린 것이다. "
        f"공개본은 정정본이어야 한다 (KNOWN_PUBLICATION_EXPOSURE)."
    )
