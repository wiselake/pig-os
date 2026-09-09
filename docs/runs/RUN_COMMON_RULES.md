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

## §0-3 (신설) — RUN 상태 어휘

```
READY_BUT_BLOCKED   착수 조건이 남아 있어 아직 시작하지 않았다.
                    준비용 read-only 조사는 여기 포함된다.
IN_PROGRESS         첫 단계에 실제로 진입했다.
CLOSED              산출물이 나왔고 AC 를 충족했다.
DEFERRED            의도적으로 뒤로 미뤘다. 사유를 함께 적는다.
```

★ **`READY_BUT_BLOCKED` 를 `IN_PROGRESS` 로 적지 않는다.** 준비 조사를 착수로
기록하면, 나중에 기록만 남았을 때 "루프를 이미 돌리기 시작했는데 왜 멈췄나"로
읽힌다. 실제로는 시작한 적이 없는데 중단된 것처럼 보이는 것이다.

경계는 하나다 — **RUN 문서에 정의된 첫 단계에 진입했는가.** 그 전의 코드 읽기·
경로 확인·쿼리 작성은 전부 `READY_BUT_BLOCKED` 안이다.

---

## §0-4 (신설) — 저장소 밖 경로는 Windows 표기로 판독한다

```
bash    /c/dev/pigos-landing        정상 동작
python  /c/dev/pigos-landing        → C:\c\dev\pigos-landing 로 해석 → 없음
```

2026-09-09 에 이 차이로 **존재하는 저장소를 "머신에 없음"으로 보고**했다.
bash 쪽 스캔이 같은 문자열로 잘 돌아가고 있어서 오류가 드러나지 않았다.

```
규칙   이 저장소 밖 경로는 Windows native 표기(C:\dev\...)로 확인한다
       존재 여부 판정은 한 도구의 결과만으로 확정하지 않는다
```

★ 부재를 보고하기 전에 **다른 도구로 한 번 더 본다.** "없다"는 판정은 "있다"보다
검증이 약한 쪽으로 기울기 쉽다 — 찾지 못한 것과 없는 것은 다르다.

---

## §0-5 (신설) — ENVIRONMENT NOTE

RUN 진행과 무관한 환경 관측은 **blocker 가 아니라 NOTE 로 남긴다.** 무관한 항목을
STOP 조건 옆에 두면 게이트의 신뢰도가 떨어진다.

```
2026-09-09  MCP 커넥터 미인증 (Figma · Canva · Google Drive · Gmail 등)
            KPI·법무 트랙에 사용되지 않음 → blocker 아님
            필요 시 claude.ai 커넥터 설정에서 승인
```

---

## 기준값 (2026-09-09 실측)

```
백엔드   pytest --collect-only   1418      (2026-09-09 로케일 파리티 가드 +3)
         pytest 전량             1417 passed · 1 skipped
         ruff                    3건 — F841(미사용 지역변수)만 잔존.
                                 나머지 8건은 CHORE-RUFF-CLEANUP 에서 정리됨

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
