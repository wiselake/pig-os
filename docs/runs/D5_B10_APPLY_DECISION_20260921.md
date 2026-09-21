# D5 — B-10 오프사이트 백업 프로덕션 적용 결정 패킷 (2026-09-21)

> 결정 요청서다. 코드 변경 0 · 프로덕션 접근 0 (이 문서 작성 중 AWS/EC2 조회 없음 — 값은 2026-09-18 B-10 실측을 인용하고 경과일만 계산).
> 원본 패킷·런북: `docs/runs/B10_OFFSITE_BACKUP_20260918.md` (branch `fix/b10-offsite-backup-20260918` @ `f0bdf8d`).

## 0. 한 화면

```
상태 (2026-09-21)
  BACKUP_EXISTS         YES    로컬 EC2 /dev/root, 매일 03:40 full (2026-09-18 실측 149.7MB)
  RESTORE_VERIFIED      YES    B-8 2026-09-16 격리 PG17 복원 · B-10 패치본 덤프도 복원 확인
  OFFSITE_PATCH_READY   YES    797394e · e708742 · 648a1dc — 오늘 재실행 ops/tests/test_backup.sh 25/25
  OFFSITE_CURRENT       NO     최신 오프사이트 객체 2026-08-25 14:47 (deploy 태그) → 오늘 기준 27일째 · 정기 잡 객체 0
  PITR                  NO

위험 (변하지 않은 사실)
  로컬 백업과 DB 가 같은 EC2 · 같은 /dev/root 장애 도메인. 인스턴스/볼륨 손실 = 백업 동반 손실.
  현 프로덕션 스크립트(0857e6f6)는 오프사이트 단계 자체가 없다(설계 결함 아닌 배포 결함 — 09-18 진단).

결정 3건 (분리)
  D5-1 production apply        UNDECIDED  ← 이 문서의 요청
  D5-2 S3 lifecycle            UNDECIDED  (업로드 재개를 막지 않는다 — 별건)
  D5-3 freshness scheduling    UNDECIDED  (크론 미등록, 수동 실행 가능)
```

## 1. D5-1 — 적용 결정 문장

> **`~/pigos/ops/backup_db.sh` 1개 파일을 패치본(sha256 `b2ef4c3638f8ff81…`)으로 교체한다. cron·.env·DB 는 건드리지 않는다.**

| 선택 | 얻는 것 | 대가 / 위험 |
|---|---|---|
| **(a) 적용** | 다음 03:40 full 부터 `pigos-db/` 에 오프사이트 사본 + 크기 대조 + sha256 sidecar. 실패가 조용히 exit 0 으로 끝나지 않음(exit 3/4/5, 로컬 보존) | 파일 1개 교체(롤백 = `.pre-b10-<ts>` 복사본 되돌리기). DB 영향 0(pg_dump 읽기 전용). 새 실패 모드: S3 오류 시 크론 로그가 빨갈 수 있음 — 그것이 목적 |
| (b) 보류 | 변경 0 | 27일째 stale 이 계속 늘어남. EC2 손실 시 8-25 이후 데이터 복구 불가 |
| (c) 코드만 merge 하고 배포 안 함 | 저장소 정합 | 09-10 법무 정정과 같은 함정 — "파일만 고치고 프로덕션은 그대로" |

권고: **(a)**. 09-18 패킷 §8·§9 그대로. 적용 담당은 SSH 권한자(Brian), 실행 순서는 §9 ①~⑪ — 이 세션은 승인 전 실행하지 않는다.

## 2. 적용 전 확인 (§9 ①) — 바뀌었을 수 있는 것

| 항목 | 09-18 값 | 적용 시 재확인 |
|---|---|---|
| 프로덕션 스크립트 sha256 | `0857e6f67c477861…` | 다르면 STOP (사이에 누가 바꿨다) |
| cron | 03:15 schema · 03:40 full · 15:05 incremental | 변경 없음이어야 |
| `.env` `BACKUP_S3_BUCKET`/`PREFIX` | 존재 | 그대로 |
| IAM 역할 `pigos-ec2-backup-role` | PutObject 가능 · GetBucketLifecycle/Versioning 불가 | 업로드에는 충분 |
| 최신 오프사이트 객체 | 2026-08-25 14:47 | 적용 후 D+1 03:41 에 새 객체 |

## 3. D5-2 · D5-3 (적용과 분리)

- **S3 lifecycle**: 09-18 §7 저장량 표(7일 1.0GB · 30일 4.5GB · 90일 13.5GB · 365일 54.7GB, full 149.7MB/일 기준). 비용은 결정 시점 가격표로. 역할에 Lifecycle 읽기 권한이 없어 현 설정 미확인. **업로드 재개를 기다리게 하지 않는다.**
- **freshness 스케줄**: `ops/check_backup_freshness.sh` (CURRENT/STALE/MISSING, 36h) 는 배치만 하고 크론에 넣지 않았다. 적용 후 수동 1회(§9 ⑪)로 먼저 보고, 알림 경로(어디로 보낼지) 결정 후 스케줄.

## 4. 저장소 측 정리 (적용과 무관하게 필요한 것)

```
branch     fix/b10-offsite-backup-20260918 @ f0bdf8d  — base 8a80ea4 (main 이전 판). PR 없음. PR #2(safety)에 포함 안 됨
base drift main 은 ae61369 (#4). B-10 은 public_privacy.* 를 안 만지므로 rebase 충돌 없음(diff 로 확인 — 브랜치 diff 에 보이는 public_privacy 4줄은 #4 부재일 뿐)
순서       PR #3 merge → main 에 새 ci.yml → B-10 을 main 위로 rebase → PR → CI (09-18 §11 그대로)
★ 배포는 scp 로 파일 1개 — git merge 와 독립. 저장소 정리를 기다려 적용을 늦추지 않는다 (선택 (c) 함정)
```

## 5. 이 문서가 하지 않은 것

- 프로덕션·S3·EC2 조회 0. 27일은 09-18 실측(08-25) + 달력 계산.
- 스크립트·cron·lifecycle 변경 0. 적용은 승인 후 §9 순서로, 실행자는 SSH 권한자.
