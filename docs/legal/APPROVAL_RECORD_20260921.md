# 승인 기록 — 2026-09-21 (결재 3·4·6·7 → PR #3 merge·배포 결정)

> **성격**: 무엇이 **누구에 의해 어떤 근거로** 정해졌는지 그대로 적는다. 위조 0.
> **★ 서명 결재문이 아니다.** 실무 채팅에서 내려진 실행 결정을 서명 결재로 위장하지 않는다.
> 대상: `docs/releases/RELEASE_PACKET_20260918.md` §1-8 C 서명 요청 4건 · §3-1 ①~⑪
> 선행: `APPROVAL_RECORD_20260910.md` — 대표(Grant) 구두 포괄 승인 + 실행 위임, 선택은 Brian(CTO)

## 0. Provenance

```
Grant (대표)      2026-09-10 구두 포괄 승인 · 실행 위임 (APPROVAL_RECORD_20260910 §0)         — 변동 없음
Brian (CTO)       2026-09-21 13:5x KST  위임 범위 내 실행 결정:
                  "PR #3 merge 후 배포" 선택 (main 직접 배포 / web·api·worker 전체 두 대안을 보고 고름)
                  → 결재 3·4·6·7 문안(PR #3 4d008a7 서빙본)을 그대로 게시하는 결정
개발 세션         기록자. 결정자가 아니다
Counsel           법률 판단 항목은 여전히 미확정 (D-13 등) — 이 결정으로 바뀌지 않음
```

## 1. 결재 4건 — 7필드

| 필드 | 결재 3 | 결재 4 | 결재 6 | 결재 7 |
|---|---|---|---|---|
| scope | 방침 제11조 :191·:194 (취약점 점검·재식별 방지 로드맵) 삭제 | V-11 농장 GPS (a) 미수집 유지 — 확정조건 5개 9/16 충족 | 제7조 [COUNSEL] → "법률 검토 중" 공개 조항 전환 (a) | 제9조 보유기간 표 — 미확정 기간 미생성, 표 머리 "정책 수립 후 개정·고지", 각 행 실측 동작만 (RELEASE_PACKET §1-8 A 원문) |
| decision | APPROVED | APPROVED | APPROVED | APPROVED |
| decided_by | Brian (CTO) — 대표 위임 범위 | 同 | 同 | 同 (★ 신규 항목 — 9/10 위임의 자동 확장이 아니라 오늘 명시 선택) |
| decided_at | 2026-09-21 13:5x KST | 同 | 同 | 同 |
| evidence | VERBAL (실무 채팅 선택지 응답) | 同 | 同 | 同 |
| recorded_by | 개발 세션 (Claude) | 同 | 同 | 同 |
| written_confirmation | NOT_RECEIVED | NOT_RECEIVED | NOT_RECEIVED | NOT_RECEIVED |

★ `written_confirmation = NOT_RECEIVED` 는 "서명문이 없다" 는 사실이지 승인의 부재가 아니다. 결정·결정자·시각·증거 형태가 전부 채워졌으므로 §1-8 C 기준 "결정됨". 서명 결재문으로 승격하려면 대표 서명 후 이 표의 `evidence`·`written_confirmation` 만 갱신한다.

## 2. 이 결정이 배포하는 것 / 하지 않는 것

```
배포 head        PR #3 4d008a7 = d088e73 (마커 제거·V-11·가드) + main ae61369 (#4 Anthropic 수탁자 행)  → main merge commit
                 ★ #4 가 포함되므로 App Store 리젝 02a50de4 의 "방침에서 서드파티 AI 식별" 요건도 같은 배포로 충족
함께 올라가는 것  8a80ea4 (가입 게이트를 계정 생성 경로에도 적용 — main 에 있었으나 프로덕션 미배포)
배포 대상        api 컨테이너만 (web·worker 는 이번 범위 아님)
manifest         변경 없음 — 8 문서 DRAFT_LAWYER_PENDING 그대로. 마커를 지우는 배포이지 게시 상태를 올리는 배포가 아니다
DB               마이그레이션 0
롤백             2e372b1 (ops/deploy.sh 가 찍는 rollback-<ts> 태그 + 배포 전 DB 스냅샷)
```

## 3. 실행 기록 (§3-1 ①~⑪ — 실행하면서 채운다)

| 단계 | 시각(KST) | 결과 |
|---|---|---|
| ① 결재 확보 | 13:5x | 위 표 |
| ② 원장 기록 | — | 이 문서 |
| ③ PR #3 Ready | 13:59 | `gh pr ready 3` — draft=false |
| ④ head·base·checks 재확인 | 13:59 | head 4d008a7 · base ae61369 불변 · backend(3.12)/backend(3.14)/frontend SUCCESS · MERGEABLE/CLEAN |
| ⑤ merge | 14:00 (05:00:56Z) | **main 6675b3f** (merge commit). PR #3 MERGED |
| ⑥ PROD SHA 실측 (기대 2e372b1) | 14:03 | **actual_prod_before = 2e372b1 ✓** — public_privacy.en 637a7d50 · .ko badf088d · public_notice.py c4b960a7: 디스크 == 컨테이너 == `git show 2e372b1`. api 이미지 2026-08-31T00:52Z. alembic 컨테이너 f3c6a8d0b2e4 = repo head → db_migration_count 0 |
| ⑦ 롤백 지점 | 14:03 | rollback_commit 2e372b1 · rollback_ref = `ops/deploy.sh` 가 배포 시 찍는 `pigos-api:rollback-<ts>` (현재 api 롤백 태그 없음, web/worker 만 존재) + 배포 전 DB 스냅샷(deploy.sh 1/5) |
| ⑧ api 배포 | — | **이 세션에서 차단됨** — auto mode 분류기 "Remote Shell Writes / Production Deploy" 거부. 산출물 준비: `git archive 6675b3f api` → `C:	mp\pigos-api-6675b3f.tgz` (721,929 B; `.env` 미포함, `.env.example` 만). 실행은 Brian (아래 §4 명령) |
| ⑨ verify_public_notice.sh | | |
| ⑩ 마커 0 · Anthropic 존재 (5항목) | | |
| ⑪ KNOWN_PUBLICATION_EXPOSURE → REMEDIATED | | |

## 4. ⑧ 배포 — Brian 이 실행할 명령 (이 세션 차단분)

```bash
# 로컬 PC (이미 만들어 둔 아카이브: C:	mp\pigos-api-6675b3f.tgz — main 6675b3f 의 api/ 만, .env 없음)
scp -i C:\dev_env\keyfile\wiselake-app-key.pem C:	mp\pigos-api-6675b3f.tgz ubuntu@52.78.65.6:/tmp/

# 서버
ssh -i C:\dev_env\keyfile\wiselake-app-key.pem ubuntu@52.78.65.6
cd ~/pigos
cp -a api api.bak-predeploy-$(date +%Y%m%d-%H%M%S)          # 되돌릴 사본
tar xzf /tmp/pigos-api-6675b3f.tgz && rm /tmp/pigos-api-6675b3f.tgz
ls api/.env && grep -c Anthropic api/content/legal/public_privacy.en.md   # .env 그대로 · 1 이어야 함
sha256sum api/content/legal/public_privacy.en.md | cut -c1-16              # 8de3d36cb54ae62c 이어야 함
./ops/deploy.sh api                                                        # 1/5 DB 스냅샷 → 2/5 rollback 태그 → build → up → health
```

deploy.sh 가 `✅ 배포 완료. 롤백 태그: rollback-<ts>` 를 찍으면 이 세션이 ⑨⑩⑪ (읽기 검증 + 문서) 을 이어서 한다.

