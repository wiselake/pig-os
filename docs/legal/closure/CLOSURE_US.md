# CLOSURE_US — 미국 게시 전 미결 종결 시트 (2026-09-10)

> 문서 세트: `MASTER_TERMS` + `GLOBAL_PRIVACY_NOTICE` + `ADDENDUM_US` (`terms_renderer.py:92-95`)
> 게이트: `_GATES` 에 US 항목 없음 = **잠금 없음** (`jurisdiction.py:63-71`). 문서 승인만 남았다.
> 리서치: `research/US_legal.md` · 브리프: `LAWYER_BRIEF` Q8·Q4·Q9·Q19·Q23 · 내부 메모: `internal/INTERNAL_US_DATA_BROKER_MEMO.md`

---

## 0. 판정

```
조건부 진행.

코드          잠금 없음. G-3 게시 게이트(320baea)·배포 5건(07d0f94 §5-2) 대기.
부속조항      [OPEN] 1건 — D-13 하나.  나머지 조항 전부 값 기입 완료.
공통 문서     CLOSURE_COMMON 의 M-1~M-8 · V-1~V-11 · R-1~R-11 · N-1~N-2
번역          불요 — ADDENDUM_US 제8조 en 정본.  ★ 7개국 중 유일하게 번역 0건으로 열린다
대리인        불요 — 제1조1 (역외 사업자 일반 대리인 의무 없음)
계약          불요

조건 = D-13 회신 + H13 결재 + COMMON 종결 + 시행일.
```

---

## 1. 적용 법령 (요약 — 판정은 `research/US_legal.md`, 확정은 변호사)

| 법령 | 적용 | 부속조항 반영 위치 | 상태 |
|---|---|---|---|
| 주 포괄 프라이버시법 (CCPA/CPRA 등) | 소비자 권리·business/service provider 지위 | 제3조 (주별 별표) · 제1조6 역할 | 별표 있음 · 역할 = D-13 대기 |
| 네브래스카 LB525 농업데이터법 | NE 생산자 농업데이터 소유권·판매 서면동의 | 제9조1 · `jurisdiction.py` `US-NE` state flag | 조항 있음 · **전자동의 = express written 충족 여부 변호사** (Q8) |
| FTC Act §5 | 익명화 실패 시 기만 | 제4조 목적② 근거 | 조항 있음 |
| CAN-SPAM | B2B 이메일 옵트아웃·물리 주소 | 제5조 | 조항 있음 · **발신 물리주소 값 확인** (운영) |
| 주 데이터브로커 등록법 (CA·VT·TX·OR·CT) | 직접 관계 없는 소비자 데이터 매매 | 내부 메모 (고객 미노출) | 원칙 비해당 논거 있음 · 목적⑤ 제3자 연락처가 예외 → **⑤ 비활성 유지** |
| DOJ Bulk Data Rule | 우려국 이전 | — | 한국 비해당 (LAWYER_BRIEF §1 국외이전 LOW) |
| CA ADMT·위험평가 규정 | 자동화 의사결정 | NOTICE 제3조의2 | 룰 엔진은 판정만, AI 는 설명만 (AI role boundary) — 해당성 변호사 |

---

## 2. 미결 항목

| # | 항목 | 위치 | 소유자 | 처리 | 태그 |
|---|---|---|---|---|---|
| US-1 | controller/processor ↔ business/service provider 지위 배분 | `ADDENDUM_US:56` `[OPEN — 역할 확정 후]` | 변호사 | **= D-13.** 부속조항 제1조6 은 이미 3개 처리유형별 후보 배분을 적어놨다. 회신은 "이 배분이 맞는가" 하나 | `COUNSEL_CONFIRMATION_REQUIRED` |
| US-2 | LB525 전자동의의 express written consent 충족 | 제9조1 | 변호사 | Q8. 충족 안 되면 NE 농장은 목적②③④⑤ 전부 별도 서면 → `US-NE` state flag 로 분기 가능 (코드 있음) | `COUNSEL_CONFIRMATION_REQUIRED` |
| US-3 | CAN-SPAM 발신 물리주소 | 제5조 | 운영 | 와이즈레이크(주) 한국 주소로 충족되는지 확인 — 미국 주소 요구 아님 (Q19, P1) | 운영 확인 |
| US-4 | 데이터브로커 등록 | 내부 메모 | 대표 + 변호사 | 원칙 비해당. **목적⑤ 활성화 전 재판정** — 지금 결정 불요 (Q4·Q7, 메모 §2-3(a)) | 조건부 |
| US-5 | 공통 미결 | `CLOSURE_COMMON` | 각 소유자 | M-1~M-8 · V · R · N — 특히 **R-6 접속기록 기준을 KR 고시로 잡은 것이 US 에 충분한지** 변호사 대조 | — |
| US-6 | 시행일 | MASTER 부칙 · NOTICE 부칙 | 대표 | COMMON M-3 (공고 + 30일 후보) | `INTERNAL_POLICY_PROPOSAL` |

### `HUMAN_INPUT_QUEUE` §3 US 줄의 Q번호 오류 (정정 필요)

```
현재 기재    "LB525 전자동의(Q7) · CA ADMT/위험평가(Q8) · DOJ Rule(Q10)"
LAWYER_BRIEF  Q7 = 리드 제공⑤ 동의 요건  ·  Q8 = LB525  ·  Q10 = 동의 UI 형식
              CA ADMT 는 Q23(주법 추적, P2) · DOJ Rule 은 §1 리스크표에만 있고 전용 Q 없음
```

변호사에게 Q번호로 가리키면 엉뚱한 질의로 간다. `COUNSEL_REQUEST_US_FIRST` 에서 정정했다.

---

## 3. ★ US 승인이 여는 실제 범위

```
"US 3종 승인" = MASTER + PRIVACY + ADDENDUM_US

열림    US                          group=US
        MX · CL · CO · JP · PH …    group=OTHER — _ADDENDUM["OTHER"]=None (jurisdiction.py:92)
                                    → MASTER + PRIVACY 두 건이 곧 완전한 세트
차단    BR · VN · TH · EU · GB      각 addendum DRAFT (release_hold / paid_blocked)
차단    KR · CN                     signup_blocked
```

이것은 버그가 아니라 설계다 (`LEGAL_P0_FREEZE` §3). **US 를 승인하는 결재는 OTHER 를 여는 결재이기도 하다.** → `CLOSURE_OTHER.md` · H13.

---

## 4. 리스크

| 리스크 | 심각도 | 완화 |
|---|---|---|
| D-13 회신이 부속조항 제1조6 배분과 다르면 NOTICE 제7조·DPA 제2조·부속조항 6건 연쇄 수정 | HIGH | 회신 형식에 "제1조6 배분 유지 / 수정(수정안)" 양자택일 요구 |
| US 승인이 OTHER 를 여는 구조를 대표가 모르고 결재 | HIGH | H13 결재문에 (1)/(2)/(3) 명시 요구 (`KNOWN_PUBLICATION_EXPOSURE` 1차 연장 조건 1) |
| NE 농장이 있는데 LB525 서면동의 미충족 상태로 목적② ON | MED | 현재 목적② 전 국가 OFF (부속조항 헤더). NE 실고객 존재 여부 **미확인** — 9-08 실측 US 11 의 주 분포 없음 |
| 공개 URL 미해결 마커 24건 노출 중 | HIGH (진행 중) | 격리 2026-09-17 만료. `COUNSEL_REQUEST_US_FIRST` 1번 |

---

## 5. 승인 경로

```
1  변호사   D-13 · Q8(LB525) · COMMON M-4·R-2·R-9·R-11        → COUNSEL_REQUEST_US_FIRST (기한 9-17)
2  대표     H13 (1)/(2)/(3) · COMMON M-1·M-3·M-5~M-8·R-1·R-3·R-5 · US-4 는 보류 가
3  운영     US-3 · COMMON M-2·R-6·R-7·R-10 + 집행 잡 티켓
4  개발     COMMON V-1·V-10·V-11 · R-8 실측 → 승인 후 본문 교체 → manifest PUBLISHED
5  배포     LEGAL_P0_FREEZE §4 순서. 9번 두 법역 확인(US 201 · BR 451) 생략 금지
```

---

## 6. 변호사 질의 — 이 국가에서 필요한 것만

```
D-13     제1조6 의 (i)(ii)(iii) 배분 유지 여부                      ★ 최우선
Q8       LB525 — 앱 내 전자동의가 express written consent 인가
Q4       익명·집계 산출물 판매의 '판매' 재분류 위험 (FTC §5 + 주법)  — 목적② ON 전
Q19      CAN-SPAM 한국 물리주소 충족                                 — P1, 지금 불요
Q23      CA ADMT 해당성                                              — P2, 지금 불요
```

★ 지금 보내는 것은 D-13 · Q8 두 건이다. 나머지는 목적② ON 또는 아웃리치 개시 전.
