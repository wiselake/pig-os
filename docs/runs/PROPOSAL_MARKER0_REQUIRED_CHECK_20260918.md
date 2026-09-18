# 제안 — 마커-0 enforcer 를 main 의 required status check 로 승격

> 상태: **제안서. 설정 변경·적용 없음.** (주말 런 G5) 적용은 Brian 의 branch-protection 편집 한 번이다.
> 근거 값은 전부 2026-09-18 실측 (`gh api repos/wiselake/pig-os/branches/main/protection`, `.github/workflows/ci.yml`).

## 1. 지금 상태

```
required_status_checks   strict=true · contexts = ["backend (3.12)", "backend (3.14)", "frontend"]
enforce_admins           true
required reviews         0
enforcer 위치            backend job 안의 pytest 전체(tests/) 에 포함
                         · api/tests/integration/test_public_legal_no_internal_markers.py  (런타임 사본 + APPROVED 문서 + manifest DRAFT 표기 + 재동기화 금지)
                         · api/tests/integration/test_publication_gate.py                  (격리 정직성 · 마커 수 == 격리 기록 · publish_candidate 미참조)
                         · scripts/verify_public_notice.sh                                  (배포 후 실서버 5항목 — CI 밖, 수동)
```

**문제 아닌 것**: enforcer 는 이미 required 인 `backend (3.12)`/`(3.14)` 안에서 돈다. 지금도 마커가 생기면 main 에 못 들어간다.

**문제인 것**:
1. **신호가 섞인다.** backend job 이 빨간 이유가 ruff 인지, 마이그레이션인지, 마커인지 체크 이름으로는 알 수 없다. 법무 마커는 다른 실패와 성격이 다르다(코드 버그가 아니라 "게시하면 안 되는 것"). 결재 화면에서 한 줄로 보여야 한다.
2. **통과 조건이 헐겁다.** pytest 는 `-p no:cacheprovider` 로 전체를 돌린다. 누가 `pytest -k "not legal"` 로 워크플로를 고치거나 파일을 `skip` 하면 backend 는 여전히 초록이다. required check 가 enforcer **자체**를 이름으로 가리키면 그 우회가 protection 위반으로 드러난다.
3. **publish_candidate 쪽 enforcer 는 CI 에 없다.** `verify_public_notice.sh` 는 실서버(`https://api.pigos.io`) 를 curl 하는 배포 후 검증이라 PR 시점에 돌 수 없고, 돌아서도 안 된다(프로덕션 읽기). 대신 **빌드 산출물 수준**(런타임 사본 `api/content/legal/public_privacy.*`) 은 PR 시점에 검증 가능하고 이미 테스트가 있다 — 별도 job 으로 분리만 하면 된다.

## 2. 제안

### 2-1. CI 에 독립 job `legal-markers` 추가 (DB services 포함 · 1분급)

```yaml
  legal-markers:
    # 법무 게시 경계 — 코드 테스트와 분리해 결재 화면에 한 줄로 보이게 한다. DB·Redis 없음.
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: api } }
    services: { postgres: <backend 와 동일>, redis: <backend 와 동일> }   # 통합 conftest PREFLIGHT 가 DB 연결을 요구한다 (실측)
    env: { DATABASE_URL: <backend 와 동일>, TEST_DATABASE_URL: <backend 와 동일>, REDIS_URL: <backend 와 동일> }
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv python install 3.12
      - run: uv sync --python 3.12
      - name: Runtime copy · approved docs · manifest — zero internal markers
        run: uv run pytest -q -p no:cacheprovider
               tests/integration/test_public_legal_no_internal_markers.py
               tests/integration/test_publication_gate.py
      - name: Enforcer files are present and not skipped
        run: |
          test -s tests/integration/test_public_legal_no_internal_markers.py
          test -s tests/integration/test_publication_gate.py
          ! grep -nE 'pytest\.mark\.(skip|xfail)' tests/integration/test_public_legal_no_internal_markers.py
```

- **실측(2026-09-18)**: 두 파일의 테스트 함수는 `db`/`client` fixture 를 쓰지 않지만, `tests/integration/conftest.py` 가 import 시점에 엔진을 만들고 세션 시작 시 PREFLIGHT 로 DB 연결을 검사한다 — 도달 불가 URL 로 돌리면 `PREFLIGHT ... expected: pigos-postgres container Running` 으로 멈춘다. 따라서 이 job 은 **DB 없이 돌지 않는다**. 적용 시 선택: (a) backend 와 같은 `services: postgres/redis` 블록을 붙인다(간단, +20초) · (b) 두 파일을 `tests/legal/` 로 옮겨 통합 conftest 밖에 둔다(깨끗하지만 파일 이동 = PR #2/#3 충돌). **(a) 권고.**
- `verify_public_notice.sh` 는 그대로 **배포 후** 절차로 둔다(RELEASE_PACKET §3-1 ⑪). CI 에 넣지 않는다.

### 2-2. branch protection 변경 (한 번, Brian)

```
contexts: ["backend (3.12)", "backend (3.14)", "frontend"]
       → ["backend (3.12)", "backend (3.14)", "frontend", "legal-markers"]
strict=true · enforce_admins=true 유지
```

★ 순서: **job 이 main 에서 최소 1회 초록** 이어야 GitHub 이 context 이름을 required 로 받는다. 즉
① ci.yml 변경을 PR 로 merge → ② main 에서 `legal-markers` 초록 확인 → ③ protection 편집.
①은 PR #3 나 PR #2 에 끼우지 않는다 — 별도 PR (docs/CI only, 코드 0).

## 3. 대가

| 선택 | 얻는 것 | 잃는 것 |
|---|---|---|
| A. 이 제안대로 (독립 job + required) | 마커 실패가 결재 화면에 한 줄로 · `-k`/skip 우회가 protection 위반으로 드러남 · 1분급 | CI job 1개 추가(러너 분) · protection 편집 1회 · main 초록 선행 필요 |
| B. 현상 유지 | 변경 0 | 신호 혼재 · 우회 가능성 |
| C. `verify_public_notice.sh` 까지 CI 에 | 실서버 검증 자동화 | **프로덕션 읽기가 PR 마다 발생** — 지금 금지. 배포 후 절차로만 |

권고: **A**. C 는 하지 않는다.

## 4. 적용 전 확인 항목 (적용자)

- [x] DB 의존 실측 완료 — 통합 conftest PREFLIGHT 때문에 DB 필요 (§2-1). services 블록 포함으로 설계
- [ ] 두 파일이 PR #3(`d088e73`)·PR #2(`d9eeda4`) 어느 쪽 버전을 기준으로 하는지 — 둘 다 같은 파일을 만졌다 (PR #3 는 cherry-pick). merge 순서에 따라 한쪽 재확인
- [ ] required 승격 후 첫 PR 에서 체크 이름이 정확히 `legal-markers` 로 뜨는지

## 5. 하지 않는 것

- 이 문서는 ci.yml 을 바꾸지 않았다. branch protection 을 바꾸지 않았다.
- 마커 정의·격리 기록·법무 문안을 건드리지 않는다.
