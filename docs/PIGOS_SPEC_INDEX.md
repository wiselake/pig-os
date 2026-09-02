# PIGOS_SPEC_INDEX v0.2.1
## PigOS·PigSignal 스펙 문서 체계 (SSOT 지도)

> **목적**: 2026-07-21 회의 실행 문서 전체의 단일 지도. 문서 간 중복 서술 금지 — 겹치는 주제는 담당 문서 참조.
> **세션 시작 시 이 파일부터.** 경로는 전부 레포 실경로.
> **v0.2 → v0.2.1**: 레포 실경로 반영, 기존 문서(2026-06-17_country-kpi-differences, signup-onboarding-spec) 연결, 스켈레톤 5종 통합 정리 반영.

---

## 1. 문서 지도 (살아있는 문서 6 + 런 프롬프트)

| # | 문서 | 경로 | 범위 | 상태 |
|---|---|---|---|---|
| 1 | COUNTRY_KPI_RULE_SPEC v0.3.1 | `docs/specs/COUNTRY_KPI_RULE_SPEC_v0.3.1.md` | KPI 정책 벡터+상속(resolved), R1/C1/R2, 경영 KPI(운영비·손익), 표준화, T2 절차, Event Envelope, 런타임 게이트 집행. **온보딩 최소입력 §11 포함** | v0.4 개정 대기 (런 C) |
| 2 | PIGOS_FEATURE_ENTITLEMENT_MATRIX | `docs/product/PIGOS_FEATURE_ENTITLEMENT_MATRIX.md` | 무료/트라이얼/유료 전수. 3층 구조. paywall SSOT. **D-08·09·10 결재 vehicle** | v0.1 — **대표 승인 대기** |
| 3 | DATA_RIGHTS_CONSENT_SPEC | `docs/legal/DATA_RIGHTS_CONSENT_SPEC.md` | 권리 4조항, purpose 6종, 마스터+국가부속+US주별부칙, Consent Ledger | v0.1 스켈레톤 — **가입 오픈 게이트.** 런 D가 보강 |
| 4 | ANONYMIZATION_RELEASE_GATE_SPEC | `docs/specs/ANONYMIZATION_RELEASE_GATE_SPEC.md` | **Data Asset Policy 소유 (A-rule 집행 SSOT)** + 판매 게이트 체크리스트 | v0.1 스켈레톤 — PigSignal 판매 게이트 |
| 5 | MEETING_NOTES_2026-07-21 | `docs/meetings/MEETING_NOTES_2026-07-21.md` | 회의 기록 + 액션 트래커. **결정 아님 — 확정은 Decision Register만** | v1.0 |
| 6 | MASTER_SCHEDULE | `docs/planning/MASTER_SCHEDULE_2026-07.md` | 통합 일정 (대표 미팅 날짜 변수형) | v0.1 |
| 7 | PIGOS_COUNTRY_LEGAL_ONBOARDING_SPEC v1.0 | `docs/legal/PIGOS_COUNTRY_LEGAL_ONBOARDING_SPEC_v1.0.md` | 국가별 가입·약관·동의·증빙 통합 baseline. Legal document ↔ Consent decision 분리, 문서 lifecycle(PUBLISHED only), promotion 파이프라인, **LEGAL-/KPI- ID namespace 분리** | v1.0 — DEVELOPMENT BASELINE / **LEGAL APPROVAL PENDING** |

**런 프롬프트** (`docs/runs/`): RUN_PROMPT_A(정책 벡터) / B(Envelope) / C(KPI v0.4+evidence+대표 결정요청서) / D(국가·주별 법무 리서치). 플레이스홀더(baseline 해시·테스트 수·런로그 경로) 채운 후 실행.

**법무 실측 감사 2건** (#7 의 근거): `docs/legal/LEGAL_PUBLICATION_GAP_REPORT_20260902.md`(문서·구현·승인 gap — publish_candidate v1.0-rc 가 정본이고 runtime 은 placeholder) · `docs/legal/PRODUCTION_CONSENT_LEDGER_AUDIT_20260902.md`(운영 원장 0행 → `PLACEHOLDER_CONSENT_PROD = NOT_FOUND`).

**기존 문서 연결**: `docs/specs/2026-06-17_country-kpi-differences.md`(런 C 입력, v0.4 대조 필수) · `docs/specs/2026-07-10_signup-onboarding-spec.md`(#1 §11과 정합 확인) · `docs/KPI_DEFINITIONS.md` · `docs/RULE_ENGINE_CATALOG.md` · `docs/legal-review-notes.md` · BILLING_ARCHITECTURE_NOTE.

### 통합·유예된 문서 (스켈레톤 5종 정리)
- PIGSIGNAL_PRODUCT_CATALOG_BM_SPEC → **미작성 유지.** 착수 트리거: AgentExchange 심사 통과. 요구사항 출처 = 회의록 §5 (가치 사다리, 10세그먼트, Agent 마이크로: 잘게·싸게·제목 판단, 거래연결 DEFERRED — TRANSACTION_MATCHING 옵트인+규제 검토 선행)
- GLOBAL_SUPPORT_INBOX_SPEC → 미작성 유지. 착수 트리거: CS 개발 착수. **핵심 확정: 단일 Ticket SSOT = 공통 Support Service. PigOS=인바운드 채널, Q-Bridge(Console)=상담 콘솔. 티켓 DB 이원화 금지. 다국어 원문·번역 양측 저장**
- ONBOARDING_ACTIVATION_FLOW → #1 §11 + 기존 signup-onboarding-spec으로 흡수
- GTM 실행 항목 → §4 참조 (Console 트래커에서 관리)
- COVERAGE_AUDIT → 본 인덱스 §5로 흡수
- CANONICAL_MODEL → Envelope(#1 §15)만 선행 고정, 전체 모델은 3번째 국가 온보딩 시

---

## 2. 지원(Support) 경계 확정
사용자 채널(PigOS 앱/이메일/웹폼) → **공통 Support Service·단일 Ticket DB(SSOT)** → Q-Bridge(Console: 인박스·번역·배정·SLA) → 채널 회신. 농장주 리드 DB(Console 컨택DB)와 분리 — 참조 연결만, 병합 금지.

## 3. 오픈 게이트 (문서 승인 + 런타임 강제)

| 오픈 행위 | 문서 게이트 | 런타임 (코드) | CI |
|---|---|---|---|
| 신규 국가 가입 | #3 승인 + 국가 약관 | country_launch_registry.can_signup() | T-R1 |
| 유료 판매 | #2 승인 (D-08·09·10) | entitlement_registry.can_sell() | T-R4 |
| PigSignal 판매 | #4 가동 + 법무 4건 | release_gate.is_approved() | T-R2 |
| 거래연결·리드 | TRANSACTION_MATCHING 옵트인 + 규제 검토 | consent_service.has_purpose() | T-R3 |
| InterPIG UI 노출 | B-02 라이선스 | 기능 플래그 | — |
| 농장주 콜드 발송 | **런 D 리서치 + 변호사 확인 (국가별 옵트인/아웃 상이)** | — | — |

registry 행에도 decided_by·approved_at 필수.

## 4. GTM·마케팅 실행 (Console 도메인에서 관리, 문구 의존성만 여기 기록)
- 통합 제품소개서: 무료 범위 서술 ← #2 승인 후. 분리 원칙 재정의(통합 소개서 허용/CTA 분리) 확인 필요
- 블로그: 1차 완료. 2차(경쟁사 비교) ← Safe Claim Matrix 예외 결정 후
- 농장주 발송: **법무 확인 전 일괄 발송 금지** (런 D §T1-3 결과 대기)
- 비교 메시지: "무료" 강조 금지, 간결·입력용이·쉬운 체크 강조
- 회사소개서 취합 / 국가별 버전 소개(JP는 B-06 후)

## 5. 대표 결정 대기 (미팅 안건)
① Entitlement 결재(D-08 두수 무제한 / D-09 경영 P0 / D-10 R1·R2) ② D-07 KR 데이터 해외 비교 ③ B-06 일본(런 C가 프로필 분리 옵션 생성) ④ Safe Claim Matrix 경쟁사 비교 예외 (+D-03 기간귀속, D-04 경영 KR 노출). → 런 C의 T4가 결정요청서(CEO_DECISION_BRIEF) 생성. 국가 KPI 실사 자료 공유와 동일 미팅 권장.

CTO 선결정: D-01(N/A B안) / D-02(통화 원본보존) / D-05 / D-06.

## 변경 이력
| v0.1~0.2 | 2026-07-21 | 초판 → Q-Bridge 경계·GTM 연결 |
| v0.2.1 | 2026-07-21 | 레포 실경로, 기존 문서 연결, 스켈레톤 통합 정리, 콜드 발송 게이트 추가 |
