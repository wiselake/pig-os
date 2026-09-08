# RUN `KPI-K-LOOP` — K-1~K-4 측정·확정·구현·검증 루프

> **성격**: 자율 실행 · STOP-on-FAIL · 사람 게이트 2곳
> **등록**: 2026-09-08 · 미착수 (전제 미충족)
> **하드룰**: push 금지 · 배포 금지 · 프로덕션 쓰기 금지 · 위조 0

---

## 0. 전제 — 충족 전에는 시작하지 않는다

```
P-1  pigos_ro 읽기 전용 롤 + ubuntu ~/.pgpass          ← ★ 미충족. Brian 1회 작업
P-2  K-2 REOPENED 해소 (가/나 택일)                     ← ★ 미충족. Brian 판단
```

**둘 다 사람이 해야 한다.** P-1 은 프로덕션 권한 변경이고, P-2 는 정의 결정이다.
어느 쪽도 루프가 스스로 못 넘는다.

### P-1 이 필요한 이유

현재 유일한 조회 경로가 `sudo -u postgres psql` 이고, auto mode 분류기가 원격
`sudo` 를 차단한다. **원격 sudo 를 여는 것보다 SELECT 전용 롤 하나가 안전하다** —
권한 상승 경로를 열지 않고도 측정이 자립한다.

```sql
-- Brian 1회 실행 (프로덕션)
CREATE ROLE pigos_ro LOGIN PASSWORD '<생성>';
GRANT CONNECT ON DATABASE pigos TO pigos_ro;
GRANT USAGE  ON SCHEMA public   TO pigos_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO pigos_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO pigos_ro;

-- ★ 개인정보 테이블은 빼는 편이 낫다 (세션 하드룰: 개인정보 컬럼 SELECT 금지)
REVOKE SELECT ON users FROM pigos_ro;
```

```
ubuntu ~/.pgpass   (chmod 600)
  localhost:5434:pigos:pigos_ro:<비밀번호>
```

★ **비밀번호는 이 세션에 들어오지 않는다.** `psql -h localhost -p 5434 -U pigos_ro
-d pigos` 가 `.pgpass` 에서 읽으므로, 트랜스크립트에 자격증명이 남지 않는다.
이것이 접속 문자열을 직접 받는 것보다 나은 이유다.

### P-2 가 필요한 이유

`K1-K4_DECISION_RECORD.md` §2 — K-2 의 전제(`mating_number` = 생애 초교배)가
틀렸음이 확인돼 REOPENED 다.

```
(가) 코호트 정본 통일     지표 1개. farrowing_rate_first_service 신규 필드 없음
(나) 병존 유지            두 번째 지표를 새로 정의해야 한다 (현행 코드에 없다)
```

**루프가 이것을 대신 정하면 안 된다.** 정의 결정이고, 잘못 고르면 L3-b 가
통째로 헛작업이 된다.

---

## 1. 단계

### L1 — 측정 (자율)

```
§5-1 쿼리 3건 (K-1 사산·미라 / K-2 mating_number 충전율 / K-3 모집단 3종)
  + gilt_mated_deleted_only        소프트 삭제 비대칭
  + 프로덕션 env use_governance_benchmarks    ★ 가장 먼저

→ K-3 영향표 완성
```

★ **표기 규율**: 수치는 **산식 감도**로만 적는다. 모집단이 하베스트 42농장이므로
"고객 영향" 문장은 금지(실고객 7농장 최대 7두).

★ **분기**: `use_governance_benchmarks = True` 로 나오면 **K-1 을 P0 로 격상**하고
L1 나머지보다 먼저 보고한다(현재 오노출).

### L2 — 확정 (자율 + 게이트)

```
DECIDED 로 전환하고 L1 수치를 결정문에 첨부
  K-1b   V2 신설 · V1 RETIRED
  K-2b   기존 필드명 유지 + 코호트          ← ★ P-2 결과에 종속
  K-2c   female-cycle 단위                   ← ★ 현행 코호트가 이미 그것
  K-3    안 D (초교배일 기준)                ← L1 결과가 안 D 조건 3행을 만족할 때만
  K-4    WEANED_PER_MATED_FEMALE_YEAR

▶ GATE-1 — 멈추고 보고
```

★ K-3 은 **자동 확정 금지**. `mated_ever` 가 NPB `Average Mated Sow Inventory` 와
동치인지(결정문 §3 3행)를 L1 수치로 확인한 뒤에만 DECIDED 로 간다. 어긋나면
DECIDED 대신 사유를 적고 GATE-1 로 간다.

### L3 — 구현 (새 세션 · 단계마다 별도 커밋)

```
a  definition_id_for() 버전 인자화 + STILLBIRTH V2 행
   + 벤치마크 재도출(raw_fields_json) + mummy_rate 신설
b  farrowing_rate 코호트 통일 (trend · report · snapshot)
   + first_service 필드            ← ★ P-2 가 (나)일 때만
   + What Changed 고지
c  PSY/NPD 모집단 → 초교배일 기준
   + jobs/kpi.py:135 부정목록 → exit_date 기준
d  라벨 / 정의 배지 (K-4) — 8 로케일

각 단계 후 pytest 전량. 통과 수 감소 시 즉시 STOP.
마이그레이션은 커밋 분리. ★ 프로덕션 alembic 실행 금지.
```

★ **1변경 = 1커밋 = 단일 변수.** a·b·c 를 섞으면 어느 것이 값을 움직였는지 못 가린다.

### L4 — 검증 (새 세션)

```
D-19 기준을 PSY · NPD · 분만율에 적용
  ① RUNTIME = ② DOCUMENTED = ③ CANONICAL
  + automated test
  + 실데이터 수기 검산

→ CONFIRMED 또는 미충족 사유

▶ GATE-2 — 보고. push 없음
```

★ PSY 를 **reference implementation** 으로 먼저 닫는다.

---

## 2. STOP 조건

```
pigos_ro 접속 실패
K-2 REOPENED 미해소 상태에서 L2 도달
L1 결과가 안 D 동치 3행을 만족하지 않음
pytest 통과 수 감소
스키마·과금·권한 경계에 손이 닿음
수치를 추정으로 채워야 하는 상황
```

---

## 3. 관련

```
docs/kpi/K1-K4_DECISION_RECORD.md        ③ 결정 · K-2 REOPENED · 안 D 동치 3행
docs/kpi/K1-K3_PRE_DECISION_EVIDENCE.md  ① 런타임 · §5-1 쿼리 · 발견 1~4
docs/kpi/T6_DEFINITION_CONFLICT_REGISTER.md   §0 3축 · 실행 흐름
docs/kpi/D19_THRESHOLD_SOURCE_AUDIT_v1.4.md:29  기존 조회 경로(sudo — 대체 대상)
```
