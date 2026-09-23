#!/usr/bin/env bash
# DB 리비전 ↔ 배포할 코드의 alembic head 대조 — 불일치면 배포 거부 (exit 3).
#
# 왜: 2026-09-23 feed initial load 로 프로덕션 DB 가 a7c9e1f3b5d7 이 됐는데 main 에는 그 파일이 없었다.
#     그 상태로 main 을 배포하면 코드가 모르는 리비전 위에서 앱이 돌고, 누군가 alembic 을 돌리는 순간 죽는다.
#     "메모로 남겼다" 는 다음 세션이 못 보면 끝이다 — 배포 경로에서 기계적으로 막는다.
#
# 사용:  ops/check_migration_drift.sh <db_revision> [versions_dir]
#   db_revision   대상 DB 의 alembic_version (deploy.sh 가 실행 중인 api 컨테이너에서 읽어 넘긴다)
#   versions_dir  기본 $ROOT/api/alembic/versions (배포될 코드)
# 거부 조건: 코드 head 가 1개가 아님 · DB 리비전이 코드에 없음(DB 가 코드보다 앞섬) · DB 리비전 ≠ 코드 head(미적용 migration)
# 우회 스위치 없음. 미적용 migration 은 승인 경로(일회용 러너 + 기대값 가드)로 먼저 적용한다.
set -euo pipefail
DBREV="${1:?usage: $0 <db_revision> [versions_dir]}"
ROOT="${PIGOS_ROOT:-$HOME/pigos}"
DIR="${2:-$ROOT/api/alembic/versions}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "$DBREV" ] || [ "$DBREV" = "None" ]; then
  echo "REFUSED: DB revision could not be read"; exit 3
fi
python3 "$HERE/alembic_graph.py" --dir "$DIR" --check-db-revision "$DBREV"
