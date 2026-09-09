"""LEGAL-P0-LIVE-PUBLICATION-EXPOSURE — 공개 법무문서 게시 경계.

## 왜 생겼나

2026-09-03 실측: `https://api.pigos.io/legal/privacy` — App Store 제출 URL — 이
내부 검토 마커를 공개하고 있었다.

    "…requires legal counsel's review [COUNSEL]"
    "[OPEN — to be confirmed operationally: …]"
    "[V — actual verification required]"

원인은 `test_public_notice.py::test_runtime_copy_matches_canonical` 이
런타임 서빙본을 `publish_candidate` 와 바이트 동일하게 강제한 것이다.
publish_candidate 는 **후보**이고 미해결 마커가 남아 있는 게 정상인 작업물이라,
그 계약은 안전장치가 아니라 오염 경로를 고정하고 있었다.

## 이 파일이 잠그는 것

1) publish_candidate 는 어떤 경로로도 runtime source 가 될 수 없다
2) 미해결 마커는 KNOWN_PUBLICATION_EXPOSURE 에 **정확히** 등록된 것만 한시 허용
   — 신규도 실패, 감소도 실패(문서가 바뀐 것이므로 명세를 갱신해야 한다)
3) 격리에는 절대 만료가 있다. 지나면 무조건 실패한다
4) status != PUBLISHED 문서는 게시 경계를 넘지 못한다

★ 이 파일은 노출을 **제거하지 않는다.** 문안 수정은 미승인 법무문서 편집이라
  개발이 할 수 없다. 현재 상태를 고정하고 재발만 막는다 —
  CONTAINED_NOT_REMEDIATED.
"""
from __future__ import annotations

import ast
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

_API = Path(__file__).resolve().parents[2]
_REPO = _API.parent
_MANIFEST = _REPO / "docs/legal/KNOWN_PUBLICATION_EXPOSURE.md"

# 미해결 마커 — 게시본에 남아 있으면 안 되는 것들.
# 새 종류를 추가할 때는 KNOWN_PUBLICATION_EXPOSURE 의 종류 표도 함께 갱신한다.
_MARKER_PATTERNS: dict[str, re.Pattern[str]] = {
    "COUNSEL": re.compile(r"\[COUNSEL[^\]]*\]"),
    "OPEN": re.compile(r"\[OPEN[^\]]*\]"),
    "V": re.compile(r"\[V\s*[—―–-][^\]]*\]"),
    "EMPTY_BRACKET": re.compile(r"\[ \]"),
    "TODO": re.compile(r"\bTODO\b"),
    "TBD": re.compile(r"\bTBD\b"),
    "PLACEHOLDER": re.compile(r"PLACEHOLDER"),
    "TEMPLATE_VAR": re.compile(r"\{\{[^}]*\}\}"),
}


def _read(p: Path) -> str:
    return p.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _count_markers(text: str) -> Counter[str]:
    c: Counter[str] = Counter()
    for name, pat in _MARKER_PATTERNS.items():
        n = len(pat.findall(text))
        if n:
            c[name] = n
    return c


def _sha256(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _nondoc_string_literals(path: Path) -> list[str]:
    """docstring 을 제외한 문자열 리터럴만 모은다.

    ★ 단순 문자열 검색으로는 안 된다. 모듈 docstring 이 "이 파일은
      publish_candidate 의 사본이다" 라고 **설명**만 해도 걸린다. 잡아야 하는 것은
      코드가 실제로 그 경로를 여는 것이고, 그건 docstring 아닌 리터럴로만 나타난다.
      (주석은 ast 가 애초에 버린다)"""
    # utf-8-sig: BOM 이 있는 소스가 있어 utf-8 로 읽으면 ast.parse 가 U+FEFF 로 깨진다.
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)                and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]


def _reads_publish_candidate(path: Path) -> bool:
    return any("publish_candidate" in lit for lit in _nondoc_string_literals(path))


def _manifest() -> dict:
    """격리 명세를 문서에서 직접 읽는다 — 별도 JSON 파일을 두면 문서와 갈라진다."""
    raw = _read(_MANIFEST)
    m = re.search(r"QUARANTINE_MANIFEST_BEGIN\s*-->\s*```json\s*(\{.*?\})\s*```", raw, re.S)
    assert m, "KNOWN_PUBLICATION_EXPOSURE.md 에서 격리 명세 블록을 찾지 못했다"
    return json.loads(m.group(1))


# ── 1. 격리 만료 — 이벤트가 아니라 절대 시각 ────────────────────────────────

def test_quarantine_has_not_expired():
    """★ 만료되면 무조건 실패한다. 자동 연장 없음.

    이벤트 기반("결정되면 해소")만 두면 결정이 밀릴 때 사실상 영구 예외가 된다.
    연장하려면 사유를 적고 expires_at 을 바꾸는 별도 커밋이 필요하며,
    그 커밋 자체가 감사 흔적이 된다."""
    mf = _manifest()
    expires = datetime.fromisoformat(mf["expires_at"])
    now = datetime.now(expires.tzinfo)
    assert now <= expires, (
        f"공개 문서 미해결 마커 격리가 만료됐다 (expires_at={mf['expires_at']}).\n"
        f"  현재 노출: {mf['status']}\n"
        f"  해소 조건: {mf['remediation_condition']}\n"
        f"  → 해소했으면 KNOWN_PUBLICATION_EXPOSURE.md 를 삭제하고 이 테스트를 hard fail 로 전환한다.\n"
        f"  → 아직이면 책임자 재판단 후 사유와 함께 expires_at 을 명시 변경한다."
    )


def test_quarantine_status_is_not_claimed_resolved():
    """해소되지 않았는데 RESOLVED 로 적어두는 것을 막는다."""
    assert _manifest()["status"] == "CONTAINED_NOT_REMEDIATED"


# ── 2. 등록분과 정확히 일치 — 증가도 감소도 실패 ────────────────────────────

def test_public_notice_markers_match_quarantine_exactly():
    """★ observed != registered → FAIL.

    23건이어도 green 으로 두지 않는다. 줄었다는 것은 문서가 바뀌었다는 뜻이고,
    왜 줄었는지 기록하며 명세를 갱신해야 한다."""
    mf = _manifest()
    for entry in mf["entries"]:
        path = _REPO / entry["source_path"]
        assert path.exists(), f"{entry['source_path']} 없음 — 라우트가 500 을 낸다"
        text = _read(path)

        observed = _count_markers(text)
        registered = Counter({k: v for k, v in entry["markers"].items()})

        assert observed == registered, (
            f"{entry['source_path']}: 미해결 마커가 등록분과 다르다.\n"
            f"  등록 {dict(sorted(registered.items()))}\n"
            f"  실측 {dict(sorted(observed.items()))}\n"
            f"  → 늘었으면 신규 오염이다. 되돌려라.\n"
            f"  → 줄었으면 문서가 바뀐 것이다. 왜 줄었는지 적고 명세를 갱신하라."
        )
        assert sum(observed.values()) == entry["expected_total"]


def test_public_notice_content_has_not_drifted():
    """본문이 바뀌었는데 명세가 그대로면 격리가 무의미해진다."""
    for entry in _manifest()["entries"]:
        text = _read(_REPO / entry["source_path"])
        assert _sha256(text) == entry["source_sha256"], (
            f"{entry['source_path']}: 본문이 바뀌었다. 격리 명세의 source_sha256 을 갱신하고 "
            f"무엇이 바뀌었는지 기록하라."
        )


def test_no_unregistered_file_carries_markers_in_public_notice_path():
    """공개 노티스 경로에 등록되지 않은 파일이 마커를 들고 들어오는 것을 막는다."""
    registered = {e["source_path"] for e in _manifest()["entries"]}
    offenders = []
    for p in sorted((_API / "content/legal").glob("public_*.md")):
        rel = p.relative_to(_REPO).as_posix()
        if rel in registered:
            continue
        if _count_markers(_read(p)):
            offenders.append(rel)
    assert not offenders, f"등록되지 않은 공개 문서에 미해결 마커가 있다: {offenders}"


# ── 3. publish_candidate 는 runtime source 가 될 수 없다 ────────────────────

def test_runtime_code_never_reads_publish_candidate():
    """★ 이번 사고의 구조적 원인.

    publish_candidate 는 법무 검토용 작업공간이다. 런타임이 거기서 직접 읽으면
    후보의 미완성이 그대로 공개된다. 승인·불변등록을 거친 artifact 만 서빙한다."""
    offenders = []
    for p in (_API / "app").rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        if _reads_publish_candidate(p):
            offenders.append(p.relative_to(_API).as_posix())
    assert not offenders, (
        f"런타임 코드가 publish_candidate 경로를 읽는다: {offenders}\n"
        f"  후보 문서는 승인 전 작업물이다. 직접 서빙 경로가 되면 안 된다."
    )


def test_tests_do_not_pin_runtime_to_publish_candidate():
    """테스트가 '런타임 == publish_candidate' 를 강제하면 오염 경로를 고정하게 된다.

    2026-08-26 ~ 2026-09-03 사이 실제로 그랬다(test_public_notice.py). 재발 방지."""
    offenders = []
    for p in (_API / "tests").rglob("*.py"):
        if "__pycache__" in p.parts or p.name == Path(__file__).name:
            continue
        # 산문의 언급은 허용한다 — 왜 그 계약을 제거했는지 기록해야 하기 때문이다.
        if _reads_publish_candidate(p):
            offenders.append(p.relative_to(_API).as_posix())
    assert not offenders, (
        f"테스트가 publish_candidate 를 런타임 정본으로 취급한다: {offenders}\n"
        f"  올바른 계약은 'runtime == 승인된 PUBLISHED artifact' 다."
    )


# ── 4. status != PUBLISHED 는 게시 경계를 넘지 못한다 ───────────────────────

def test_manifest_documents_are_not_claimed_published():
    """현재 manifest 8문서는 전부 DRAFT 다. PUBLISHED 를 참칭하지 않는지 고정한다.

    ★ 이 테스트는 '공개해도 된다' 는 뜻이 아니다. 문서가 자기 상태를 정직하게
      표시하고 있는지만 본다. 실제 차단은 아래 resolver 계약이 맡는다."""
    mfjson = json.loads(_read(_API / "content/legal/manifest.json"))
    for doc_id, meta in mfjson["documents"].items():
        status = meta.get("status", "")
        assert status.startswith("DRAFT"), (
            f"{doc_id} 의 status 가 {status!r} 다. PUBLISHED 로 올리려면 "
            f"승인 기록(DOCUMENT_APPROVED)과 불변 등록이 선행되어야 한다."
        )


def test_signup_plan_marks_draft_documents_as_draft():
    """가입 화면에 나가는 문서가 DRAFT 임을 서버가 스스로 신고하는지.

    any_draft 는 아직 차단 신호가 아니라 표시 신호다 — 그 사실을 고정해 두고,
    차단으로 승격하는 변경이 오면 이 테스트가 함께 바뀌게 한다."""
    from app.services import consent_service as cs

    plan = cs.build_signup_plan(
        selected_country="US", farm_country="US", farm_state=None,
        lang=None, include_body=False,
    )
    assert plan.any_draft is True, "manifest 가 전부 DRAFT 인데 any_draft 가 False 다"
    assert all(d.status.startswith("DRAFT") for d in plan.documents)
