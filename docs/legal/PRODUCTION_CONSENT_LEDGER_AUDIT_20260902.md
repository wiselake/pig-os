# PRODUCTION_CONSENT_LEDGER_AUDIT — 2026-09-02

> **성격**: 운영 DB 실측. `LEGAL_PUBLICATION_GAP_REPORT_20260902.md`(문서·구현·승인 gap)와 성격이 다르다.
> 이 문서는 **실제 운영 데이터에 어떤 consent evidence 가 존재하는가**만 다룬다.
> **집계만 기록한다** — user_id · 이메일 · 이름 · 농장명 · raw ledger dump 없음.

---

## AUDIT_MODE

```
target                  production  (api.pigos.io · 52.78.65.6)
접근                     pigos-api 컨테이너 내 asyncpg — DATABASE_URL 은 출력하지 않음
                        (DB 는 compose 외부. db 서비스 없음 → 컨테이너 자체 커넥션 사용)
transaction_read_only   true
read_only_enforced      true   ← 자기검증: 트랜잭션 내 쓰기 시도가 DB 에서 거부됨
                               probe: CREATE TEMP TABLE → ReadOnlySQLTransactionError
종료                     rollback
쓰기·migration·job 실행   0건
```

★ "SELECT 만 하겠다"는 선언이 아니라 **DB 가 쓰기를 거부하도록** 잠근 뒤 그것을 증명했다.

---

## TOTAL

```
consent_ledger rows     0
first_at                —
last_at                 —
distinct notice_version []   (빈 목록)
```

---

## PLACEHOLDER

```
notice_version ILIKE '%0.1-draft%'   rows = 0
jurisdictions                        —
statuses                             —
contexts                             —
```

---

## 대조군 — "0" 이 조회 오류가 아님을 확인

0건은 "아무도 동의하지 않았다"일 수도, "테이블·DB·코드가 잘못됐다"일 수도 있다. 분리했다.

```
consent_ledger 존재         true
consent_ledger 컬럼 수      15          ← 마이그레이션 적용됨
alembic head               f3c6a8d0b2e4  (d4a1b2c3e5f7 consent_ledger 이후)
consent 유사 테이블         consent_ledger 하나뿐 (agree/term 계열 없음)

배포된 코드
  app/routers/base/consent.py    2,365 B   2026-08-28 08:12
  app/db/models/consent.py       5,382 B   2026-08-28 08:12

users                      85          2026-06-26 ~ 2026-08-29
farms                      75          pigplan_migration 42 · native_signup 33
```

**스키마·코드·데이터가 모두 정상인 DB 에서 원장만 비어 있다.** 조회 오류가 아니다.

---

## ORIGIN

```
native_signup       33 farms      2026-07  17건 · 2026-08  16건 (최신 2026-08-29 22:46 UTC)
pigplan_migration   42 farms      최신 2026-07-20 (하베스트분)
account_scope/no_farm  N/A        ledger 가 비어 있어 집계 대상 없음
```

---

## FINDING

```
placeholder_rows_exist        NO
native_signup_exposure        NOT_ESTABLISHED
migration_only                N/A  (migration 유래 ledger 행도 0건)
historical_first_seen         —
```

### ★ 부수 발견 — `NATIVE_SIGNUP_WITHOUT_CONSENT_RECORD`

원래 질문 밖이지만 대조군에서 드러났다.

```
consent 코드 파일 배치       2026-08-28 08:12
그 이후 신규 계정            2 건        (2026-08-28 00:00 UTC 이후 기준)
그 이후 native_signup 농장    2 건
그중 배포 시각 이후가 확실한 건 ≥ 1 건   (2026-08-29 22:46 UTC)
대응하는 consent_ledger 행    0 건
```

즉 **consent 코드가 배포된 뒤에도 가입이 있었고 원장에는 아무 행도 남지 않았다.**

원인 후보는 최소 셋이며 이 감사만으로는 가르지 못한다.

```
① 그 가입이 iOS 였다              iOS 는 consent API 를 호출하지 않는다
                                 (LEGAL_PUBLICATION_GAP_REPORT §5)
② 코드가 디스크에만 있고 미가동     scp 배포 후 재기동 전이면 구 프로세스가 계속 돈다
                                 → PLATFORM_PARITY §9-5 P1 DEPLOY_PROVENANCE 와 같은 뿌리
③ 호출됐으나 실패                  기록 실패 시 가입은 통과하는 경로가 있었는가
```

★ **② 를 배제할 수 없다.** 현재 컨테이너 기동 시각이 `2026-08-31 00:52:16 UTC`(RestartCount 0,
`2e372b1` 배포)이고, 문제의 가입은 그 **이전**이다. 그때 돌던 프로세스는 사라졌고 로그도 남아 있지 않다.

★ **① 도 배제할 수 없다.** `consent_ledger` 에 `channel`(WEB/ANDROID/IOS) 컬럼이 없어
어느 클라이언트에서 온 가입인지 원장으로 판별할 수 없다 —
`LEGAL_PUBLICATION_GAP_REPORT` 의 `CONSENT_WITHOUT_CHANNEL`(P1)이 여기서 실제 비용으로 나타났다.

### 관측 공백

```
현재 컨테이너 기동      2026-08-31 00:52:16 UTC
그 이후 신규 가입        0 건
그 이후 consent 호출     0 건   (api 로그 전수 grep — GET/POST /api/v1/consent/* 매칭 0)
로그 보존 범위          현재 기동 시점 이후만. 2026-08-29 가입 시점 로그 없음
```

**재기동 이후로는 가입 자체가 없어 consent 기록이 동작하는지 관측할 기회가 없었다.**
"동작하지 않는다"가 아니라 **아직 관측되지 않았다**.

---

## VERDICT

```
PLACEHOLDER_CONSENT_PROD = NOT_FOUND
```

조회 시점(2026-09-02) 기준 production `consent_ledger` 에 `0.1-draft` 동의 기록은 **없다.**
"발생한 적이 없다"가 아니라 **현재 원장에 존재하지 않는다** — append-only 테이블이므로
삭제 흔적이 없는 한 사실상 같지만, 표현은 조회 시점 기준으로 유지한다.

부수 판정은 분리한다.

```
CONSENT_RECORDING_IN_PRODUCTION = INCONCLUSIVE
  근거   배포 후 가입 ≥1건에 대응하는 원장 행 0건
  제약   현재 컨테이너 기동 이전 사건 · 로그 소실 · channel 컬럼 부재
  구분   NOT_WORKING 이 아니라 UNOBSERVED/INCONCLUSIVE
```

---

## IMPLICATION

```
reconsent_decision_required = NO
```

placeholder 동의 기록이 0건이므로 **재동의 대상 자체가 존재하지 않는다.**
승인본 게시 시 기존 동의를 어떻게 처리할지 결정할 필요가 현재로선 없다.

이는 법무 트랙에 좋은 소식이다 — 승인·번역·연결을 마친 뒤 **깨끗한 상태에서** 첫 동의를 받을 수 있다.

### 다만 반대 방향의 문제가 남는다

```
placeholder 에 동의한 사용자        0 명
consent 기록이 아예 없는 가입자     최대 85 계정 / 33 native 농장
```

동의 원장이 비어 있다는 것은 **동의를 받은 증거가 없다**는 뜻이기도 하다. 서비스 운영(①)의
lawful basis 가 계약 이행이고 그 계약이 곧 약관인데, 약관 동의 기록이 없다.
이는 이번 감사의 판정 범위 밖이며 **별도 결정 사항**이다.

```
후속 결정 (법무/제품)
  기존 가입자에 대한 소급 동의 취득이 필요한가
  필요하다면 승인본 게시 후 일괄 고지·동의로 처리할 것인가
  → 개발이 정하지 않는다
```

---

## 다음 확인 (본 감사 범위 밖)

```
1  consent 기록이 실제로 동작하는가        재기동 이후 첫 가입에서 원장 행 생성 확인
                                          (강제 가입 생성 금지 — 자연 발생 관측)
2  2026-08-29 가입의 클라이언트            channel 컬럼이 없어 원장으로는 불가.
                                          앱 분석 이벤트 등 다른 경로 필요
3  DEPLOY_PROVENANCE                      PLATFORM_PARITY §9-5 P1 과 동일 뿌리.
                                          "무엇이 언제부터 돌고 있었는가" 기록 부재
```

---

## 근거

```
쿼리 1  SELECT count(*), min(created_at), max(created_at) FROM consent_ledger
쿼리 2  consent_ledger LEFT JOIN farms  GROUP BY notice_version, jurisdiction,
        collection_context, consent_status, purpose_code, data_origin
        ★ LEFT JOIN — farm_id 가 nullable 이고 목적①⑥ 은 account scope 라
          INNER JOIN 하면 실제 동의 행이 감사에서 누락된다
쿼리 3  WHERE notice_version ILIKE '%0.1-draft%'  GROUP BY ...
쿼리 4  대조군 — alembic_version · information_schema · users · farms.data_origin
자기검증 CREATE TEMP TABLE → ReadOnlySQLTransactionError (쓰기 거부 확인)
로그    docker logs pigos-api | grep -oE '(GET|POST) /api/v1/consent/...'  → 0건
기동    docker inspect pigos-api  StartedAt=2026-08-31T00:52:16Z  RestartCount=0
정리    업로드한 임시 스크립트 4개 삭제 (서버·컨테이너 양쪽)
```
