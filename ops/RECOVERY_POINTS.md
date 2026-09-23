# 복구점 ledger (PigOS 프로덕션 DB)

> 일반 백업(`backup_db.sh` cron, 7일 보존)과 별개로 **의도해서 남기는** 복구점만 적는다.
> 한 줄 = 한 복구점. 지우거나 옮기면 그 사실도 여기에 적는다. 복원 절차는 `ROLLBACK.md` §E.
>
> ★ 로컬 `~/pigos-backups/` 사본은 `backup_db.sh` 보존 정리(`-deploy.sql.gz` 외 `-mtime +7`)로 지워진다 —
> 오래 남길 복구점은 S3 `pigos-db-backup/pigos-db/recovery-points/` 에 둔다(일반 백업 경로 `pigos-db/` 와 분리).
> 버킷 수명주기 규칙은 서버 역할(`pigos-ec2-backup-role`)로 조회할 수 없다 — **확인 전까지 S3 영구 보존을 가정하지 않는다.**

## 복구점

| # | 이름 | DB 상태 | 위치 | 크기 · sha256 | 증명 |
|---|---|---|---|---|---|
| RP-1 | pre-feed-load | alembic `f3c6a8d0b2e4` · 사료 테이블 없음 · 2026-09-23 09:18:59 KST (feed initial load 직전) | S3 `pigos-db/recovery-points/pigos-full-20260923-091859-pre-feed-load.sql.gz` (SSE AES256, 메타 `recovery-point=pre-feed-load`) · 로컬 원본 `pigos-full-20260923-091859-feedload-initial-load.sql.gz` 는 **2026-10-02 03:15 KST 보존 정리에서 삭제 예정** | 149,733,226 bytes · `27b5fde1a1c763d05cdb7f54658bc223853cc881d9cdc0c00484b6fcb2b41297` — S3 왕복 다운로드 sha256 일치 (2026-09-23 05:53 UTC) | 복원 리허설 #1 `docs/feed/runs/restore_test_20260923/` |
| RP-2 | post-feed-load | alembic `a7c9e1f3b5d7` · feed_source_rows 5,461 · 2026-09-23 11:08:31 KST | S3 `pigos-db/pigos-full-20260923-110831-postload.sql.gz` (일반 백업 경로 — backup_db.sh 업로드) · 로컬 같은 이름(7일 보존) | 150,207,912 bytes · 앞 16자 `0e71d7058d3e122b` | 복원 리허설 #2 `docs/feed/runs/restore_test_postload_20260923/` |

## 할 일

- RP-2 를 `recovery-points/` 로도 복사할지 — 일반 경로의 S3 수명주기가 확인되면 결정.
- 버킷 수명주기·버전관리 확인(콘솔 권한 필요, 사람 작업) → 결과를 이 문서 머리에.

## 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-09-23 | 신설. RP-1 S3 보존(결정 D-C GO) · RP-2 등재 |
