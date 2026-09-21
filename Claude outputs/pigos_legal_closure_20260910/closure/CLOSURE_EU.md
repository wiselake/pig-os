# CLOSURE_EU — EU 게시 전 미결 종결 시트 (2026-09-10)

> 문서 세트: `MASTER` + `PRIVACY` + `ADDENDUM_EU`
> 게이트: `_GATES["EU"] = release_hold, reason_code="OPEN_EU_REP"` (`jurisdiction.py:68`). 가입 451.
> 리서치: `research/GB_EU_legal.md` · 브리프: Q20(P0) · Q18(P0) · Q5·Q3(LIA) · Q2(코호트) · Q11(P2)
> ★ **현재 타겟 아님** (`CLAUDE.md` 5개 시장 · `COUNSEL_QUESTION_QUEUE` §D). 이 시트는 "지금 무엇을 안 해도 되는가"를 고정하는 용도다.

---

## 0. 판정

```
추가 검토 필요 — 게이트 유지. 지금 착수할 항목 0건.

닫힌 것     부속조항 본문 10개 조 · DPO 문의처 · 컨트롤러 기재 · LIA 초안(internal/LIA_PURPOSE2_DRAFT.md)
남은 것     Art.27 대리인 계약        H1     계약 (연 1~3천 유로 — HUMAN_INPUT_QUEUE §1)
            D-13 역할                 [OPEN] 변호사
            DPO 해당성 Art.37         Q20    변호사
            LIA 최종 승인             Q5·Q3  변호사
            쿠키 CMP UI               제5조  개발 (변호사 확인 후)
            회원국 언어               제9조  국가별 스케줄
            DE·DK·IT·PL 아웃리치 게이팅  Q18 · D-10
```

---

## 1. 실측 — EU 계정

```
COUNSEL_QUESTION_QUEUE B-8   ES · DE · DK · NL 각 1~2농장 — 전부 pigplan_migration, native 0
```

**EU 실고객 0.** 게이트 451 이 아무도 막고 있지 않다. 이것이 "지금 착수 0건"의 근거다.

---

## 2. 미결 항목

| # | 항목 | 위치 | 소유자 | 처리 | 착수 시점 |
|---|---|---|---|---|---|
| EU-1 | Art.27 EU 대리인 명칭·주소 | `ADDENDUM_EU:9` `[OPEN]` | 계약 (H1) | rep-as-a-service. GB 와 같은 업체 병행 가능 (§D) | EU 출시 결정 후 |
| EU-2 | D-13 역할 | `:57` `[OPEN]` | 변호사 | COMMON N-1 — **US 회신으로 함께 닫힌다** | 지금 (US 건에 포함) |
| EU-3 | DPO 지정 의무 해당성 | 제1조2 · Q20 | 변호사 | Art.37 대규모·정기 모니터링 임계 | EU 출시 결정 후 |
| EU-4 | 목적② LI + 이의권 — LIA 승인 | 제4조 · `LIA_PURPOSE2_DRAFT` | 변호사 | D-01 (b) 국가별 분기의 EU 축. RUN L (LIA 초안) 은 회신 불요 — 지금 가능 | LIA 초안은 지금, 승인은 출시 전 |
| EU-5 | 최소 코호트 k값 | D-05 · Q2 | 변호사 + 통계 | `INTERNAL_POLICY_PROPOSAL` k=10/20, 지배율 70/85%. **EDPB 02/2026 의견수렴 2026-10-30 종료** 후 재검토 트리거 | 10-30 이후 |
| EU-6 | 쿠키 CMP | 제5조 · F7 | ~~개발~~ **CMP 존재 — 변호사 대조로 이관** | ✔ **실측 2026-09-10** (`C:\dev\pigos-landing`). GA 로드는 사실이나 **무방비가 아니다** — `components/GoogleAnalytics.astro` 가 **Consent Mode v2** 로 EEA·UK 를 `denied` 기본값 + 동의 배너, 그 외 지역은 `granted` 기본값. 배너 문구 6개 언어. `privacy.astro:13`·`terms.astro:13` 이 이 컴포넌트를 쓴다 | 변호사 (문구·기본값 적정성) |
| EU-7 | 회원국 언어 | 제9조 | 국가별 | EU 단일 의무 없음. 프랑스 소비자 등 국가별 | 출시국 확정 후 |
| EU-8 | 아웃리치 게이팅 | Q18 · D-10 | 대표 | DE·DK·IT·PL 옵트인 국가 발송 금지 — **콜드 이메일 실행 여부 자체가 V5 미확인** | 아웃리치 개시 전 |

---

## 3. 리스크

| 리스크 | 심각도 | 완화 |
|---|---|---|
| 랜딩 GA 쿠키가 EU 방문자에게 동의 없이 작동 | MED | EU-6 — 출시와 별개로 CMP. 이용자 0 이어도 방문자는 있다 |
| 한국 EU 적정성 1차 재심사 | LOW | Q11 모니터링. 목적⑥ 도입 시 P0 승격 |
| GDPR 프레임을 US 문서에 역수입 (동의 토글로 ② 설계) | MED | D-01 (b) 국가별 분기 유지 — EU 만 LI |

---

## 4. 승인 경로

```
지금        EU-2 (D-13, US 건과 함께) · RUN L (LIA 초안 — 회신 불요)
출시 결정   대표 "EU 를 연다" → H1 계약 → EU-3 · EU-4 승인 → EU-7 → _GATES["EU"] 해제
별도        EU-6 랜딩 CMP (법무 트랙 밖, 랜딩 트랙)
```
