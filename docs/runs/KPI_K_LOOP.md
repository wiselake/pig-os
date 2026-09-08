# RUN `KPI-K-LOOP` — K-1~K-4 측정·확정·구현·검증 루프

> **성격**: 자율 실행 · STOP-on-FAIL · 사람 게이트 2곳
> **등록**: 2026-09-08 · 미착수 (전제 미충족)
> **하드룰**: push 금지 · 배포 금지 · 프로덕션 쓰기 금지 · 위조 0

---

## 0. 전제 — 충족 전에는 시작하지 않는다

```
P-1  pigos_ro 읽기 전용 롤 + ubuntu ~/.pgpass          ← ★ 미충족. Brian 1회 작업
P-2  K-2 = (가) 코호트 정본 통일                        ← 판정 완료 (2026-09-08)
     K-2d 115일 폐사 제외 삭제 여부                     ← ★ 미충족. 권고=삭제
```

**둘 다 사람이 해야 한다.** P-1 은 프로덕션 권한 변경이고, P-2 는 정의 결정이다.
어느 쪽도 루프가 스스로 못 넘는다.

### P-1 이 필요한 이유

현재 유일한 조회 경로가 `sudo -u postgres psql` 이고, auto mode 분류기가 원격
`sudo` 를 차단한다. **원격 sudo 를 여는 것보다 SELECT 전용 롤 하나가 안전하다** —
권한 상승 경로를 열지 않고도 측정이 자립한다.

### ★ PII 컬럼 보유 테이블 — 실측 (2026-09-08, 모델 전수)

```
users             email · phone · name · username · password_hash
farms             gps_lat · gps_lng · region · name · farm_code
                  ★ 개인사업 농장은 이것이 곧 개인정보다
organizations     name
pilot_signups     name · email
devices           token                      단말 식별자
audit_log         ip_address · user_agent
                  ★ old_value / new_value 는 JSONB — 기록된 무엇이든 들어올 수 있다
notifications     title · body               내용에 개인정보 유입 가능
consent_ledger    user_id · evidence_ref      동의 증빙 — 식별 연결고리
```

★ **초판 스캔은 `farms` 를 놓쳤다.** 정규식이 `lat` 를 봐서 `gps_lat` 이
안 걸렸다. 지적이 없었으면 목록에서 빠질 뻔했다 — 컬럼명 패턴 매칭만으로
개인정보를 판정하면 안 된다는 사례로 남긴다.

### ★ 그래서 REVOKE 가 아니라 허용목록으로 간다

`GRANT ALL TABLES` 후 빼는 방식은 **새 테이블이 생길 때마다 자동으로 열린다**
(`ALTER DEFAULT PRIVILEGES` 가 그렇게 동작한다). 이 루프가 실제로 필요한 것은
생산 이벤트와 거버넌스 테이블뿐이므로, 처음부터 그것만 준다.

```sql
-- Brian 1회 실행 (프로덕션)
CREATE ROLE pigos_ro LOGIN PASSWORD '<생성>';
ALTER ROLE pigos_ro SET default_transaction_read_only = on;
ALTER ROLE pigos_ro SET statement_timeout = '30s';

GRANT CONNECT ON DATABASE pigos TO pigos_ro;
GRANT USAGE  ON SCHEMA public   TO pigos_ro;

-- 생산 이벤트 (K-1·K-2·K-3 측정 대상)
GRANT SELECT ON sows, matings, farrowings, weanings, removals, breeding_cycles
    TO pigos_ro;

-- 거버넌스 (정의·벤치마크 상태 확인)
GRANT SELECT ON kpi_definitions, benchmarks, source_observations,
                country_kpi_policy, country_kpi_presentation, kpi_snapshots
    TO pigos_ro;

-- farms 는 컬럼 단위로만 — 하베스트/실고객 구분에 data_origin 이 필요하다
GRANT SELECT (id, country, data_origin, data_classification, farm_scale)
    ON farms TO pigos_ro;

-- ★ ALTER DEFAULT PRIVILEGES 는 넣지 않는다. 새 테이블이 자동으로 열리면 안 된다.
```

★ `ALTER DEFAULT PRIVILEGES` 를 쓸 경우 **실행 롤 기준**이므로 마이그레이션 롤이
다르면 `FOR ROLE <migration_role>` 이 필요하다. 위 설계에서는 아예 쓰지 않으므로
이 함정에 걸리지 않는다.

```
ubuntu ~/.pgpass   (chmod 600)
  localhost:5434:pigos:pigos_ro:<비밀번호>
```

★ **비밀번호는 이 세션에 들어오지 않는다.** `psql -h localhost -p 5434 -U pigos_ro
-d pigos` 가 `.pgpass` 에서 읽으므로, 트랜스크립트에 자격증명이 남지 않는다.

★ `default_transaction_read_only` 는 롤 자체를 읽기 전용으로 잠근다 — 권한 설정이
어긋나도 쓰기가 안 나간다. 이중 방어다.

### P-2 — K-2 는 (가)로 정해졌다. 남은 것은 K-2d

```
K-2  (가) 코호트 정본 통일 — 지표 1개
     현행 코호트가 이미 female-cycle 이므로 K-2c 충족. 손 안 대는 게 가장 싼 정본
     Porc d'Or "완료 주기의 교배 중 분만 비율" · PigCHAMP "% of mated females
     that reach farrowing" — 둘 다 코호트·female 단위
     "초교배 분만율"은 신규 산식 + 수요 근거 0(D10) → 백로그만(T6-09)

K-2d 코호트의 "115일 내 폐사 분모 제외" 를 삭제할 것인가   ★ 미결
     권고 = 삭제. 외부 정의는 폐사를 제외하지 않는다
```

**K-2d 가 정해지기 전에는 L3-b 를 시작할 수 없다.** 값이 내려가는 변경이라
What Changed 고지 대상이고, US 분만율 벤치마크와의 비교 가능 여부가 여기서 갈린다.

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
  K-2    (가) 코호트 정본 통일 — 지표 1개
  K-2b   기존 필드명 유지 (신규 필드 없음 — (가)이므로)
  K-2c   female-cycle 단위 — ★ 현행 코호트가 이미 그것. 코드 변경 0
  K-2d   115일 폐사 제외 삭제 여부           ← ★ 미결이면 여기서 STOP
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
   ★ _cohort_farrowing_rate 자체는 손대지 않는다 — 이미 정본이다
     동기간 나눗셈 3경로를 이 함수로 갈아끼우는 작업이다
   + K-2d 가 '삭제'면 115일 폐사 제외 절 제거
   + What Changed 고지 (값이 내려간다)
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
K-2d 미해소 상태에서 L3-b 도달
L1 결과가 안 D 동치 3행을 만족하지 않음
pytest 통과 수 감소
스키마·과금·권한 경계에 손이 닿음
수치를 추정으로 채워야 하는 상황
```

---

## 3. 관련

```
docs/kpi/K1-K4_DECISION_RECORD.md        ③ 결정 · K-2=(가) · K-2d · 안 D 동치 3행
docs/kpi/K1-K3_PRE_DECISION_EVIDENCE.md  ① 런타임 · §5-1 쿼리 · 발견 1~4
docs/kpi/T6_DEFINITION_CONFLICT_REGISTER.md   §0 3축 · 실행 흐름
docs/kpi/D19_THRESHOLD_SOURCE_AUDIT_v1.4.md:29  기존 조회 경로(sudo — 대체 대상)
```
