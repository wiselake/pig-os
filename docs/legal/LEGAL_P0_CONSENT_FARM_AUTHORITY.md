# LEGAL-P0-CONSENT-FARM-AUTHORITY

> **상태**: `CODE_COMPLETE / TESTED` · `PROD_NOT_DEPLOYED`
> **발견**: 2026-09-03, consent HTTP 계층 테스트 작성 중
> **승인**: 2026-09-03 개발 승인 (판단 4건 고정)
> **주의**: 코드가 닫혔다는 뜻이지 **서비스가 고쳐졌다는 뜻이 아니다.**
> push·deploy 0건이라 라이브 PigOS 는 여전히 임의 `farm_id` 를 받는다.

---

## 한 줄

인증된 사용자가 **자신의 소속 농장인지 검증 없이** 임의의 `farm_id` 를 제출해
동의 원장 행을 만들 수 있다.

---

> ⚠️ **아래 「종결 기록」 전까지는 발견 시점(2026-09-03 오전)에 쓴 원본이다.**
> 현재형으로 읽히지만 이미 지난 상태다 — "왜 지금 고치지 않았나"·characterization
> 테스트 언급은 **당시 기록**이며, 그 테스트는 예고대로 정상 계약으로 교체됐다.
> 지금 상태는 문서 맨 아래 「종결 기록」이다. 원본은 판단 근거로 보존한다.

## 결함

```
api/app/services/consent_service.py:163

    rec = ConsentRecord(
        user_id=user_id, farm_id=req.farm_id, ...
                         ^^^^^^^^^^^^^^^^^^
                         요청 본문의 값을 그대로 쓴다
    )
```

라우터([`consent.py:44`](../../api/app/routers/base/consent.py))는 `current_user` 를 넘기지만
`req.farm_id` 는 검증 없이 통과한다. `/consent/withdraw` 도 같은 `farm_id` 를 받는다.

### 영향

```
기밀성 유출        현재 확인된 바 없음
                   읽기(current_consents)는 user_id 로 걸린다. 남의 동의를
                   보거나 바꾸지는 못한다.

권한 경계          깨진다. 인증만 하면 임의 농장에 쓰기가 된다.

법적 원장 무결성   깨질 수 있다. ★ 이것이 본질이다 —
                   원장은 "누가 · 어느 농장에 대해 · 무엇에 동의했는가" 의
                   증거물이다. 귀속 농장이 틀린 행이 섞이면 그 원장으로는
                   아무것도 증명하지 못한다.
```

### ★ CONSENT-EVIDENCE 보다 먼저 닫아야 한다

`LEGAL-P0-CONSENT-EVIDENCE` 는 locale·channel·document hash·plan snapshot 을
원장에 더 정확히 남기는 작업이다. 그러나 **귀속 농장이 틀리면 그 정교한 증빙 전체가
틀린 것**이다. 잘못된 대상에 완벽하게 서명한 문서는 증거가 아니다.

따라서 순서는 `FARM-AUTHORITY` → `CONSENT-EVIDENCE` 다. 반대로 하면 evidence 필드를
추가한 마이그레이션 이후에 귀속 오류를 고치게 되고, 그때는 이미 쌓인 행의
정정 범위가 넓어진다.

---

## 왜 지금 고치지 않았나

권한 경계 변경이다. 밤샘 자율 RUN 의 하드규칙(`권한 손대면 멈추고 리포트`)에 걸린다.
자율 판단으로 열고 닫을 성질이 아니다.

현재 상태는 테스트로만 고정돼 있고, **사양이 아니라 결함 재현임을 명시**했다.

```
api/tests/integration/test_consent_http_contract.py
  ::test_characterization_known_defect_record_accepts_foreign_farm_id
```

이름과 docstring 양쪽에 `CHARACTERIZATION / KNOWN_DEFECT` 를 박아두었다. 결함이
닫히면 이 테스트는 삭제되거나 403 기대로 교체된다 — 실패 메시지가 그 절차를 안내한다.

---

## 고치는 데 필요한 것 — 스키마 변경 불필요 (실측 확인)

기존 관계와 헬퍼가 이미 있다. 새 테이블도, 마이그레이션도 필요 없다.

```
api/app/db/models/platform.py:144    UserFarm            사용자↔농장 명시 소속
api/app/core/dependencies.py:71      get_farm_context    "organization hierarchy 또는
                                                          user_farms membership" 검증
api/app/core/permissions.py          get_accessible_farm_ids(user, db)
```

즉 구현은 "새 권한 모델 설계"가 아니라 **이미 다른 라우터가 쓰는 검증을 동의 경로에도
적용**하는 일이다.

### 결정할 것 (개발 승인 사항)

| # | 항목 | 후보 |
|---|---|---|
| 1 | 요구할 관계 | `get_accessible_farm_ids` 재사용(org 계층 + user_farms) / UserFarm 직접 소속만 |
| 2 | 거부 상태코드 | 403(권한 없음) — 404 로 존재를 숨길지 여부 |
| 3 | `farm_id` 누락 허용 | `withdraw` 는 `farm_id: UUID \| None` 이다. None 을 계속 허용할지 |
| 4 | 기존 행 | 잘못 귀속된 행이 실제로 있는지 **먼저 조회**(집계만). 있으면 정정 범위 별도 결정 |

★ `4` 는 조회가 선행이다. 프로덕션 `consent_ledger` 는 0행으로 관측됐으므로
(`PRODUCTION_CONSENT_LEDGER_AUDIT_20260902.md`) 정정 대상이 없을 가능성이 높지만,
**"없을 것이다"로 넘기지 않고 확인 후 적는다.**

---

## 하면 안 되는 것

```
동의 화면 자체를 막지 말 것        가입 직후 흐름이 깨진다. 막는 것은 "남의 농장"이지
                                   "자기 농장에 대한 동의"가 아니다

signup 경로 회귀 주의              LEGAL-P0-WEB-CONSENT-FAIL-CLOSED 는 record 성공을
                                   로그인 확정 조건으로 삼는다. 여기서 403 이 잘못
                                   나면 정상 가입이 전부 막힌다 —
                                   방금 만든 farm_id 가 반드시 통과해야 한다

withdraw 를 같이 보라              record 만 고치면 withdraw 로 같은 일을 할 수 있다
```

---

## 선행/후행

```
선행   개발 승인 (사람 결정·법무 빈칸 아님)

후행   LEGAL-P0-CONSENT-EVIDENCE    귀속이 옳아진 뒤에 증빙을 정교화한다
관련   LEGAL-P0-MANDATORY-CONSENT-LOGIN-GATE   원장 신뢰성을 함께 좌우한다
```

---

## 관련

```
api/app/services/consent_service.py:163                  결함 위치
api/app/routers/base/consent.py:44,59                    farm_id 를 받는 두 엔드포인트
api/tests/integration/test_consent_http_contract.py      characterization 재현
docs/legal/PRODUCTION_CONSENT_LEDGER_AUDIT_20260902.md   프로덕션 원장 0행 실측
ef739d1                                                  결함을 기록한 커밋
```


---

# 종결 기록 (2026-09-03)

## 승인된 판단 4건 → 구현 결과

| # | 결정 | 구현 |
|---|---|---|
| 1 | 기존 farm-scoped API 의 canonical semantics 재사용 | `can_access_farm` 을 그대로 호출. 법무 전용 규칙·UserFarm 직접 조회 **신설 없음** |
| 2 | `get_farm_context` 의 실패 semantics 재사용 | **403** (`ForbiddenError`). ★ 조건부 지시("404로 숨긴다면 404")의 전제는 성립하지 않았다 — canonical 은 없는 농장·비활성·접근불가를 **모두 403** 으로 처리하며 404 로 숨기지 않는다 |
| 3 | `withdraw(farm_id=None)` 허용 유지 | 유지. 계정 스코프 철회 경로 보존 |
| 4 | 기존 잘못 귀속 행 — prod SELECT-only 선행 | **`HISTORICAL_MISATTRIBUTION = NOT_FOUND`** (아래) |

## prod 집계 — 코드 변경 **전** 실행

```
read_only_probe         ReadOnlySQLTransactionError   ← 쓰기가 DB 에서 거부됨을 증명
transaction_read_only   on
consent_ledger rows     0
attribution buckets     (분류할 행 없음)

대조군   farms 75 · users 85 · user_farms 78 · orgs 73
```

대조군이 0 이 아니므로 스키마를 잘못 본 0 이 아니다. 임시 스크립트는 서버·컨테이너
양쪽에서 삭제했다. 과거 관측을 근거로 "없음" 처리하지 않고 실제로 조회했다.

## 듀얼 리뷰에서 잡힌 것 — 1차 구현은 불완전했다

context-aware · fresh-context 리뷰어를 병렬로 돌렸고, **양쪽이 독립적으로**
1차 구현의 결함 2건을 찾았다. 재검증 후 전부 수정했다.

```
C1  consent_service 의 "미사용" settings import 제거가 테스트를 깨뜨렸다
    test_consent_record_context 가 monkeypatch 문자열로 그 이름을 짚고 있었다.
    ruff 는 문자열 patch 대상을 볼 수 없다. → patch 대상을 실제 소유 모듈
    (app.core.config.settings)로 정정. 그 alias 는 4a64da8 이후 무관해진 것이었다

C2  withdraw(farm_id=None) 이 prev.farm_id 를 무검증 상속했다
    farm_id 를 빼는 것만으로 검증을 건너뛰고 접근 불가 농장에 귀속된 행을
    새로 만들 수 있었다. 도달 경로가 실재한다 — 결함기 행, 그리고
    account_deletion_service 가 owner 삭제 시 farm.active=False 로 만들어
    남은 공동 멤버가 접근을 잃는 경우. → 상속분도 같은 기준으로 검증
```

테스트 2건은 docstring 이 실제 assert 보다 과장돼 있어 바로잡았다
(`..._keeps_account_scope` 는 직전 행이 farm-scoped 라 정반대를 기록하고 있었다).

## 남은 결정 — 개발이 단독으로 정하지 않는다

```
INACTIVE_FARM_WITHDRAWAL   canonical 은 f.active = TRUE 를 요구한다. 그래서 농장이
                           비활성화되면 그 농장 스코프 동의를 **철회**할 수도 없다(403).
                           record 는 그게 맞지만, 철회는 정보주체의 권리라
                           테넌트 수명주기에 종속시키는 게 옳은지는 법무 판단이다.
                           현재는 canonical 을 그대로 따랐다(일관성·fail-closed).

ORG_ADMIN_ATTRIBUTION      canonical 은 조직레벨 롤(VENDOR/DISTRIBUTOR/DEALER_ADMIN)
                           에게 서브트리 농장 접근을 준다. 따라서 대리점 관리자가
                           고객 농장에 귀속된 자기 동의 행을 남길 수 있다.
                           승인 조건이 "canonical 을 그대로 따른다" 였으므로
                           의도된 결과이나, 원장 귀속 관점에서 좁힐지는 별도 판단.
                           현재 소비자는 없다(current_consents 는 user_id 로 거른다).

ACCOUNT_SCOPE_PURPOSE_SET  farm_id=None 이면 **모든** 가시 목적이 NULL 로 기록된다.
                           모델 주석은 farm 단위 목적(②③④⑤)에 farm_id 필수라고
                           적고 있어 서로 어긋난다. LEGAL-P0-CONSENT-EVIDENCE 소관.
```

## ★ 이 P0 를 닫는 과정에서 발견된 별건

`LEGAL-P0-CONSENT-LEDGER-NOT-PERSISTED` — consent 라우터가 commit 을 하지 않는다.
**귀속을 옳게 만들어도 애초에 저장되지 않으면 의미가 없다.** 별도 문서 참조.
