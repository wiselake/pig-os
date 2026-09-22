# 별첨 B — 침해통지 기한 사전 초안 (PRE-COUNSEL DRAFT, 2026-09-10)

> **★ 이 표의 어떤 값도 확정이 아닙니다.** `legal:compliance-check` + 공개 자료 검색으로 만든 **사전 초안(pre-counsel research)** 이며, 변호사 검토를 거치지 않았습니다. 사내 어느 문서(방침·DPA·부속조항)에도 이 값을 옮기지 않습니다.
> **용도**: 2차 자문 요청서 §3-1 의 빈 표를 변호사가 백지에서 채우는 대신, **저희 초안을 대조·정정**하시게 하는 것. 백지보다 빠르고, 저희가 무엇을 잘못 알고 있는지도 드러납니다.
> **앵커링 위험**: 초안을 드리면 그 값에 끌릴 수 있습니다. 그래서 요청서 본문이 아니라 **별첨으로 분리**했고, 각 칸에 신뢰도를 붙였습니다. 요청서에는 "저희 초안이 틀렸다면 그렇게 적어 주십시오"를 명시했습니다.

### 신뢰도 태그

```
[A] 출처 URL 확인 + 값이 1차 자료·주요 로펌 자료에서 일관         → 변호사는 "맞다/틀리다"만
[B] 값은 알고 있으나 조문 원문 대조 안 함                          → 변호사 확인 필요
[C] 구조만 알고 숫자 미확인                                        → 변호사가 채워야 함
[—] 모름                                                           → 변호사가 채워야 함
```

★ 전 항목이 **2026-09-10 기준**이며, 기준일(effective / current as of) 자체도 변호사 확인 대상입니다.

---

## 1. controller 층 — 회사가 controller 인 경우

| 법역 | 근거 (사내 인지) | 감독당국 신고 | 정보주체 통지 | 기산점 | 임계 | 신뢰도 |
|---|---|---|---|---|---|---|
| **EU** | GDPR Art.33 · 34 | 인지 후 **72시간**. 초과 시 지연 사유 첨부 | 고위험 시 **부당한 지체 없이** | controller 가 침해를 "인지(aware)"한 때 | 개인의 권리·자유에 대한 위험이 없을 것 같으면(unlikely) 신고 면제 | [A] |
| **GB** | UK GDPR · DPA 2018 (ICO) | **72시간** | 고위험 시 부당한 지체 없이 | 동일 | 동일 | [A] |
| **KR** | PIPA 제34조 + 시행령 | **72시간** (임계 충족 시 PIPC·KISA) | **72시간** 내 정보주체 통지 | "유출등을 알게 된 때" | 1천명 이상 · 민감정보/고유식별정보 · 외부 불법접근 — **3요건 중 하나** 로 인지 | [B] |
| **BR** | LGPD Art.48 + ANPD Res. CD/ANPD nº 15/2024 | **3 영업일** (ANPD) | 3 영업일 (정보주체) | 인지한 날 | "관련 위험 또는 피해(risco ou dano relevante)" — 건수 기준 아님 | [B] |
| **TH** | PDPA §37(4) + PDPC 고시(2022) | **72시간** | 고위험 시 부당한 지체 없이 | 인지한 때 | 개인의 권리·자유에 위험이 없을 것 같으면 면제 | [B] |
| **VN** | **Law 91/2025/QH15 + Decree 356/2025/NĐ-CP** (2026-01-01 시행) | **72시간** 구조로 인지 — 소관 당국·양식 미확인 | 미확인 | 미확인 | 미확인 | [C] ★ 사내 문서가 구 Decree 13 기준이라 이 행은 특히 대조 필요 |
| **US 연방** | FTC Safeguards Rule · HBNR · HIPAA | **PigOS 는 비해당 추정** | — | — | Safeguards Rule 은 **비은행 금융기관** 대상 (500명 이상 · 30일). PigOS 는 금융기관 아님 | [B] — **비적용 근거 확인 요청** |
| **US CA** | Civ. Code §1798.82 (+ SB 446, 2026) | 500명 초과 시 AG 제출 | **30 역일** (2026 개정) | 발견(discovery) | 암호화 예외 등 | [A] |
| **US TX** | Bus. & Com. §521.053 | 250명 이상 시 AG **30일** | **60일** | 발견 | | [B] |
| **US IA** | Iowa Code §715C | 500명 초과 시 AG 5영업일 | 지체 없이 | 발견 | | [C] |
| **US NE** | Neb. Rev. Stat. §87-801 이하 | AG 동시 통지 | 지체 없이 | 발견 | **네브래스카 resident** 기준 | [C] |
| **US NC** | N.C.G.S. §75-65 | AG 동시 | 지체 없이 | 발견 | **NC resident** 기준 | [C] |
| **US MN** | Minn. Stat. §325E.61 | | **48시간**(?) — 미확인 | 발견 | | [—] |
| **CN** | — | HOLD (D-07). 이번 범위 밖 | — | — | — | — |

---

## 2. processor 층 — 회사 → 고객(controller) 통지

★ **이 층이 별도로 존재한다**는 것이 이번 요청의 핵심입니다. controller 의 감독당국 기한에서 역산하면 안 되는 이유가 여기 있습니다.

| 법역 | 근거 | 기한 | 신뢰도 |
|---|---|---|---|
| EU · GB | GDPR Art.33(2) | **부당한 지체 없이** (숫자 없음) | [A] |
| KR | PIPA 제26조⑧ — 수탁자에 제34조 준용 | ★ **수탁자가 직접 신고 의무를 질 수 있음.** 고객 통지로 끝나지 않을 수 있다 | [B] — §3-2 (c) 로 질의 |
| US CA | Civ. Code §1798.82(b) | 데이터를 **보유·관리하는 자**는 소유자·라이선시에게 **"immediately following discovery"** | [B] — 요청서에 "인지하고 있음(확인 요청)"으로 표기 |
| US NC · MN 등 | 각 주법 | 유사한 즉시 통지 구조로 인지 | [C] |
| BR · TH · VN | operador / processor 규정 | 미확인 | [—] |

**회사안 (검토 요청)**: DPA 제6조① 에 *"부당한 지체 없이, 어떠한 경우에도 인지 후 **24시간** 이내(적용법이 더 짧은 기한을 요구하면 그 기한)"*. 24시간은 확정이 아니라 검토 대상입니다.

---

## 3. 단계적 통지 (§3-2 b) — 수신자별

| 경로 | 초안 | 신뢰도 |
|---|---|---|
| processor → 고객 | 계약으로 정하는 사항. 1차 + 보완 구조 가능으로 추정 | [C] |
| controller → 감독당국 | GDPR Art.33(4) 명시적으로 **단계적 제공 허용**. ICO 도 동일 안내 | [A] |
| controller → 정보주체 | 단계적 구조에 대한 명시 근거 미확인 | [—] |

---

## 4. 이 초안이 못 채운 것 — 변호사가 반드시 채워야 하는 칸

```
VN 전 행                 신법 기준 값 (사내 문서 구법 기준 · [C])
US IA · NE · NC · MN     값 대부분 [C]·[—]
US resident 기준 (§3-3 f) 농장 소재주 vs 정보주체 거주주 — 초안 없음
기산점 정의               "인지"의 법역별 정의 · constructive knowledge 적용 여부
BR · TH · VN processor 층  전부 [—]
US 연방 비적용 근거        업종별 규정(HBNR·HIPAA·GLBA)의 비적용을 문서로 확인
```

---

## 5. 방법론 — 이 초안을 어떻게 만들었나

```
1  legal:compliance-check 의 규제 개요 (GDPR·CCPA·LGPD·PDPA·PIPL 축)
2  공개 자료 검색 — 로펌 인사이트 · 감독당국 안내 · 법령 텍스트 사이트
3  각 값에 신뢰도 태그. 검색으로 URL 을 확인한 것만 [A]
4  ★ 1차 자료 원문 대조는 하지 않았습니다. 조문 번호도 인지 기준입니다
```

**한계**: 검색 결과의 제목·요약까지만 봤고 조문 원문을 열어 대조하지 않았습니다. 그래서 [A] 도 "출처가 있다"는 뜻이지 "원문을 봤다"는 뜻이 아닙니다.

---

## 6. 출처

```
EDPB Guidelines 9/2022 (breach notification v2.0)
  edpb.europa.eu/system/files/2023-04/edpb_guidelines_202209_personal_data_breach_notification_v2.0_en.pdf
ANPD Resolution CD/ANPD nº 15/2024 (영문본)
  machadomeyer.com.br/images/RESOLUCAO_CD_ANPD_N_15_DE_24_DE_ABRIL_DE_2024_eng.pdf
Thailand PDPC 침해통지 고시 — IAPP · Nishimura & Asahi · DLA Piper Privacy Matters
Korea PIPA — Baker McKenzie Global Data and Cyber Handbook (KR) · DLA Piper DataGuidance (KR)
Vietnam Law 91/2025/QH15 + Decree 356/2025/NĐ-CP — EY Vietnam · Tilleke & Gibbins · DFDL · FPF Issue Brief (2026-01)
California SB 446 / Civ. Code §1798.82 — leginfo.legislature.ca.gov · Norton Rose Data Protection Report · Pillsbury
Texas §521.053 · 주별 요약 — Davis Wright Tremaine "Summary of U.S. State Data Breach Notification Statutes"
FTC Safeguards Rule 침해 신고 — ftc.gov 보도자료(2023-10) · ftc.gov 사업자 안내(2024-05)
```
