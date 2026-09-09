# RUN 공통 규칙 §0 — PREFLIGHT 와 종료 판정

> **개정**: 2026-09-09 (`ENV-1-NODE-DETERMINISM`)
> **적용**: `docs/runs/` 의 모든 RUN. 각 RUN 문서가 §0 을 복사하지 말고 이 문서를 참조한다.
> **하드룰**: push 금지 · 배포 금지 · 프로덕션 쓰기 금지 · 위조 0

---

## 0. 왜 개정했는가

**환경이 틀린 것과 코드가 틀린 것은 다른 사건이다.** 옛 §0 은 둘을 한 상태로 묶어서,
환경 문제가 코드 회귀처럼 보고됐다.

```
2026-09-08  백엔드 전량 실행 → 663 ERROR
            원인: Docker Desktop 다운 (pigos-postgres Exited 255)
            복구 후 재측정: 1414 passed
            → 코드 회귀 0. 그런데 STOP-on-FAIL 게이트는 터졌다

2026-09-09  프론트 vitest → jsdom 38건 실패처럼 보임
            원인: node 22.11 은 require(esm) 이 기본 꺼짐 (22.12+ 에서 기본)
            → 코드 회귀 0. 게다가 NODE_OPTIONS 플래그로 덮여 있어 원인이 가려져 있었다
```

두 건 모두 **테스트 실패가 아니었다.** 그런데 실패로 집계되면 RUN 이 헛돈다.

---

## §0-1 (개정) — 베이스라인 + PREFLIGHT

시작 전 순서.

```
1  hostname == bjh 확인        아니면 STOP (brian = 읽기 전용)

2  PREFLIGHT — 하나라도 미충족이면 ENVIRONMENT_INVALID 로 즉시 종료
   ★ 이것은 STOP-on-FAIL 이 아니다. 실패 카운트에 넣지 않고 코드 회귀로 기록하지 않는다.

   P-a  백엔드   pigos-postgres 컨테이너 Running
                 Exited/부재 → ENVIRONMENT_INVALID
   P-b  프론트   node --version ∈ package.json engines 범위
                 밖이면 ENVIRONMENT_INVALID
   P-c  수집 수  pytest --collect-only 가 직전 RUN 기록값과 같은가 (±0)
                 어긋나면 사유 기록 후 계속 (종료 조건 아님)

3  PREFLIGHT 통과 후에만 전량 실행 → BASELINE_PASS / BASELINE_FAIL 기록
```

### ENVIRONMENT_INVALID 보고 형식

세 줄이면 된다 — **어떤 항목이 / 실제값 vs 기대값 / 복구 방법 한 줄.**

```
ENVIRONMENT_INVALID: test database unreachable at 127.0.0.1:5433/pigos_test
  actual: OperationalError: connection refused
  expected: pigos-postgres container Running
  fix: docker start pigos-postgres pigos-redis
```

### 자동 검사 — 사람이 기억하지 않는다

```
프론트   src/scripts/preflight-node.mjs
         package.json 의 pretest / pretest:run 에 물려 있어 npm test 앞에서 자동 실행
         engines 범위 밖 → exit 78
         ★ NODE_OPTIONS=--experimental-require-module 가 남아 있어도 exit 78
           (버전 불일치를 플래그로 덮던 과거로 되돌아가지 않도록)

백엔드   api/tests/conftest.py :: pytest_collection_modifyitems
         integration 테스트가 수집됐을 때만 DB 를 확인 → 불가면 pytest.exit(78)
         ★ skip 하지 않는다. skip 은 조용히 0건 통과하는 구멍이다
         ★ unit 만 돌릴 때는 막지 않는다 — 불필요한 의존성 강제는 새로운 오탐이다
```

★ **종료 코드 78 을 쓰는 이유**: pytest 자신의 코드는 0~5, vitest 실패는 1 이다.
78 은 그 어느 것과도 겹치지 않으므로 CI·RUN 게이트가 "테스트 실패"로 오탐하지 않는다.

---

## §0-2 (개정) — 종료 판정

```
STOP-on-FAIL          PREFLIGHT 통과 후의 통과 수 감소만 해당한다

TEST_ENV_FAILURE      환경 실패로 인한 대량 ERROR. 복구 후 재측정한 값을 최종 판정으로 쓴다
                      예) 2026-09-08 663 ERROR = Docker 다운 → 복구 후 1414 passed
                          TEST_ENV_FAILURE → RECOVERED

ENVIRONMENT_INVALID   PREFLIGHT 단계에서 걸러진 것. 실행 자체를 하지 않았으므로
                      통과/실패 수를 기록하지 않는다
```

★ **환경 실패를 "복구했으니 없던 일"로 지우지 않는다.** `TEST_ENV_FAILURE → RECOVERED`
로 남긴다. 같은 환경 문제가 반복되면 그것 자체가 고칠 대상이라는 신호다.

---

## 기준값 (2026-09-09 실측)

```
백엔드   pytest --collect-only   1415
         pytest 전량             1414 passed · 1 skipped
         ruff                    11건 — 전부 선존(미사용 import·미사용 지역변수·정렬).
                                 신규 코드는 clean

프론트   node                    22.23.2   (.nvmrc · engines ">=22.12.0 <23")
         vitest                  40 파일 · 217 tests   ★ NODE_OPTIONS 불필요
         tsc --noEmit            통과
```

### Node 버전 — 실측으로 확정한 것만 적는다

```
v20.11.1   vitest 기동 불가 (styleText 미지원)          ← 이 머신의 기본값이었다
v22.11.0   jsdom 38건 실패 (require(esm) 기본 꺼짐)
v22.12.0   전량 통과 확인 — engines 하한의 근거
v22.23.2   전량 통과 확인 — .nvmrc 정본
```

★ `22.22.3`(옛 루트 `.nvmrc`)은 **검증하지 않았다.** 그래서 채택하지 않고
`.nvmrc` 를 22.23.2 로 통일했다 — 검증하지 않은 값을 정본으로 쓰지 않는다(위조 0).

---

## 관련

```
docs/runs/KPI_K_LOOP.md              P-1~P-3 전제
src/scripts/preflight-node.mjs       프론트 PREFLIGHT
api/tests/conftest.py                백엔드 PREFLIGHT
src/.nvmrc · .nvmrc                  22.23.2 (통일)
src/package.json                     engines.node ">=22.12.0 <23" · pretest 체인
```
