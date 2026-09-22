# PigOS

> Global Swine Farm Management SaaS + Data Monetization Platform
> 피그플랜 27년 양돈 노하우 기반 글로벌 버전

---

## 세션 프로토콜 규칙

1. **세션 시작 시** CLAUDE.md + PROGRESS.md를 읽고 현재 상태를 3줄 이내로 요약 보고
2. **태스크 완료마다** PROGRESS.md 현재상태 갱신 후 `git commit`
3. **컨텍스트가 커지면** 사람에게 `/clear` 권유 (대화가 길어져 응답이 느려지거나, 한 세션에서 대형 태스크 3개 이상 완료 시)
4. **UI 텍스트 추가/변경 시** `src/messages/` 아래 **en/ko/zh/es/vi/th/pt/ru 8개 파일 모두** 동시 업데이트 (누락 금지). `i18n.test.ts`가 키 파리티 강제. **컴포넌트/페이지에 인라인 `{en,ko,...}` 딕셔너리 금지 — 반드시 messages 파일 + `useTranslations`** (언어 표시명 상수 LANG_LABELS류만 예외). 언어 추가 = JSON 1개만 추가하면 끝.
5. **웹에 기능·약관·API 계약이 붙거나 바뀌면** `docs/PLATFORM_PARITY.md`에 한 줄 추가.
   모바일(Android·iOS)은 **독립 저장소 2개**라 자동으로 따라오지 않는다.
   셀 상태는 `platform_implementation_status` — `PLANNED`/`IN_PROGRESS`/`DONE`/
   `PENDING_RECHECK`/`BLOCKED`/`NOT_APPLICABLE`(사유 필수).
   ★ **`DONE` 은 implementation commit SHA 필수** — 없으면 `IN_PROGRESS`.
   ★ **서버가 옳다고 모바일도 옳은 게 아니다** (D-13 B′ 로 반증됨).
   ★ 특히 **API 계약 변경(nullable 여부·필드 추가/삭제)은 기능보다 위험하다** —
   모바일은 배포 주기가 길어 구버전이 오래 남는다.
6. **사용자 노출 기능/수치가 바뀌면** `docs/LANDING_SYNC.md`(랜딩 동기화 정본)를 갱신. 랜딩페이지(pigos.io, `c:/dev/pigos-landing`)는 이 문서를 참조해 `FACTS.md`를 맞춘다. **위조 0**: `[확정]`만 랜딩에 사실로 노출, `[베타/검증중]`은 hedge, `[내부]`는 비노출.

---

## 프로젝트 개요

- **제품**: PigOS — 해외 양돈 농장용 Farm Management SaaS
- **도메인**: **pigos.io** (2026-05-18 구매 확정)
- **포지셔닝**: 벤더-중립 독립 데이터 플랫폼 + 오픈 연동 생태계
- **전략**: 무료 제공 → 데이터 수집 → 수익화 → 농가 배분
- **타겟 시장**: **5개 글로벌 시장 (US · CN · SEA[VN+TH] · LatAm · KR) × 8개 언어** — LANDING_SYNC §3 [확정], 로그인 문구 "5 global markets · 8 languages"
  - **KR = 레퍼런스 전용** (대표 확인 2026-08-05): 공개 마케팅 타겟 아님. **실고객 가입 차단**(jurisdiction KR gate `signup_blocked`, reason `KR_REFERENCE_ONLY`) + **대표 override**(`allow_kr_signup` env=True인 확인용 환경에서만 해제, 서버 env라 클라 우회 불가). 온보딩 기본 국가=US. 한국법(PIPA·준거법·법정보존)은 회사 본국법으로 계속 적용. ko 로케일=대표 검토용
  - **EU·GB = 현재 타겟 아님**: 대리인 계약 불요(부속조항은 향후 진출 대비 보존)
  - **LatAm 갭**: 현재 BR(pt)만 커버. 스페인어권(멕시코·콜롬비아 등)·러시아어권(CIS)은 리서치·부속조항 미비 — 활성화 전 보완
- **처리 법역(consent 커버리지 — 타겟과 별개)**: KR·US·EU·GB·BR·TH·VN·CN + OTHER — 법 적용·부속조항·jurisdiction 리졸버 범위

---

## 기술 스택 (MVP)

| 영역 | 기술 |
|------|------|
| Backend | FastAPI (Python) → Phase 2+ Spring Boot (Java 21) |
| Frontend | Next.js + TypeScript |
| Mobile | React Native (Android + iOS 공용) |
| DB | PostgreSQL 16+ (Shared Schema + farm_id) + TimescaleDB (IoT) |
| Cache | Redis 7+ |
| Infra | AWS (서울 리전, ap-northeast-2) + Docker + Kubernetes |
| Mobile Android | Kotlin + Jetpack Compose + Room + WorkManager + Retrofit |
| Mobile iOS | Swift + SwiftUI (Android 안정화 후 Phase 2) |
| Offline Sync | Room (Android) / Core Data (iOS) — sync protocol: docs/specs/2026-05-19_offline-sync-spec.md |
| Background Jobs | ARQ (Redis 기반) |

> **Mobile 결정 근거 (2026-06-05)**: 현장 작업자 + Android 우선 + 오프라인 입력 + 저사양 기기 + 백그라운드 동기화 조합에서
> React Native보다 Native가 더 안정적. Room/WorkManager/DataStore로 오프라인-퍼스트 아키텍처가 구조적으로 깔끔하고,
> 카메라·푸시·배터리·네트워크 복구 대응도 Native가 유리. 공용 자산: FastAPI API, OpenAPI 스펙, sync protocol, KPI 공식, 디자인 토큰.

---

## 폴더 구조

```
pig-os/
├── CLAUDE.md           ← 이 파일
├── docs/
│   ├── specs/          ← DB 스키마, KPI 계산식, API 스펙
│   ├── master-data/    ← 시드 데이터 (질병코드, 백신, 벤치마크)
│   └── api/            ← OpenAPI 스펙
├── api/                ← 백엔드 소스 (FastAPI, uv) — app/engine, app/jobs, alembic
├── src/                ← 프론트엔드 (Next.js 15, npm)
└── tests/              ← 테스트
```

---

## 핵심 설계 원칙

1. **모듈형 구조**: 11개 모듈 독립 배포 가능 (49 테이블)
2. **지역 중립**: 단일 스키마로 8개 법역 커버 (KR·US·EU·GB·BR·TH·VN·CN + OTHER, country_configs)
3. **Multi-tenant Strategy**: Shared Database / Shared Schema
   - 모든 테넌트 범위 테이블은 반드시 `farm_id` 컬럼 포함
   - 접근 제어는 organization hierarchy + farm membership + row-level filtering으로 강제
   - 향후 엔터프라이즈 고객 요청 시 schema-per-tenant를 선택적 프리미엄 아키텍처로 검토 가능
4. **월마감 잠금**: `period_locks`로 확정 데이터 수정 차단
5. **감사 추적**: 모든 CUD → `audit_log`
6. **오프라인 동기화**: `sync_queue` + WatermelonDB (Last-Write-Wins)
7. **Soft Delete**: `deleted_at` 패턴 (모든 핵심 테이블)
8. **API 버전 관리**: `/api/v1/` URL prefix 고정 (헤더 방식 사용 안 함)

---

## Q&A Architecture Decision

PigOS Q&A는 Rule-grounded 아키텍처를 사용한다.

```
사용자 질문
    ↓
Intent 분류
    ↓
KPI / 이벤트 / Rule / Snapshot 조회
    ↓
Rule Engine → Structured Result 생성
    ↓
Renderer (Base: 템플릿 | Addon #1: LLM)
    ↓
사용자 응답
```

| 구분 | MVP / Base | Addon #1 (AI Insight) |
|------|-----------|----------------------|
| 엔진 | Rule Engine only | Rule Engine + LLM |
| 응답 | 정형 텍스트 (템플릿) | 자연어 설명 |
| 비용 | 없음 | LLM API 비용 발생 |
| 목적 | 기능 검증 | 유료 가치 제공 |

**핵심 원칙**:
- LLM은 **판단 금지** — 검증된 Rule Engine 결과를 자연어로 변환하는 역할만 수행
- Rule Engine은 항상 `Structured Result` (JSON)를 생성하고, Renderer가 응답 형태를 결정
- LLM 벤더 교체 (Claude ↔ GPT-4o) 시 Rule Engine 코드 변경 없이 Renderer만 교체 가능

**Structured Result 예시**:
```json
{
  "intent": "explain_fcr",
  "severity": "warning",
  "kpi": "FCR",
  "current_value": 3.12,
  "target_value": 2.85,
  "causes": [
    "feed_intake_increased",
    "daily_gain_decreased",
    "mortality_increased"
  ],
  "recommended_actions": [
    "check_feed_waste",
    "review_group_health",
    "compare_finisher_group_performance"
  ]
}
```

**통신 방식**: MVP는 REST (`POST /api/v1/farms/{farm_id}/chat/query`), 추후 WebSocket 추가

**구현 위치**:
- `api/app/engine/rule_engine.py` — RuleContext, Finding, StructuredResult, RuleRegistry, RuleEngine
- `api/app/engine/rules/base.py` — Base 규칙 (NPD/PSY/Farrowing/Inventory)
- `api/app/engine/renderer.py` — Template Renderer (en/ko) — Addon #1에서 LLM으로 교체
- `api/app/services/chat_service.py` — intent 분류 + RuleEngine 호출
- `api/app/routers/base/chat.py` — HTTP 엔드포인트

---

## KPI 계산 전략

> ## ★ 현황 경고 (2026-08-28 실측)
>
> 아래 표는 **목표 아키텍처**다. 현재 운영과 다르다.
>
> ```
> kpi_snapshots 행 수          0        (2026-05-29 이래 단 한 건도 기록된 적 없음)
> daily/weekly/monthly 집계   매일 실행되나 71농장 전건 실패
> 실패 사유                 KpiSnapshot 모델에 farrowing_rate 컴럼이 없다
> 대시보드 실제 동작       요청 시 계산 + Redis 30초 캐시
> ```
>
> 근거: `docs/runs/RUNTIME_INTEGRITY_AUDIT_20260828.md`
>
> **스냅샷이 동작 중이라고 가정하고 기능을 설계하지 말 것.**
> 스냅샷 의존 기능(What Changed · 스냅샷-first Home · 과거비교 · 오프라인 read-cache)은
> 파이프라인 수정이 선행되어야 한다.

| 용도 | 방식 (목표) | 현재 상태 |
|------|------|------|
| 대시보드 첫 화면 | `kpi_snapshots` 테이블 조회 (스냅샷) | **미동작** — 요청 시 계산 중 |
| 월간 리포트 | 스냅샷 | **미동작** |
| Q&A 분석 | 스냅샷 우선 + 필요 시 실시간 상세 조회 |
| 개별 이벤트 상세 | 실시간 계산 |
| 데이터 수정 직후 | 해당 기간 스냅샷 즉시 재계산 |

**백그라운드 잡 (ARQ)** — ★ 아래 3건은 현재 **전건 실패 중**이다(위 경고):
- `daily_kpi_aggregation` — 매일 00:00
- `weekly_kpi_aggregation` — 매주 월요일
- `monthly_kpi_aggregation` — 매월 1일
- `recalculate_snapshot_on_event_change` — 이벤트 변경 시 트리거

---

## 기획 문서 (biz-report-os 프로젝트)

심층분석 기획서 및 회의 자료는 별도 프로젝트에서 관리:
- `c:/dev/biz-report-os/projects/pig-os/docs/`
- GlobalStrategy.html (심층분석 16개 섹션)
- Meeting2_Prep.html (2차 회의 준비)
- 참고문서/ (지역별 관리포인트, 경쟁사 분석, 개발반영사항)

---

## 현재 상태 / 다음 할 일

> MVP 스프린트(2026-06~07) 출시 완료. 6월 자율 스프린트 상세 기록은 하단 "자율 실행 플랜(아카이브)".
> 현재 작업 지도: `docs/PIGOS_SPEC_INDEX.md` · 일정: `docs/planning/MASTER_SCHEDULE_2026-07.md`.
> 진행 중(2026-08): consent 인프라(국가별 약관·목적별 동의)·KPI v0.4 국가정책·법무 트랙(부속조항 v1.4·LIA·게시후보본)·테스트 하드닝.

---

## Phase 2 기능 (MVP 이후)

### Task 자동배정 시스템 (노동력 절감)
> 출처: National Hog Farmer 2026-05-20 — AI 기반 노동력 절감이 양돈 산업 핵심 혁신 요소

```
Rule Engine Alert → Task 자동생성 → 담당자 배정 → 모바일 알림 → 완료 체크
```

- DB: `tasks` 테이블 (farm_id, assigned_to, rule_id, due_at, completed_at, priority)
- 모바일: "오늘 할 일" 홈 화면 (아침에 앱 열면 자동 목록)
- 예시: A-042 분만 115일 초과 → 수의사에게 자동 Task 발송

### PRRS 유전자 성과 추적
- `sow.breed` + `health_events.disease_code` 연결 → 품종별 PRRS 발생률 비교 분석

### Traceability Addon (소비자 투명성)
- 농장 이벤트 → 도축장 코드 → 소비자 QR 스캔 이력 추적
- B2B 데이터 판매 프리미엄 버전

---

## 자율 실행 플랜 (아카이브)

> 2026-06 MVP 자율 스프린트(Phase 1~14, 54/54 완료) + 자율 실행 지침(Autonomous Mode)은
> `docs/archive/AUTONOMOUS_SPRINT_2026-06.md`로 이관(2026-08-05) — 역사적 기록.

---

## 프론트엔드 구조 & 컨벤션

### 폴더 배치 (실제 확인, 2026-06-04 기준)

```
src/
├── app/
│   ├── layout.tsx               ← 루트: Providers(next-intl + TanStack + auth 인터셉터)
│   ├── globals.css              ← 라이트 테마 CSS 변수 토큰
│   ├── providers.tsx
│   ├── page.tsx                 ← 루트 "/" = 대시보드 (현재 Sidebar 직접 import, Shell 이전 예정)
│   ├── (auth)/
│   │   ├── layout.tsx           ← 로그인 전용 centered 레이아웃 (#0F1B2D 배경)
│   │   └── login/page.tsx
│   ├── onboarding/page.tsx      ← Shell 없는 독립 페이지 (다크 배경 #0F172A)
│   ├── kpi/page.tsx
│   ├── chat/page.tsx
│   ├── sows/page.tsx
│   ├── sows/[id]/page.tsx
│   ├── finishers/page.tsx
│   ├── piglets/page.tsx
│   └── record/page.tsx
├── components/
│   ├── Sidebar.tsx              props: { lang?: "en"|"ko", onAskAI?: () => void } — collapsed 내부 state
│   ├── Topbar.tsx               props: { lang?, onLangToggle?, onQuickInput?, onBell?, alertCount? }
│   ├── BottomNav.tsx            props: { lang?, onAskAI?, alertCount? } — md:hidden 고정
│   ├── QuickInputDrawer.tsx     props: { open: boolean, onClose: () => void, lang? }
│   ├── AskAiDrawer.tsx          props: { open: boolean, onClose: () => void, context?, lang? }
│   └── ui/                      ← Stat, AIBubble, AIAction, Card, PipeItem 등 공용 UI
├── store/
│   └── auth.store.ts            Zustand + persist(localStorage). 필드: user(UserProfile|null), accessToken, refreshToken, activeFarmId
├── lib/
│   └── api/
│       ├── client.ts            ← axios 인스턴스 + 인터셉터
│       ├── queryKeys.ts
│       └── endpoints/           ← auth, farms, kpi, chat, sows, events, finishers, piglets, sync
└── types/
    └── api.types.ts             ← UserProfile, ChatResponse, FindingOut, Alert, SowStatus, ...
```

### 페이지 구조 (Shell 통합 전)
- 모든 app 페이지가 직접 `<Sidebar />` import + `ml-[220px]` offset 사용
- `/dashboard` 페이지 없음 — 대시보드는 루트 `/`(page.tsx)
- Shell 통합 후 `(app)/` 라우트 그룹 아래로 이동 예정

### 상태관리 경계
| 계층 | 도구 |
|------|------|
| 서버 데이터 (fetch/cache) | TanStack Query |
| 전역 클라이언트 (auth) | Zustand (persist) |
| URL 연동 필터/탭 | `useSearchParams` / URL |
| UI 로컬 (open/close 등) | useState |

### 디자인 토큰 (globals.css CSS 변수)
- 배경: `bg-background`, `bg-surface`, `bg-bg`, `bg-bg2`, `bg-panel-hi`
- 텍스트: `text-text`, `text-text1`, `text-text2`, `text-text3`, `text-muted`, `text-faint`
- 테두리: `border-border`
- 브랜드: `bg-navy` (#0D1B3E), `bg-primary` (blue #2563EB), `bg-snout` (pig snout 색상), `text-gold`
- 시맨틱: `text-success`, `text-danger`, `text-warning`, `text-purple`
- 숫자·코드: `font-mono` (JetBrains Mono)

---

## 스펙 문서 체계 (2026-07-21 신설)

- **진입점**: `docs/PIGOS_SPEC_INDEX.md` — 전 스펙의 지도. 세션 시작 시 참조.
- 핵심 스펙: `docs/specs/COUNTRY_KPI_RULE_SPEC_v0.3.1.md` (국가별 KPI 정책·룰·경영 KPI. v0.4 개정 진행 중)
- 결재 대기: `docs/product/PIGOS_FEATURE_ENTITLEMENT_MATRIX.md` (무료/유료 SSOT — **승인 전 paywall·과금 구현 금지**)
- 밤샘 런 프롬프트: `docs/runs/` (A 정책벡터 / B Envelope / C v0.4+evidence / D 법무 리서치)
- 일정: `docs/planning/MASTER_SCHEDULE_2026-07.md`
- **핵심 규율**: 위조 0은 수치와 결정 모두에 적용 — Decision Register에서 APPROVED 아닌 정책은 코드·seed에 반영 금지. 미검증 벤치마크는 UNVERIFIED_DRAFT 격리.
- ⚠️ 상단 "전략: 무료 제공 → 데이터 수집 → 수익화 → 농가 배분" 중 **"농가 배분"은 2026-07-21 회의에서 방향 변경** (대가 = 현금 배분이 아니라 벤치마크 인사이트 환원). 본문 수정은 대표 확인 후.
