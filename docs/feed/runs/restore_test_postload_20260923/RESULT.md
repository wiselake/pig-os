# 복원 리허설 #2 — 적재 **후** 덤프, 데이터가 든 상태의 downgrade — 2026-09-23

> GO: 대표 2026-09-23 ("적재 후 덤프 복원 테스트 — GO"). 절차는 #1(`../restore_test_20260923/`)과 같다.
> 원문 로그 `run.log`, 스크립트 `restore_test_postload.sh`(실행한 그대로). 이 문서는 해석만 한다.

## 입력 — 적재 후 recovery point 가 없었다

리뷰 질문 "cron 백업이 적재 후 덤프를 이미 만들었습니까?" → **아니오.** 일일 full 은 03:40 KST 이고 적재는 09:18~09:24 KST 라
09-23 03:40 덤프는 적재 전이다. 다음 cron full 은 09-24 03:40.
→ backup 스크립트 동기화(GO) 직후의 수동 확인 실행이 곧 적재 후 recovery point 가 됐다:
`pigos-full-20260923-110831-postload.sql.gz` 150,207,912 bytes (적재 전 덤프 대비 +474,686) · sha256 앞 16자 `0e71d7058d3e122b`
· `COPY public.feed_source_rows` 5,461행 · S3 사본 같은 크기 (`../prod_20260923/backup_sync_manual_run.txt`).

## 결과

| 단계 | 판정 |
|---|---|
| 격리 | network none · 포트 0 · api env 없음 · CPU 1 · 메모리 2G · 끝에 container 0 / volume 0 |
| 복원 | rc 0 · 42초 |
| 복원 직후 alembic = a7c9e1f3b5d7 | PASS |
| feed_source_rows = 5,461 · sync_runs = SUCCEEDED(+5461), SUCCEEDED(+0) | PASS (프로덕션 기록과 동일) |
| **데이터가 든 상태의 downgrade → f3c6a8d0b2e4** | **PASS** · 피드 테이블 0개 남음 |
| downgrade 후 스키마 | sha256 `1881aa73d2200f66` = #1 의 적재 전 스키마와 **동일** |
| downgrade 후 행 수 | 비피드 92 테이블 합계 2,495,564 — 복원 직후와 전부 동일, #1 의 적재 전 합계와도 동일 |
| 다시 upgrade → a7c9e1f3b5d7 | PASS · 스키마 sha256 `e09d6d821e3dee07` = #1 의 fresh upgrade 와 동일 |
| 다시 upgrade 후 피드 테이블 | feed_source_rows **0** · feed_source_sync_runs **0** — **이것이 롤백 비용**: downgrade 는 5,461행을 버린다 |
| 비피드 스키마 지문 | 세 시점 모두 `417247fc…` |

## ★ `CHECK schema restored == re-upgraded : FAIL (10 lines)` — 복원이 CHECK 제약 표기를 바꾼다 (결함 아님, 의미 동일)

차이 10줄은 전부 두 피드 테이블의 CHECK 제약 5개(`ck_fsr_basis` · `ck_fsr_cost_status` · `ck_fsr_quantity_status` · `ck_fsr_source_status` · `ck_fssr_status`)의 **표기**다.
허용 값 집합은 같다.

```text
프로덕션(마이그레이션으로 생성, 덤프에 기록된 형태)   ANY ((ARRAY['AS_RECORDED'::character varying, …])::text[])
덤프를 복원한 뒤(그 텍스트를 PG 가 다시 파싱한 형태)   ANY (ARRAY[('AS_RECORDED'::character varying)::text, …])
```

근거: 덤프 파일 자체가 앞의 형태를 담고 있다(grep 확인) → 프로덕션 = fresh upgrade 형태. 복원이 표기를 바꾼다.
같은 현상이 다른 테이블에 이미 있다 — 적재 전 덤프의 비피드 CHECK 는 17개 모두 뒤의 형태다(2026-08-25 Supabase → 로컬 PG 이전이 덤프/복원이었기 때문).

**운영상 의미:** 복원한 DB 의 스키마 해시는 원본과 **같지 않다**. 복원 뒤 검증은 해시가 아니라 비피드 지문
(information_schema 컬럼 기준, `417247fc…`) · 테이블별 행 수 · alembic_version 으로 한다. `ops/ROLLBACK.md` §E-3 에 반영.

## 닫힌 것 / 남은 것

- 닫힘: "데이터가 든 상태의 downgrade 미실측"(#1 한계) · "적재 후 recovery point 없음".
- 남음: 다른 호스트로의 복원(재해 복구) — 범위 밖. S3 사본에서 내려받아 복원하는 경로는 검증하지 않았다.
- ★ 보존 정책: 이 덤프와 적재 전 덤프(09:18:59) 모두 `backup_db.sh` 의 7일 보존 대상이다(`-deploy` 접미사만 제외).
  적재 전 덤프는 **S3 사본이 없고** 2026-10-02 03:15 KST cron(schema 백업도 같은 보존 정리를 돈다 · `find -mtime +7` = 만 8일 이상)에서 삭제된다 → 결정 대기 목록 D-C.
