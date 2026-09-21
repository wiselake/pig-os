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
| ③ PR #3 Ready | | |
| ④ head·base·checks 재확인 | | |
| ⑤ merge | | |
| ⑥ PROD SHA 실측 (기대 2e372b1) | | |
| ⑦ 롤백 지점 | | |
| ⑧ api 배포 | | |
| ⑨ verify_public_notice.sh | | |
| ⑩ 마커 0 · Anthropic 존재 (5항목) | | |
| ⑪ KNOWN_PUBLICATION_EXPOSURE → REMEDIATED | | |
