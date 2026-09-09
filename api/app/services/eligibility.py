"""국가 진입 허용 판정 — LEGAL-P0-CONSENT-AUTHORITY.

## 왜 생겼나 (2026-09-03 실측)

국가 차단이 `POST /consent/record` **안에서만** 걸려 있었다.

    api/app/routers/base/auth.py         jurisdiction 호출 0건
    api/app/routers/base/onboarding.py   jurisdiction 호출 0건

그래서 **동의 API 를 호출하지 않는 것만으로 국가 차단까지 우회**됐다. iOS main 이
실제 반례다 — consent 호출 0건인데 가입이 된다. 클라이언트가 법적 권한 경계를
쥐고 있으면 구버전·미배선·악성 클라이언트가 전부 통과한다.

## 이 모듈이 판정하는 것 / 하지 않는 것

    판정함   국가 자체의 hard block (CN=HOLD_D07 · KR=KR_REFERENCE_ONLY)
             allow_kr_signup override
             selected_country + farm_country 결합 법역

    판정 안 함   consent_ledger row 존재       ← 순환이다. 아래 참조
                국가별 부속조항 동의 여부
                목적별 선택동의 완료
                locale·hash 증빙

★ **가입 자격(eligibility)과 동의 완료(consent completion)는 다르다.**
  `POST /consent/record` 는 인증 엔드포인트라 토큰이 필요하고, 토큰은 register
  이후에 나온다. register 에 ledger row 존재를 요구하면 영원히 가입할 수 없다.
  동의 완료 강제는 별도 계층(WEB_CONSENT_FAIL_CLOSED · CONSENT_EVIDENCE)이 맡는다.

## override 는 여기 한 곳에서만 만든다

`consent_service` 가 같은 override 를 따로 구성하고 있었다. 두 곳이 갈라지면
"동의 화면은 막는데 가입은 뚫리는" 상태가 다시 생긴다. 그래서 구성 자체를
`feature_overrides()` 로 공용화하고 양쪽이 이것만 쓴다.

                     jurisdiction.resolve()
                              ↑
                  eligibility (이 모듈)
                              ↑
              ┌───────────────┼───────────────┐
            auth          onboarding        consent
"""
from __future__ import annotations

from fastapi import HTTPException

from app.core.config import settings
from app.services import jurisdiction as jz
from app.services.terms_renderer import build_document_set


def feature_overrides(extra: dict[str, bool] | None = None) -> dict[str, bool]:
    """게이트 해제 플래그 — **단일 출처**.

    KR 은 레퍼런스 전용이라 운영 기본 차단이고, 대표 확인용 환경에서만
    `allow_kr_signup`(서버 env)으로 열린다. 서버 env 라 클라이언트가 우회할 수 없다.
    """
    return {"KR_signup": settings.allow_kr_signup, **(extra or {})}


def resolve_entry(
    *,
    selected_country: str,
    farm_country: str | None = None,
    farm_state: str | None = None,
    extra_overrides: dict[str, bool] | None = None,
) -> jz.Jurisdiction:
    """법역 판정만. 차단하지 않는다(조회용)."""
    return jz.resolve(
        selected_country=selected_country,
        farm_country=farm_country,
        farm_state=farm_state,
        feature_overrides=feature_overrides(extra_overrides),
    )


def assert_country_entry_allowed(
    *,
    selected_country: str,
    farm_country: str | None = None,
    farm_state: str | None = None,
    extra_overrides: dict[str, bool] | None = None,
) -> jz.Jurisdiction:
    """국가 진입이 허용되는지 확인하고, 막혔으면 451 로 거부한다.

    ★ 이름이 `signup` 이 아닌 이유: `/onboarding/farm` 은 최초 가입뿐 아니라
      **기존 계정의 추가 농장 생성**에도 쓰인다. signup 이라고 부르면 몇 달 뒤
      의미가 틀어진다.

    ★ 호출 위치: **첫 DB write/flush 이전.** 451 을 던진 뒤 rollback 에 기대지
      않는다. 부분 생성된 org·user 가 남을 여지를 애초에 만들지 않는다.

    Args:
        selected_country: 계정·조직의 국가 (가입 시 선택 국가)
        farm_country:     농장 국가. 계정 국가와 다를 수 있다 —
                          US 계정 + BR 농장을 단순히 selected_country=BR 로 넣으면
                          기존 cross-jurisdiction 판정(더 엄격한 쪽 채택 + counsel)
                          의미를 잃는다.
    """
    j = resolve_entry(
        selected_country=selected_country,
        farm_country=farm_country,
        farm_state=farm_state,
        extra_overrides=extra_overrides,
    )
    if j.gate.signup_blocked:
        # 기존 consent_service 와 동일한 에러 계약을 쓴다 — 클라이언트가 이미
        # 이 형태를 처리하고 있어 새 status·포맷을 발명하지 않는다.
        raise HTTPException(451, f"SIGNUP_BLOCKED:{j.gate.reason_code}")
    return j


def assert_publication_approved(j: jz.Jurisdiction) -> None:
    """해당 법역의 게시 문서가 전부 승인본인지 확인하고, 아니면 451 로 거부한다.

    ## 왜 (G-3 · 2026-09-09 대표 결정 (나))

    `any_draft` 는 이미 계산되고 있었지만 **소비처가 프론트 배너 하나뿐**이었다.
    즉 초안 상태에서도 동의가 그대로 접수됐고, `consent_ledger.notice_version` 에
    초안 버전이 적혔다. 배포 대기 중인 두 수정이 이 경로를 강화한다 —
    `557a347`(원장 commit)·`e064e60`(기록 실패 시 가입 차단). 둘 다 옳은 수정인데,
    **게시 정본이 잘못된 상태에서 증거 능력만 올린다.**

    승인 안 된 문서에 동의를 받는 것보다 신규 가입을 잠시 막는 쪽을 택했다.
    (제품·운영 리스크 판단. 법률 판단이 아니다 —
     `docs/legal/DEPLOY_GATE_20260910.md` §7)

    ## 호출 위치 — ★ 첫 DB write 이전

    `record_consents` 에서만 막으면 **계정은 이미 만들어진 뒤 동의에서 실패**한다.
    그러면 가입이 멈추는 게 아니라 고아 계정이 쌓인다(H11). 그래서 계정을 만드는
    두 진입점(`/auth/register` · `/onboarding/complete`)에서 먼저 막는다.

    ## 막지 않는 것

        /onboarding/farm    기존 계정의 농장 추가 — 동의를 수집하지 않는다.
                            여기까지 막으면 중단 범위가 불필요하게 넓어진다.
        철회(withdraw)      승인 여부와 무관하게 언제나 가능해야 한다.
    """
    doc_set = build_document_set(jurisdiction_code=j.code, group=j.group)
    if doc_set.any_draft:
        # 451 계약을 재사용한다 — 프론트가 detail 을 그대로 보여주는 경로가 이미 있다.
        raise HTTPException(451, "PUBLICATION_NOT_APPROVED")
