# main 브랜치 보호 — 적용 기록 (2026-09-16)

> **왜 지금인가**: 2026-09-10, push 금지 기간 중 `8a80ea4` 가 `main` 에 직접 push 됐다.
> 그 결과 origin/main 이 로컬 작업과 갈라졌고, PR 이 열렸을 때 GitHub 이 merge ref 를
> 만들지 못해 **CI 가 큐잉조차 되지 않았다** — 실패가 아니라 침묵이었다. 사람이 규율을
> 지키는 것에 기대는 대신 저장소가 거부하게 만든다.

---

## 적용 전 상태 — 보호 없음

```
GET /repos/wiselake/pig-os/branches/main/protection
→ 404 {"message": "Branch not protected"}
```

2026-09-16 11:5x KST 측정. **한 번도 보호된 적이 없다.**

---

## 적용값

```json
{
  "required_status_checks": {
    "strict": true,
    "checks": [
      {"context": "backend (3.12)"},
      {"context": "backend (3.14)"},
      {"context": "frontend"}
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
```

### 적용 후 GET 검증 (실측)

```
checks           ["backend (3.12)", "backend (3.14)", "frontend"]
strict           true      ← base 가 앞서 있으면 재실행을 요구한다
enforce_admins   true      ← admin 도 예외 없음. 이번 사고가 admin push 였다
reviews          0
dismiss_stale    true
force_push       false
deletions        false
```

---

## 결정 두 가지와 근거

### 1. status check context 는 조회한 값이다 — 추측하지 않았다

```
GET /repos/wiselake/pig-os/commits/3c97fe2/check-runs
→ "frontend" · "backend (3.12)" · "backend (3.14)"   (전부 github-actions, success)
```

문자열을 손으로 적었으면 오타 하나로 **required check 가 영영 pending** 이 되어
모든 PR 이 막힌다. 마지막 GREEN 런의 실제 context 이름을 그대로 썼다.

### 2. `required_approving_review_count = 0` — 의도적

collaborator 는 5명 전원 admin 이다 (`changeun77`, `foes88`, `kilhyeon-kim`,
`wiselakeManager`, `wiselake-admin`). 즉 형식상 리뷰어는 있다.

그럼에도 0 으로 둔 이유:

```
GitHub 은 PR 작성자의 self-approve 를 허용하지 않는다.
PR #2 의 작성자는 foes88(Brian) 이고, 아침의 예정된 행동은 Brian 의 merge 판단이다.
지금 1 로 걸면 그 판단을 실행할 수 없다 — 다른 admin 이 깨어 있어야 한다.
enforce_admins=true 라 admin 이라고 우회되지도 않는다.
```

**보호의 목적은 "실수로 main 에 쓰는 것"을 막는 것이지 merge 를 봉인하는 것이 아니다.**
PR 필수 + CI 필수 + admin 예외 없음만으로 이번 사고 경로는 완전히 닫힌다. 리뷰 1명은
실제로 리뷰할 사람이 정해진 뒤 한 줄로 올리면 된다:

```bash
gh api -X PATCH repos/wiselake/pig-os/branches/main/protection/required_pull_request_reviews \
  -f required_approving_review_count=1
```

→ **사람 결정 항목**으로 남긴다.

---

## 이번 사고 경로가 실제로 닫혔는가

| 이번에 일어난 일 | 지금 | 근거 |
|---|---|---|
| admin 이 main 에 직접 push | 거부 | PR 필수 + `enforce_admins=true` |
| CI 없이 main 이 전진 | 거부 | 3개 required check |
| base 가 앞선 채 merge | 거부 | `strict=true` (재실행 요구) |
| main force push / 삭제 | 거부 | `allow_force_pushes=false` · `allow_deletions=false` |
| 갈라진 뒤 CI 침묵 | 여전히 가능 | ★ 아래 |

★ **남는 구멍 하나**: merge ref 를 못 만들면 `pull_request` 워크플로가 조용히 안 도는
GitHub 동작 자체는 보호로 막히지 않는다. 다만 이제 갈라짐이 main 에서 시작될 수 없으므로
발생 확률이 크게 줄고, 발생해도 PR 화면에 conflict 로 보인다. "checks 0건" 을 GREEN 으로
읽지 않는 것은 사람 쪽 규율로 남는다.

---

## 검증 방법에 대한 정직한 한 줄

`git push --dry-run` 으로는 확인하지 않았다 — dry-run 은 서버의 pre-receive 거부까지
재현하지 않아 통과한 것처럼 보인다. 실제 push 로 시험하는 것은 이 세션의 금지 사항이라
**보호 API 의 GET 응답을 증거로 삼는다**(위 실측 블록).

적용 시점 확인:

```
origin/main HEAD   8a80ea4   (변경 없음)
PR #2              draft · OPEN · 미merge
```

---

## 관련

```
docs/DEV_ECOSYSTEM_AUDIT_20260911.md   CI 가 한 번도 안 돌던 사실
docs/legal/HUMAN_INPUT_QUEUE.md        B-9 (갈라짐의 원인과 해소)
.github/workflows/ci.yml               required check 3개의 출처
```
