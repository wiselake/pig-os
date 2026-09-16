# 릴리스 판단 패킷 — 2026-09-16 밤샘 작업

> **이 문서의 목적**: 아침에 사람이 **merge 할지, 배포할지만** 판단할 수 있게 하는 것.
> merge·배포·가입 재개는 하지 않았다. 아래 숫자는 전부 실측이며 추정값은 없다.

---

## 0. 한눈에

```
MAIN-MERGE-READY    YES     PR #2 base=main · mergeable · CI GREEN
PROD-DEPLOY-READY   NO      ★ 아래 §7 — 배포는 가입 재개가 아니고, 남은 사람 결정이 있다
MAIN CHANGED        NO      origin/main = 8a80ea4 (밤새 그대로)
PROD CHANGED        NO      애플리케이션 쓰기 0 · DB 쓰기 0 · 배포 0
```

---

## 1. Merge readiness

```
branch      safety/pigos-20260916
HEAD        55b8534
origin/main 8a80ea4
ahead/behind  152 ahead / 0 behind      (merge-base 이후 우리 쪽만 전진)
PR #2       base=main · draft · mergeable=true · 152 commits
            mergeable_state=blocked  ← ★ 브랜치 보호가 걸렸다는 뜻이다. 아래 §6 참조
CI          run 35076804473 (55b8534)
```

★ **`blocked` 은 문제가 아니다.** 어젯밤까지 `clean` 이었던 것이 오늘 `blocked` 인 이유는
main 브랜치 보호를 걸었기 때문이고, draft PR 은 정의상 merge 대상이 아니다. Ready 로
전환하고 required check 3개가 초록이면 merge 가능해진다.

---

## 2. DB — ★ 마이그레이션 없음

```
새 alembic 리비전      0건        (밤새 스키마를 건드리지 않았다)
head                  f3c6a8d0b2e4   — 프로덕션 백업의 alembic_version 과 **동일**
프로덕션 DDL 필요      없음
롤백 시 DB 고려사항    없음 (스키마 변경이 없으므로 앞뒤 호환)
```

★ 이것이 이번 배포의 성격을 정한다: **코드만 바뀐다.** DB 순서·다운타임 문제가 없다.

---

## 3. 런타임에서 달라지는 것

| 기능 | 변화 | 사용자 체감 |
|---|---|---|
| 가입 속도 제한 | `/auth/register`·`/onboarding/complete` 5회/시간, 로그인·비밀번호재설정 20회/분 → 초과 시 **429** | 정상 농가는 닿지 않는다. ★ 세 클라이언트가 429 문구를 모른다(§7) |
| 배경 잡 | 푸시 전건 실패가 더 이상 "성공"으로 끝나지 않는다 | 없음 (로그·잡 결과만) |
| 운영 상태 | `/health/ready` · `/health/ops` 신설. `/health` 는 **불변** | 없음 (내부) |
| 공개 방침 | ★ 내부 마커 **48건**(언어별 24) 사라짐 — 9/10 정정분 46 + 오늘 V-11 2. 9/10 정정은 배포된 적이 없다 | ★ 있음 — 공개 문서가 실질적으로 바뀐다 |
| 가입 게이트 | 변화 없음 — B-9 병합은 canonical 유지, 중복 제거뿐 | 없음 |

★ **공개 방침 변경이 이번 배포에서 유일하게 외부에 보이는 변화다.** 그리고 그것이
격리 종료의 전제다(§5).

---

## 4. 배포 순서 (권고)

DB 변경이 없으므로 단순하다.

```
1  api      (게이트·속도제한·잡·ops 엔드포인트·공개 방침 렌더 — 전부 여기)
2  worker   (api 와 같은 이미지. 잡 결과 의미론이 바뀌었다)
3  web      (변경 없음 — 그래도 같은 커밋으로 맞춰두는 편이 롤백이 쉽다)
4  mobile   ★ 배포하지 않는다. 이번 변경에 모바일 코드는 없다
```

배포 직후 `/health/ops` 를 먼저 본다 — 이번에 만든 것이 바로 이 순간을 위한 것이다.

---

## 5. 배포 후 확인 (최소)

```
1  curl -s https://api.pigos.io/health                → {"status":"ok"}
2  curl -s https://api.pigos.io/health/ops            → checks 3개. kpi_snapshots 는 degraded 가 정상이다(0행, 기존 상태)
3  ★ curl -s "https://api.pigos.io/legal/privacy?lang=ko" | grep -c "\[V —"   → **0**
   같은 것을 lang=en 으로 한 번 더. 이 둘이 0 이어야 격리를 닫을 수 있다 (§5-1)
4  가입 차단 확인   KR 로 register → 451 KR_REFERENCE_ONLY
5  가입 허용 확인   US 로 register → ★ 지금은 451 PUBLICATION_NOT_APPROVED 가 정답이다
                   (G-3 미배포 상태라면 201). 어느 쪽인지 배포 범위에 따라 먼저 정하고 본다
6  속도 제한        같은 IP 로 register 6회 → 6번째 429 + Retry-After
7  배경 잡          다음 06:00 UTC 후 잡 로그에 "OK|PARTIAL|TOTAL FAILURE" 중 하나가 찍히는지
```

### 5-1. ★ 격리 종료는 3번 뒤에만 가능하다

```
지금   SOURCE 마커 0  ·  ★ PRODUCTION 마커 48 (언어별 24)
배포 후 3번이 0 이면  → KNOWN_PUBLICATION_EXPOSURE 삭제 + status 종결
       확인 전에는  → 격리 유지. 소스가 깨끗하다는 것은 종료 사유가 아니다
```

★★ **48 이다. 2가 아니다.** 2026-09-16 밤에 공개 URL 을 처음 직접 세어보고 알았다 —
9/10 의 24→1 정정(`ec99391`)이 **배포된 적이 없다.** 프로덕션은 `6f16e41`(2026-08-27)
내용을 서빙 중이다. 그래서 이번 배포의 공개 효과는 "마커 2건 제거" 가 아니라
**"48건 제거"** 이고, 격리 만료가 하루 남은 지금 이것이 배포 판단의 가장 큰 근거다.

**만료 2026-09-17 23:59:59 KST 가 내일이다.** 배포하면 닫을 수 있고, 안 하면 만료된다 —
그때는 연장이 아니라 "게시 문서 없이 열어둘 것인가"를 결정해야 한다(LEGAL_P0_FREEZE §6).

---

## 6. 롤백

```
되돌릴 지점    8a80ea4 (현재 origin/main)
DB             고려사항 없음 — 스키마 변경 0
worker         앞뒤 호환. 잡 결과 문자열 형식만 달라진다
frontend       변경 없음
공개 방침      되돌리면 내부 마커 48건이 다시 노출된다 ★ 격리도 함께 되돌려야 한다
```

★ 롤백에서 유일하게 주의할 것은 **방침 문서다.** 코드 롤백이 곧 법무 상태 롤백이 된다.

---

## 7. 사람이 결정해야 하는 것

```
1  PR #2 merge 여부                       ★ 아침의 한 단계
2  배포 여부 — 그리고 G-3 를 포함할지      (포함하면 신규 가입이 전면 중단된다. 9/09 (나) 결정)
3  B-10  S3 오프사이트 백업 재개           22일 끊김. 운영 스크립트 변경이라 하지 않았다
4  B-5   iOS Debug 빌드 호스트             (가) 되돌림 권고
5  H13   "미국만" vs "OTHER 만" 한 문장     xfail 10건이 대기
6  H17   공개 사이트 방침·약관 교체         CURRENT_PUBLICATION_SET 없이는 불가
7  변호사 수신처                            1차 7건·2차 침해통지 미발송
8  main 브랜치 리뷰 필수 인원 0 → 1         지금은 0 (§6 아래)
9  429 안내 문구 (웹·Android·iOS)          가입 재개 전
```

★ 8번 보충: 리뷰 필수를 0 으로 둔 이유는 PR #2 의 작성자가 Brian 이고 GitHub 이
self-approve 를 금지하기 때문이다 — 1로 두면 아침에 merge 할 수 없다. 자세한 근거는
`docs/governance/BRANCH_PROTECTION_20260916.md`.

---

## 8. 권고 — 아침에 할 **한 단계**

```
PR #2 를 Ready for review 로 바꾸고 required check 3개가 초록인지 확인한다.
그 다음에 merge 를 판단한다.
```

배포는 그 뒤의 별도 판단이고, **가입 재개는 또 그 뒤다**(약관 승인 필요). 셋을 한 번에
묶지 않는 것이 이 패킷의 요점이다.
