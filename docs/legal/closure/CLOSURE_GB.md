# CLOSURE_GB — 영국 게시 전 미결 종결 시트 (2026-09-10)

> 문서 세트: `MASTER` + `PRIVACY` + `ADDENDUM_GB`
> 게이트: `_GATES["GB"] = release_hold, reason_code="OPEN_UK_REP"` (`jurisdiction.py:69`). 가입 451.
> 리서치: `research/GB_EU_legal.md` (EU 와 공동) · 브리프: Q20 · Q18(GB 법인 LOW–MED) · Q5·Q3 · Q11
> ★ **현재 타겟 아님.** EU 시트와 구조가 같다 — 차이만 적는다.

---

## 0. 판정

```
추가 검토 필요 — 게이트 유지. 지금 착수할 항목 0건 (EU 와 동일).
GB 실고객 0 (B-8 목록에 GB 없음).
```

---

## 1. EU 와 다른 점

| 항목 | EU | GB | 근거 |
|---|---|---|---|
| 대리인 | Art.27 EU 대리인 | UK GDPR Art.27 **UK 대리인 별도** — 같은 업체가 병행 가능 | `HUMAN_INPUT_QUEUE` H2 · §D |
| 감독당국 | 회원국 DPA | ICO | 제1조1 |
| 국외이전 | EU→KR 적정성 | **UK→KR 적정성** (UK 는 EU 적정성 결정을 승계·별도 유지) | `LAWYER_BRIEF` §1 국외이전 LOW |
| B2B 콜드 이메일 | DE·DK·IT·PL HIGH | **GB 법인 대상 LOW–MED** (PECR 법인 예외) | `LAWYER_BRIEF` §1 콜드 아웃리치 |
| 쿠키 | ePrivacy 지침 | PECR | 제5조 |
| 언어 | 회원국별 | en — **번역 불요** | 제9조 |

---

## 2. 미결 항목

| # | 항목 | 위치 | 소유자 | 착수 시점 |
|---|---|---|---|---|
| GB-1 | UK 대리인 명칭·주소 | `ADDENDUM_GB:9` `[OPEN]` | 계약 (H2) | GB 출시 결정 후 |
| GB-2 | D-13 역할 | `:58` `[OPEN]` | 변호사 | 지금 (US 건에 포함) |
| GB-3 | DPO 해당성 | 제1조2 | 변호사 | 출시 결정 후 |
| GB-4 | LIA 승인 | 제4조 | 변호사 | EU-4 와 동일 문서 |
| GB-5 | 쿠키 (PECR) | ~~개발~~ **변호사** | EU-6 과 같은 CMP 로 커버. ✔ 2026-09-10 실측 — UK 는 `GoogleAnalytics.astro` 의 EEA+UK `denied` 기본값에 **포함돼 있다**. PECR 적정성 판단만 남음 |

---

## 3. 왜 GB 가 EU 보다 가깝나 (참고 — 결정 아님)

```
번역 불요 · 콜드 이메일 법인 예외 · 대리인 1곳 · 단일 감독당국
→ EU 를 열지 않고 GB 만 여는 선택지가 구조상 존재한다.
   단 CLAUDE.md 5개 시장에 GB 없음. 대표 결정 사안.
```

---

## 4. 승인 경로

```
지금        GB-2 (D-13)
출시 결정   대표 "GB 를 연다" → H2 계약 → GB-3 · GB-4 → _GATES["GB"] 해제
```
