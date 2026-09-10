# closure/ — 국가별 게시 전 미결 종결 시트 (2026-09-10)

> **성격**: 판정 시트. **값을 확정하지 않는다.** 각 국가에서 "무엇이 닫혔고, 무엇이 남았고, 누가 닫는가"를
> 한 장에 고정한다. 제안값은 전부 `INTERNAL_POLICY_PROPOSAL` 태그를 달며, 태그 없는 값은 존재하지 않는다.
>
> **위조 0 / PROPOSED ≠ APPROVED.** 이 폴더의 어떤 값도 승인 없이 `publish_candidate/` 본문에 들어가지 않는다.
> 근거는 `파일:줄` 로 붙였다. 붙이지 못한 숫자는 `미확인` 으로 적었다.

## 파일

| 파일 | 대상 | 판정 |
|---|---|---|
| `CLOSURE_COMMON.md` | MASTER_TERMS + GLOBAL_PRIVACY_NOTICE — 전 국가 공통 미결 (마커 30건 중 25건이 여기) | 조건부 진행 |
| `CLOSURE_US.md` | 미국 — 1차 출시 시장 | **조건부 진행** (D-13 + H13 + COMMON) |
| `CLOSURE_OTHER.md` | 부속조항 없는 전 국가(MX·CL·CO·JP·PH…) — US 승인과 함께 열리는 그룹 | 대표 결재 대기 (H13) |
| `CLOSURE_BR.md` | 브라질 | 추가 검토 필요 (SCC·pt-BR·F1/F3) |
| `CLOSURE_EU.md` | EU | 추가 검토 필요 — 현재 비타겟, 게이트 유지 |
| `CLOSURE_GB.md` | 영국 | 추가 검토 필요 — 현재 비타겟, 게이트 유지 |
| `CLOSURE_TH.md` | 태국 | HOLD 유지 (D-09) |
| `CLOSURE_VN.md` | 베트남 | HOLD 유지 (D-08) |
| `CLOSURE_KR.md` | 한국 — PigOS 비대상(A-rule). 피그플랜 현행 게시본 = 참조 전용 | 열지 않음 유지 |
| `CLOSURE_CN.md` | 중국 | HOLD (D-07) — 부속조항으로 해소 불가 |

## 판정 어휘

```
조건부 진행        조건이 전부 사람 결정(대표·변호사)이고 코드 작업은 끝났다
추가 검토 필요      변호사 회신 + 계약/번역 등 외부 산출물이 필요하다
HOLD 유지          내부 출시 게이트 문서(internal/INTERNAL_LAUNCH_GATE_*)가 HOLD 이고 해제 조건 미충족
열지 않음 유지      정책상 대상이 아니다 (KR A-rule)
```

## 소유자 어휘

```
대표      Grant 결재 (H-번호 / D-번호)
변호사    LAWYER_BRIEF Q-번호 또는 COUNSEL_QUESTION_QUEUE 항목
운영      값을 정하면 그 값을 집행하는 잡이 필요하다 (PRIVACY_NOTICE_FACT_FINDING A-6)
인프라    AWS 설정값 확인 (Brian)
계약      돈이 드는 외부 계약 (H1~H3)
번역      pt-BR · th · vi 법정 언어본
개발      위 항목이 닫힌 뒤에만 착수
```

## 마커 총계 (publish_candidate/ ko본, 2026-09-10 grep)

```
PIGOS_GLOBAL_PRIVACY_NOTICE   OPEN 10 · V 11 · COUNSEL 1 · [ ] 1     = 23
PIGOS_MASTER_TERMS            OPEN  3 · COUNSEL 1                     =  4   (헤더 제외)
ADDENDUM_US                   OPEN  1                                 =  1
ADDENDUM_BR                   OPEN  1 · COUNSEL 2                     =  3
ADDENDUM_EU / GB / TH         OPEN  2 각                              =  6
ADDENDUM_VN                   OPEN  2                                 =  2
                                                                      39
```

★ 39건 중 `[OPEN — 역할 확정 후 DPA·본 조에 반영]` 6건(부속조항 전부) + NOTICE 제7조 `[COUNSEL]` 1건 = **7건이 D-13 하나**다.
D-13 회신 하나가 7건을 닫는다 (`COUNSEL_QUESTION_QUEUE` A-1).

## 관련

```
docs/legal/HUMAN_INPUT_QUEUE.md                    소유자별 미결 (H1~H15)
docs/legal/COUNSEL_QUESTION_QUEUE_20260902.md      변호사 신규 질의 (A-1, B-1~B-8, §G 보류 규율)
docs/legal/COUNSEL_REQUEST_US_FIRST_20260910.md    ★ 오늘 발송할 US 우선 회신 요청서
docs/legal/PRIVACY_NOTICE_FACT_FINDING_20260902.md [V]·[OPEN] 실측
docs/legal/LEGAL_P0_FREEZE_20260910.md             게이트 현황 · 배포 순서
docs/legal/DECISION_REGISTER.md                    D-01~D-15
```
