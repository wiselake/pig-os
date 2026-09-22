# CLOSURE_BR — 브라질 게시 전 미결 종결 시트 (2026-09-10)

> 문서 세트: `MASTER` + `PRIVACY` + `ADDENDUM_BR`
> 게이트: `_GATES["BR"] = release_hold, reason_code="OPEN_BR_SCC"` (`jurisdiction.py:70`). 가입 451.
> 리서치: `research/BR_legal.md` · 브리프: Q12(P0) · Q22(P1) · Q27(P1) · Q3(LIA)

---

## 0. 판정

```
추가 검토 필요.  US 다음 순서 (COUNSEL_QUESTION_QUEUE §E).

닫힌 것     DPO(encarregado) = 와이즈레이크(주) / wiselake@wiselake.ai   제1조 기입 완료
            현지 대리인 불요 근거 기재                                   제1조1
            부속조항 본문 9개 조 작성 완료

남은 것     SCC 전문(pt) 첨부              [OPEN]   계약/조달
            F1 국제이전 vs 국제수집         [COUNSEL] 변호사
            F3 완전익명 Art.12 제외         [COUNSEL] 변호사
            D-13 역할                       [OPEN]   변호사
            pt-BR 번역 0건                  H14      번역   ★ 제8조가 스스로 pt-BR 을 정본으로 지정
            BR 신규가입 유지/중단           D-5      대표
```

---

## 1. 적용 법령

| 법령 | 적용 | 부속조항 | 상태 |
|---|---|---|---|
| LGPD | 전반 | 제1~9조 | 본문 완료 |
| ANPD 국제이전 규정 (SCC) | 한국 적정성 없음 → SCC 편입 필수, 유예 종료 | 제2조 | **전문 미첨부** |
| LGPD Art.12 | 완전 익명화 산출물 적용 제외 | 제2조 F3 · 제4조 | 변호사 |
| LGPD Art.16 IV | 배타적 사용 익명화 산출물 존속 | D-03 연결 | 변호사 (Q15) |
| ANPD 익명화 규정 | 제정 중 | 모니터링 트리거 (LAWYER_BRIEF §3) | — |

---

## 2. 미결 항목

| # | 항목 | 위치 | 소유자 | 처리 | 태그 |
|---|---|---|---|---|---|
| BR-1 | SCC 전문 (포르투갈어 원문) 별도 첨부 | `ADDENDUM_BR:16` | 계약/조달 + 변호사 | ANPD 표준계약조항 원문 확보 → 지정 필드(당사자·역할·범주·목적·보유·보안·재이전)만 기입. **본문 수정 금지** (제2조2). 첨부 방식(별지 vs 링크)은 변호사 | `LEGAL_REQUIREMENT` |
| BR-2 | F1 흐름이 국제이전인가 국제수집인가 | `:21` `[COUNSEL]` | 변호사 | 이용자가 직접 역외 서버에 입력 = coleta internacional 이면 SCC 가 F1 에 자동 적용되지 않음. **이 답이 BR-1 의 범위를 정한다** — F2(외부 AI 재이전)만 SCC 인지, F1 도인지 | `COUNSEL_CONFIRMATION_REQUIRED` |
| BR-3 | F3 완전익명 산출물의 LGPD 밖 여부 | `:23` `[COUNSEL]` | 변호사 | Art.12. 익명화 기준은 D-05 (k값) 와 연동 — 변호사+통계 | `COUNSEL_CONFIRMATION_REQUIRED` |
| BR-4 | D-13 역할 | 제2조 표 · `[OPEN — 역할 확정 후]` | 변호사 | COMMON N-1 과 동일 건 | `COUNSEL_CONFIRMATION_REQUIRED` |
| BR-5 | **pt-BR 본** | 제8조 | 번역 + 대표 (H14) | 부속조항 제8조2 "포르투갈어본이 정본". 현재 공개 게시 언어 ko·en 뿐 (`public_notice.py`). **en 으로 게시하면 자기 문서와 모순.** 번역 대상 = MASTER + PRIVACY + ADDENDUM_BR + SCC | H14 입력 |
| BR-6 | BR 신규가입 유지/중단 | `EXTERNAL_INPUT_REQUEST` D-5 | 대표 | App Store BR 라이브 ↔ 게이트 451. 현재 코드가 이미 451 이므로 **"중단"이 현 상태**다. 유지하려면 게이트 해제 = BR-1~BR-5 전부 | 대표 확인 |
| BR-7 | encarregado 지정 방식 · ATPP 완화 | Q22 | 변호사 | P1 — 출시 후 3개월 | 지금 불요 |
| BR-8 | 인테그레이터 데이터 귀속 | 제9조 · Q27 | 변호사 | P1. 제9조 보증 강화 조항은 이미 있음 | 지금 불요 |

---

## 3. 실측 — BR 계정

```
9-08 실측 (LEGAL_P0_FREEZE §3)   실고객 23 중 BR 1     ← 1차 근거 문서 없음 (CLOSURE_OTHER §1 과 동일 문제)
```

BR 1농장이 실고객이면 **게이트 451 상태에서 이미 서비스 중**인 계정이다. 재동의 범위(H11)에 들어간다.

---

## 4. 리스크

| 리스크 | 심각도 | 완화 |
|---|---|---|
| SCC 없이 F2(외부 AI 재이전) 발생 | HIGH | 목적⑥ BR 비활성 유지 (부속조항 헤더 목적② OFF 와 같은 방식) — **⑥ 도 OFF 인지 코드 확인 필요** |
| en 게시 + 제8조 pt 정본 = 자기모순 | HIGH | pt-BR 번역 전 BR 게이트 해제 금지 |
| App Store BR 라이브인데 가입 451 | MED | 심사 URL 문제와 별개 — 451 화면 문구가 8 로케일 중 pt 포함인지 확인 (`f0934c0`) |

---

## 5. 승인 경로

```
1  변호사   BR-2 (F1 구분) → BR-1 범위 확정 → BR-3 · BR-4
2  조달     SCC 원문 확보 · 지정 필드 기입 (변호사 검수)
3  번역     MASTER · PRIVACY · ADDENDUM_BR · SCC → pt-BR  (하루짜리 아님)
4  대표     H14 (게시 언어) · BR-6
5  개발     _GATES["BR"] release_hold 해제 → 배포 순서 §4
```

★ US 회신 요청에 BR 을 넣는 이유는 **BR-2 하나**다 (`COUNSEL_REQUEST_US_FIRST` 5번). 답이 "F1 은 국제수집"이면 SCC 범위가 F2 로 좁아져 파일럿이 가까워진다.
