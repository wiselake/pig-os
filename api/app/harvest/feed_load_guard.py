"""Initial-load 실행 가드 — 기본값은 언제나 **거부**다 (INITIAL LOAD APPROVAL GATE §5).

프로덕션 적재는 광범위한 우회 스위치(REMOVE_PROD_GUARD 같은 것)로 열지 않는다. 대신 실행이 자기 전제를
전부 **명시**하고, 하나라도 실제와 다르면 거부한다 — 승인받은 그 한 번만 통과하는 일회성 계약이다.

    --apply --expect-environment production
            --expect-code-sha <persistence fingerprint>
            --expect-migration <alembic revision>
            --expect-source-scope-hash <scope hash>
            --expect-source-rows <preflight 실측 N>

검사 실패는 전부 RefusedError. "모르면 통과" 경로가 없다.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

LOCAL_HOSTS = {"localhost", "127.0.0.1", "pigos-postgres", "::1"}
PROD_URL_MARKERS = ("rds.amazonaws.com", "52.78.65.6", "api.pigos.io", "supabase", "pigos-prod")

# 적재 동작을 결정하는 코드 — 이 집합의 내용이 바뀌면 지문이 바뀌고 승인은 무효가 된다.
FINGERPRINT_FILES = (
    "app/harvest/feed_load_guard.py",
    "app/harvest/feed_source_snapshot.py",
    "app/harvest/feed_source_sync.py",
    "app/harvest/feed_source_reconcile.py",
    "app/harvest/pigplan_feed_delivery.py",
    "app/repositories/feed_source_repo.py",
    "app/db/models/feed_source.py",
    "app/engine/feed/types.py",
    "app/engine/feed/normalize.py",
    "scripts/feed_source_initial_load.py",
)


class RefusedError(RuntimeError):
    """실행 거부. 메시지는 무엇이 기대와 달랐는지만 말한다(비밀값 없음).

    ★ 메시지는 ASCII 만 쓴다 — cp949 콘솔에서 거부 사유가 UnicodeEncodeError 로 가려지면
      운영자는 '왜 거부됐는지' 를 못 본다(2026-09-23 리허설 D 에서 실제로 발생).
    """


def api_root() -> Path:
    return Path(__file__).resolve().parents[2]


def code_fingerprint(root: Path | None = None) -> str:
    """적재 코드 지문 — 파일 경로+내용 해시의 해시. 승인 시점의 값을 --expect-code-sha 로 고정한다.

    프로덕션 체크아웃에는 .git 이 없어 커밋 SHA 를 믿을 수 없다(운영 실측). 내용 지문은 그 자리에서 계산된다.
    """
    root = root or api_root()
    h = hashlib.sha256()
    for rel in FINGERPRINT_FILES:
        p = root / rel
        if not p.exists():
            raise RefusedError(f"fingerprint source missing: {rel}")
        h.update(rel.encode())
        h.update(hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).digest())
    return h.hexdigest()


def detect_environment(database_url: str) -> str:
    """local | production | unknown. unknown 은 --apply 에서 거부된다."""
    host = (urlparse(database_url.replace("+asyncpg", "")).hostname or "").lower()
    env = (os.environ.get("ENVIRONMENT") or "").strip().lower()
    if host in LOCAL_HOSTS and env != "production":
        return "local"
    if env == "production" or any(mk in database_url for mk in PROD_URL_MARKERS):
        return "production"
    return "unknown"


@dataclass(frozen=True)
class Expectations:
    environment: str | None = None
    code_sha: str | None = None
    migration: str | None = None
    source_scope_hash: str | None = None
    source_rows: int | None = None


def check_write_allowed(mode: str, database_url: str, exp: Expectations) -> dict[str, str]:
    """쓰기 전에 부른다. mode: dry-run | target-local | apply. 통과하면 기록용 evidence 를 돌려준다."""
    env = detect_environment(database_url)
    host = (urlparse(database_url.replace("+asyncpg", "")).hostname or "?").lower()
    if mode == "dry-run":
        return {"mode": mode, "environment": env, "writes": "none"}
    if mode == "target-local":
        if env != "local" or host not in LOCAL_HOSTS:
            raise RefusedError(f"--target-local requires a local/ephemeral target (detected environment={env}, host={host})")
        return {"mode": mode, "environment": env, "writes": "local"}
    if mode != "apply":
        raise RefusedError(f"unknown mode {mode!r}")

    # ── --apply: 모든 기대를 명시해야 한다 ──
    missing = [n for n, v in (("--expect-environment", exp.environment), ("--expect-code-sha", exp.code_sha),
                              ("--expect-migration", exp.migration), ("--expect-source-scope-hash", exp.source_scope_hash),
                              ("--expect-source-rows", exp.source_rows)) if v in (None, "")]
    if missing:
        raise RefusedError(f"--apply requires explicit expectations, missing: {', '.join(missing)}")
    if env == "unknown":
        raise RefusedError("environment could not be determined (ENVIRONMENT env var / DATABASE_URL); refusing to apply")
    if exp.environment != env:
        raise RefusedError(f"environment mismatch: expected {exp.environment!r}, detected {env!r}")
    actual = code_fingerprint()
    if exp.code_sha != actual:
        raise RefusedError(f"code fingerprint mismatch: expected {exp.code_sha[:12]}..., actual {actual[:12]}... (this checkout is not the approved code)")
    return {"mode": mode, "environment": env, "code_fingerprint": actual, "writes": "target"}


def check_migration(exp_migration: str, db_revision: str | None, code_heads: list[str]) -> None:
    """대상 DB 가 승인된 revision 에 있고, 코드의 head 가 하나이며 같은 revision 인지."""
    if len(code_heads) != 1:
        raise RefusedError(f"alembic must have exactly one head, found {len(code_heads)}: {code_heads}")
    if code_heads[0] != exp_migration:
        raise RefusedError(f"code alembic head {code_heads[0]} != approved migration {exp_migration}")
    if db_revision != exp_migration:
        raise RefusedError(f"target DB is at {db_revision!r}, approved migration is {exp_migration}; apply the migration first")


def check_scope(exp_hash: str, actual_hash: str, exp_rows: int, actual_rows: int, *, unmapped_farms: int) -> None:
    """소스 범위·행수·매핑 밖 농장. 하나라도 어긋나면 그 실행은 승인된 실행이 아니다."""
    if exp_hash != actual_hash:
        raise RefusedError(f"source scope hash mismatch: expected {exp_hash[:12]}..., actual {actual_hash[:12]}...")
    if unmapped_farms:
        raise RefusedError(f"{unmapped_farms} source farm(s) have no PigOS mapping (out of the authorized scope)")
    if exp_rows != actual_rows:
        raise RefusedError(f"source row count changed since preflight: expected {exp_rows}, actual {actual_rows}; re-run the preflight for a new approval")
