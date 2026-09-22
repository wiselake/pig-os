"""가입 게이트 회귀 — `8a80ea4`(Lou, origin/main) 의 16 케이스를 canonical 경로로 이식.

## 왜 이 파일이 있나 (B-9)

`origin/main` 에만 있는 `8a80ea4` 는 같은 문제를 다른 진입점으로 풀었다:
`jurisdiction.signup_overrides · resolve_for_signup · assert_signup_allowed`.
이쪽 계보는 `eligibility` 파사드(`feature_overrides · resolve_entry ·
assert_country_entry_allowed`)로 풀었고, G-3(게시 승인)·H13(개시 허용목록)이
그 파사드 위에 얹혀 있다.

**둘 다 남기면 가입 허용 판단이 두 군데가 된다.** 그래서 구현은 `eligibility` 하나로
확정하고(B-9 결정), 저쪽 **테스트 자산만** 가져온다. 프로덕션 코드는 복사하지 않았다.

★ 원본을 없던 일로 만들지 않는다. `8a80ea4` 는 origin 에 그대로 보존돼 있고, 그 커밋이
  잡으려던 회귀 — "게이트가 `/consent/record` 한 곳에만 있어 차단 법역에서도 계정은
  만들어지고 동의만 451" — 는 이 저장소에서도 실재했다(H11). 여기서 그 의도를 잇는다.

## 이식 매트릭스 — 16 케이스 중 무엇이 새것인가

```
이미 canonical 에 있음 (test_country_entry_authority.py)
  CN 451 HOLD_D07                     :68  test_cn_register_is_blocked_and_creates_nothing
  KR 451 KR_REFERENCE_ONLY            :99  test_kr_is_blocked_when_override_off
  env override 로 KR 해제             :110 test_kr_is_allowed_when_override_on
  농장국이 더 엄격하면 그쪽 적용       :131 test_us_account_cn_farm_is_blocked
  override 출처가 하나                :117 test_override_source_is_shared_not_duplicated
  진입경로들이 같은 국가 판정          :195 test_all_entry_paths_agree_on_the_same_country

여기서 새로 고정 (저쪽에만 있던 것)
  1  소문자 국가코드 정규화
  2  차단 note 가 그 국가를 지목한다 (KR 인데 CN 이라 적히던 버그)
  3  plan.gate 와 파사드 assert 의 판정 일치 — 국가별 전수
  4  ★ 이중 게이트 부재 — jurisdiction 에 두 번째 공개 assert 가 생기지 않는다

의도적으로 이식하지 않음
  "US·BR·DE·GB·TH·VN·AU 는 전부 통과" — H13(4) 개시 허용목록 이후 거짓이다.
  지금은 US 만 열려 있고 나머지는 LAUNCH_NOT_ENABLED 다. 저 케이스를 그대로 옮기면
  H13 결정을 테스트가 되돌리는 셈이 된다. 대신 그 사실 자체를 아래에서 고정한다.
```
"""
import pytest
from fastapi import HTTPException

from app.services import eligibility as el
from app.services import jurisdiction as jz


@pytest.fixture(autouse=True)
def _lock_kr(monkeypatch):
    """운영 기본값(allow_kr_signup=False)으로 고정. conftest 의 autouse override 를 끈다."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "allow_kr_signup", False)


# ── 1. 소문자 정규화 ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw", ["kr", "Kr", "cn"])
def test_lowercase_country_is_normalized_before_the_gate(raw):
    """클라이언트가 소문자로 보내도 차단은 지켜진다.

    정규화가 게이트보다 뒤에 있으면 `?country=kr` 한 줄로 우회된다.
    """
    with pytest.raises(HTTPException) as ei:
        el.assert_country_entry_allowed(selected_country=raw)
    assert ei.value.status_code == 451


def test_lowercase_does_not_change_the_reason_code():
    upper = jz.resolve(selected_country="KR", feature_overrides=el.feature_overrides())
    lower = jz.resolve(selected_country="kr", feature_overrides=el.feature_overrides())
    assert upper.code == lower.code
    assert upper.gate.reason_code == lower.gate.reason_code == "KR_REFERENCE_ONLY"


# ── 2. 차단 note 가 그 국가를 지목한다 ─────────────────────────────────────────
#
# 원본 회귀: note 에 'signup blocked (CN, D-07 HOLD)' 가 하드코딩돼 KR 차단에도
# CN 이 찍혔다. 사유 문자열이 틀리면 운영 로그·감사에서 엉뚱한 법역을 쫓는다.

@pytest.mark.parametrize("country,reason,wrong", [
    ("KR", "KR_REFERENCE_ONLY", "CN"),
    ("CN", "HOLD_D07", "KR"),
])
def test_blocked_note_names_its_own_country(country, reason, wrong):
    j = el.resolve_entry(selected_country=country)
    note = " ".join(j.notes)
    assert reason in note, note
    assert wrong not in note, f"{country} 차단인데 note 에 {wrong} 이 적혔다: {note}"


# ── 3. plan 과 파사드가 같은 판정 ─────────────────────────────────────────────

@pytest.mark.parametrize("country", ["KR", "CN", "US", "BR", "DE", "AU"])
def test_signup_plan_gate_matches_the_facade(country):
    """UI 플랜과 서버 게이트가 갈라지면 화면과 서버가 어긋난다.

    ★ 판정 값을 이 테스트에 적지 않는다 — 두 경로가 **서로** 같은지만 본다.
      값을 적으면 H13 결정이 바뀔 때 이 파일이 결정을 되돌리는 쪽이 된다.
    """
    from app.services import consent_service as cs

    plan = cs.build_signup_plan(
        selected_country=country, farm_country=country,
        farm_state=None, lang="en", include_body=False,
    )
    try:
        el.assert_country_entry_allowed(selected_country=country)
        blocked_by_facade = False
    except HTTPException as e:
        assert e.status_code == 451
        blocked_by_facade = True
    assert plan.gate.signup_blocked is blocked_by_facade, country
    if blocked_by_facade:
        assert plan.gate.reason_code, f"{country} 차단인데 사유코드가 비었다"


# ── 4. ★ 이중 게이트 부재 ─────────────────────────────────────────────────────

def test_jurisdiction_exposes_no_second_signup_assert():
    """B-9 결정: 가입 허용 판단의 공개 진입점은 `eligibility` 하나다.

    `jurisdiction` 은 순수 정책 계층(lookup·resolve)으로 남는다. 여기에 451 을 던지는
    두 번째 assert 가 생기면 호출부마다 어느 쪽을 쓰는지 갈리고, G-3·H13 이 한쪽에만
    얹혀 "동의 화면은 막는데 가입은 뚫리는" 상태가 다시 만들어진다
    (LEGAL-P0-CONSENT-AUTHORITY 가 실제로 겪은 것).

    ★ 이름 목록이 아니라 **동작**으로 본다: jurisdiction 의 공개 함수 중 HTTPException 을
      던지는 것이 있으면 실패한다.
    """
    import inspect

    src = inspect.getsource(jz)
    offenders = []
    for name, fn in vars(jz).items():
        if name.startswith("_") or not inspect.isfunction(fn):
            continue
        if getattr(fn, "__module__", None) != jz.__name__:
            continue
        body = inspect.getsource(fn)
        if "HTTPException" in body or "raise HTTPException" in body:
            offenders.append(name)
    assert not offenders, (
        f"jurisdiction 이 451 을 던지는 공개 함수를 노출한다: {offenders}. "
        "가입 차단은 eligibility.assert_country_entry_allowed 하나로만 한다 (B-9)."
    )
    assert "HTTPException" not in src, (
        "jurisdiction 은 순수 정책 계층이다 — HTTP 계약을 여기서 만들지 않는다 (B-9)"
    )


def test_facade_is_the_only_override_source():
    """`allow_kr_signup` 을 읽는 곳이 둘이면 한쪽만 바뀐다.

    원본 구현은 `jurisdiction.signup_overrides` 에서 같은 설정을 다시 읽었다.
    canonical 은 `eligibility.feature_overrides` 하나다.
    """
    import ast
    import inspect

    assert "allow_kr_signup" in inspect.getsource(el.feature_overrides)

    # ★ 문자열 검색이 아니라 **설정 접근**을 본다. jurisdiction 은 주석에서
    #   allow_kr_signup 을 설명하고 있고(65·154행) 그것은 문제가 아니다.
    #   문제는 settings 를 import 하거나 그 속성을 읽는 것이다.
    tree = ast.parse(inspect.getsource(jz))
    reads_settings = any(
        (isinstance(n, ast.ImportFrom) and n.module == "app.core.config")
        or (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
            and n.value.id == "settings")
        for n in ast.walk(tree)
    )
    assert not reads_settings, (
        "jurisdiction 이 settings 를 직접 읽는다 — override 출처가 둘이 된다 (B-9)"
    )


# ── 5. H13 이후의 실제 상태 — 저쪽 '전부 통과' 케이스를 대체한다 ──────────────

def test_launch_allowlist_is_the_reason_open_countries_are_now_closed():
    """`8a80ea4` 의 "US·BR·DE·GB·TH·VN·AU 전부 통과" 는 H13(4) 이후 거짓이다.

    지금 막히는 사유가 **법역 정책이 아니라 개시 허용목록**임을 명시한다 — 둘은 해소
    조건이 다르다. CN·KR 은 법무 결정(D-07·A-rule)이고, 나머지는 H13 한 문장이다.
    """
    kr = el.resolve_entry(selected_country="KR")
    cn = el.resolve_entry(selected_country="CN")
    assert kr.gate.reason_code == "KR_REFERENCE_ONLY"
    assert cn.gate.reason_code == "HOLD_D07"

    for country in ("BR", "DE", "GB", "TH", "VN", "AU"):
        j = el.resolve_entry(selected_country=country)
        if j.gate.signup_blocked:
            assert j.gate.reason_code == "LAUNCH_NOT_ENABLED", (
                f"{country} 가 개시 허용목록이 아닌 사유로 막혔다: {j.gate.reason_code}"
            )


def test_paid_and_release_holds_are_not_signup_blocks():
    """유료차단(TH·VN)·릴리스보류(EU·GB·BR)는 그 자체로 가입을 막지 않는다.

    저쪽 케이스의 핵심은 "게이트 종류를 섞지 않는다" 였고 그것은 지금도 참이다.
    허용목록으로 열어 보면 남는 차단이 없어야 한다.
    """
    for country in ("TH", "VN", "DE", "GB", "BR"):
        j = el.resolve_entry(
            selected_country=country,
            extra_overrides={f"LAUNCH_{country}": True},
        )
        assert not j.gate.signup_blocked, (
            f"{country}: 개시 허용 후에도 막힌다 — {j.gate.reason_code}"
        )
