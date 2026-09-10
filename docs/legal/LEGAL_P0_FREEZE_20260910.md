# 법무 P0 트랙 동결 — 2026-09-10

> **RUN**: `LEGAL-P0-FREEZE-AND-QUARANTINE` · machine `bjh`
> **성격**: 상태 기록. **새 조사·새 측정 없음.** 기존 문서·커밋에서만 인용한다.
> **산출**: 이 문서 · 코드 로직 변경 0 · push 0 · 배포 0 · 프로덕션 쓰기 0
>
> ★ **이 문서는 어떤 게이트도 열지 않는다.** H13·H14·변호사 회신은 코드로 닫히지 않는다.

---

## 0. 한 줄

```
목표      PigOS 를 미국에서 합법적으로 가입받을 수 있는 상태로 만드는 것. 그 하나.
현재      개발이 닫을 수 있는 것은 전부 닫혔다. 남은 것은 전부 사람 결정이다.
배포      0건. 프로덕션은 아직 아무것도 바뀌지 않았다.
```

---

## 1. 게이트 현황 (B-1)

| # | 게이트 | 상태 | 근거 |
|---|---|---|---|
| **G-1a/G-1b** ★ | 문안·구조(대표) / 법률 확인(변호사) — 2026-09-10 분할 | `G-1a` 구두 승인·택일 3건 미결 / `G-1b` HUMAN DECISION REQUIRED | manifest 8건 `DRAFT_LAWYER_PENDING` · H13 |
| **G-2** | 게시 언어 | `HUMAN / LEGAL DECISION REQUIRED` | addendum 전부 en · 공개 고지 ko·en · H14 |
| **G-3** | 초안 동의 차단 | `CODE_COMPLETE / TESTED · PROD_NOT_DEPLOYED` | `320baea` · `587dfed` · `f0934c0` |
| **G-4** | 코드 배포 | `READY` | 대상 sha 5건 확정 · 롤백 단위 확정 (`07d0f94`) |
| **G-5** | 기존 사용자 재동의 | `DEFERRED` — 이번 배포 완료 판정에서 분리 | `LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md` `OPEN` |
| **G-6** | 적재 확인 | 배포 후 검증 | — |

★ **`CODE_COMPLETE` 은 "서비스가 고쳐졌다"가 아니다.** G-3 는 로컬 커밋에만 있고,
프로덕션은 여전히 초안 문서로 동의를 받는다 — 다만 `557a347` 이 배포되지 않아
원장에 남지 않을 뿐이다.

---

## 2. 코드로 닫힌 것 / 사람이 닫아야 할 것 (B-2)

### 2-1. 코드로 닫혔다 — 배포만 남았다

```
320baea  G-3 게시 게이트
         assert_publication_approved — /auth/register · /onboarding/complete
         첫 DB write 이전 + record_consents 심층 방어
         ★ 철회·농장추가는 의도적으로 제외

587dfed  부분 승인 동작 고정 — 법역별 열림/닫힘 + OTHER 동반 개방

f0934c0  차단 안내 문구 8 로케일 — 원문 코드 대신 사유를 보여준다

배포 대기 법무 5건 (07d0f94 §5-2)
  90e1284  미지원국 기본 목적② OFF (MASTER §10③)
  4a64da8  국가 진입 서버 강제
  e064e60  웹 가입 fail-closed
  f4d9c3f  동의 원장 쓰기 전 농장 권한 검사
  557a347  동의 쓰기 commit
```

### 2-2. 사람이 닫아야 한다

| # | 항목 | 담당 | 선행조건 |
|---|---|---|---|
| H13 | `CURRENT_PUBLICATION_SET` — (1)/(2)/(3) 택일 | **Brian** | 없음. 오늘 가능 |
| — | US 3종 회신 (`MASTER_TERMS`·`GLOBAL_PRIVACY_NOTICE`·`ADDENDUM_US`) | **변호사** | 요청 범위 좁히기 — Brian |
| H14 | 게시 언어 — BR·TH·VN 을 열 것인가 | Brian + 변호사 | pt-BR·th·vi 번역 (하루짜리 아님) |
| H11 | 원장 없는 기존 계정 처리 | Brian + 법무 | 배포 후 |
| H12 | 차단 국가 기존 계정 로그인 허용 | Brian | — |
| — | manifest status 갱신 | 개발 | H13 + 변호사 회신 |

★ **H14 는 오늘 결정하지 않아도 된다.** US 로 여는 순간 H14 는 마감 없는 항목이 된다.

---

## 3. H13 이 여는 실제 범위 (B-3)

```
"US 3종 승인" = MASTER_TERMS + GLOBAL_PRIVACY_NOTICE + ADDENDUM_US
```

이것이 여는 범위는 **US 하나가 아니다.**

```
열림    US                        group=US
        MX · CL · CO · JP …       group=OTHER — 부속조항이 없어 문서 세트가 두 건뿐
차단    BR · VN · TH · EU · GB    각자 addendum 이 DRAFT
차단    KR · CN                   기존 국가 게이트 (변동 없음)
```

`build_document_set` 이 MASTER + PRIVACY + **그 법역의 addendum 하나**만 담기
때문이다(`terms_renderer.py:92-95`). `OTHER` 에는 적용할 부속조항이 없으므로
그 둘이 곧 완전한 세트가 된다 — **게이트가 틀린 게 아니라 설계대로다.**

★ 그리고 `CLAUDE.md` 가 **스페인어권·러시아어권 CIS 를 "리서치·부속조항 미비"**
로 적어둔 그 시장이 정확히 `OTHER` 다.

### (2) OTHER 차단을 택할 경우

```
방법     app/services/jurisdiction.py:63 _GATES 에 "OTHER" 한 줄 추가
         ★ 게이트가 국가가 아니라 **그룹** 단위다(`:127` gate = _GATES.get(group))
         → 국가를 하나도 열거하지 않는다

범위     ★ "OTHER 전부" 로 둔다. 개별 국가 선별은 하지 않는다 —
         고르는 행위 자체가 리서치 없는 판단이 된다
```

★ **미적용.** `_GATES` 는 정책이 코드에 들어간 자리이고, `CLAUDE.md` 는 승인되지
않은 정책을 코드·seed 에 반영하는 것을 금지한다. H13 결재 후 적용한다.

### 결재 전 알아야 할 대가

2026-09-08 실측 실고객 23농장의 국가 분포다.

```
US 11 · MX 5 · KR 4 · CN 2 · VN 1 · PH 1 · BR 1
```

`MX`·`PH` 는 둘 다 `OTHER` 다. **(2)는 리서치 미비 시장을 닫는 동시에 US 다음으로
큰 유입원을 닫는다.** 결재 문장은 "리서치 안 된 시장을 열지 않는다"와
**"이미 유입 중인 MX·PH 를 닫는다"** 양쪽으로 읽혀야 정확하다.

---

## 4. 배포 순서 (B-4)

`DEPLOY_GATE_20260910.md` §7 의 확정본. 각 단계는 앞 단계가 참일 때만 의미가 있다.

```
1   H13 확인
2   H14 확인 — US 경로면 오늘 불필요
3   둘 중 필요한 것이 미결정  →  배포 STOP
4   manifest / publication set 갱신
5   롤백 지점 고정 — 현 배포본 2e372b1 (마이그레이션 0건)
6   원격 반영 (push — 현재 0건)
7   프로덕션 배포        ★ prod alembic 금지
8   —
9   ★ G-3 게이트가 실제로 **열리는지** 확인 — **두 법역**
      승인 법역 성공 1건 (예: US 201)
      addendum 보유 법역 차단 1건 (예: BR 451)
      ★ MX 로 차단 확인 금지 — OTHER 는 US 와 함께 열린다
      ★ 열림만 보면 게이트가 통째로 꺼진 것과 구분되지 않는다
10  full test
11  신규 가입 smoke — 9 와 같은 확인을 프로덕션에서 반복
12  consent_ledger 의 document / version 확인
```

★ **게이트가 닫힌 채 배포되면 서비스가 전면 중단되고, 그것은 코드가 의도대로
동작한 결과라 장애처럼 보이지 않는다.** 롤백 판단이 늦어지는 경로가 여기다.

---

## 5. 미해결 실측 항목 (B-5)

전부 **기존 측정의 인용**이다. 이 RUN 에서 새로 재지 않았다.

```
라이브 게시 고지의 미해결 표기
  api.pigos.io/legal/privacy?lang=en · ?lang=ko
  V 11 · OPEN 10 · COUNSEL 1 · EMPTY_BRACKET 2  = 24
  → 격리 중(KNOWN_PUBLICATION_EXPOSURE). 2026-09-17 로 1차 연장(b2eb30c)

동의 원장
  consent_ledger 0행. 원인 = 커밋 누락(557a347 미배포)
  2026-09-02 감사에서 신규 가입 2건이 동의 기록 없이 생성된 것을 확인

차단 법역 기존 계정
  KR·CN 는 signup_blocked 이나 로그인은 막히지 않는다 → H12

게시 언어
  현재 ko·en          법정 요건 후보 pt-BR · th · vi (H14 에서 확정)
  ★ ADDENDUM_BR 은 스스로 pt-BR 을 정본으로 지정 — en 게시는 자기 문서와 모순
  ★ KR 은 게시 언어에 있는데 PigOS 비대상(A-rule)
```

★ **숫자 하나가 미확인이다.** 2026-09-10 대화에서 "가입자 34농장 전원 동의 0건 ·
차단 법역 15농장" 이 언급됐으나, 2026-09-08 실측은 **75농장 = 피그플랜 42 + 내부
10 + 멤버없음 2 + 실고객 23** 이고 그중 KR 4 · CN 2 였다. 두 집계의 모집단이
다른 것으로 보이나 **확인되지 않았다.** 프로덕션 조회가 막혀 있어 이 RUN 에서
재측정하지 않았다.

→ **배포 후 "기존 N농장 재동의" 범위가 이 숫자로 정해지므로 확정이 필요하다.**

---

## 6. 재개 조건 (B-6)

```
H13 도착 (내용이 (1)/(2)/(3) 중 무엇인지 명시)
  → (2)면  _GATES 에 "OTHER" 한 줄 + 테스트 → 커밋
  → 이어서 변호사 회신 대기

변호사 US 3종 회신 도착
  → manifest status 갱신 → G-1b 충족  (★ 2026-09-10 G-1 이 G-1a 대표 / G-1b 변호사 로 분할됨 — DEPLOY_GATE §6-0)
  → 배포 순서 §4 의 1번부터

H13·회신 둘 다 도착
  → §4 전체를 그대로 실행. 9번 두 법역 확인을 건너뛰지 않는다

2026-09-17 도래, 둘 다 미도착
  → ★ 세 번째 만료일을 적기 전에 먼저 결정할 것:
     "게시 문서 없이 서비스를 계속 열어둘 것인가"
     연장은 그 질문의 답이 아니다

KPI 트랙 (T6 · K-1~K-4)
  → 이 트랙과 별개다. P-1(pigos_ro) · P-2(K-2d) 대기로 멈춰 있다
    KPI_K_LOOP 는 READY_BUT_BLOCKED — 착수한 적 없다
```

---

## 7. 관련

```
docs/legal/DEPLOY_GATE_20260910.md            기준 문서 — G-1~G-6 · 배포 순서 · §6-3 OTHER 범위
docs/legal/KNOWN_PUBLICATION_EXPOSURE.md      격리 명세 · 연장 이력
docs/legal/HUMAN_INPUT_QUEUE.md               H11~H15
docs/runs/RUN_COMMON_RULES.md                 §0 PREFLIGHT · 상태 어휘 · 기준값
api/tests/integration/test_publication_consent_gate.py   G-3 10건
api/tests/integration/test_publication_gate.py           격리 CI 가드 9건
```
