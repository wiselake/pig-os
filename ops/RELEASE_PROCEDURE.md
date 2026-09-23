# 릴리스 절차 — SHA 로 말할 수 있는 서버 (결정 D-A·D-B, 2026-09-23)

> 상태: **도구·게이트 설치 완료, 이 절차로의 첫 배포는 아직 없음(사람 GO 필요).**
> 지금 서버 `~/pigos` 에는 `RELEASE_MANIFEST.json` 이 없으므로 새 게이트는 모든 배포를 거부한다 — 의도된 상태다.
> 근거: `docs/feed/runs/goal_20260923/evidence/w2_server_preflight_v2.txt`

## 구성

```text
~/pigos-gate/            게이트 (앱 트리 밖) — deploy.sh · check_migration_drift.sh · alembic_graph.py · additive_revisions.txt ·
                         release_manifest.py · GATE_SOURCE.json(설치된 게이트의 커밋 sha + 파일별 sha256)
~/pigos/                 앱 트리 — 릴리스 tarball 을 푼 것 + RELEASE_MANIFEST.json(커밋 sha · 파일별 sha256 · 실행 파일 · alembic head)
                         .env 와 백업 디렉터리들은 대조 범위 밖
```

게이트를 앱 트리 밖에 두는 이유: 롤백 때 앱 트리는 DB 보다 옛것이다. 옛 트리 안의 게이트·허용 목록은 새 리비전을 모른다.

## 1. 워크스테이션 — 산출물 만들기

```bash
python ops/release_manifest.py build      --ref <40자리 sha> --out <dir>    # pigos-release-<sha12>.tar.gz (+ .sha256)
python ops/release_manifest.py gate-build --ref <sha>        --out <dir>    # 게이트를 바꿀 때만: pigos-gate-<sha12>.tar.gz
```

## 2. 서버 — 게이트 설치(바꿀 때만)

```bash
umask 077
mv ~/pigos-gate ~/pigos-gate.prev-<옛sha12>          # 지우지 않는다
mkdir -m 700 ~/pigos-gate && tar -xzf pigos-gate-<sha12>.tar.gz -C ~/pigos-gate
python3 ~/pigos-gate/release_manifest.py verify-gate --dir ~/pigos-gate
```

## 3. 서버 — 앱 트리 교체 + preflight + 배포

```bash
sha256sum -c pigos-release-<sha12>.tar.gz.sha256
# (교체 방식은 결정 대기 DQ-3: 제자리 풀기 vs 버전 디렉터리 + 전환)
~/pigos-gate/deploy.sh <api|web|worker|all> --expect-sha <40자리 sha> --preflight-only    # 먼저 게이트만
~/pigos-gate/deploy.sh <api|web|worker|all> --expect-sha <40자리 sha>                     # 배포
```

게이트 순서: G(게이트 자기 검증) → A(앱 트리 == 커밋, 파일 단위 + 실행 비트) → 0(DB 리비전 ↔ 코드 head, additive 허용 목록) → 백업·빌드·기동.
우회 스위치는 없다. `~/pigos/ops/deploy.sh`(앱 트리 안의 사본)로 실행하면 거부한다(APP_TREE).

## ★ 알려진 위험 — 결정 대기

- **DQ-4 롤백이 백업 스크립트를 되돌린다.** 릴리스는 `ops/` 를 포함하고 cron 은 `~/pigos/ops/backup_db.sh` 를 부른다. 옛 릴리스로 롤백하면
  백업 스크립트도 옛 판이 된다 — 2026-08-25 사고와 같은 경로다. manifest 는 이것을 잡지 못한다(옛 릴리스 기준으로는 정상 파일).
  (`docs/feed/runs/goal_20260923/DECISION_QUEUE.md`)
- manifest 는 서명되지 않는다. 우발적 드리프트를 잡는 장치이지, 서버 쓰기 권한을 가진 사람의 위조를 막는 장치가 아니다.
