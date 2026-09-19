# SYNC-AUDIT-ATTRIBUTION-GAP — 오프라인 동기화로 들어온 쓰기는 행위자가 없다

> **상태**: `OPEN — NOT REMEDIATED` · 수정하지 않음(판독만)
> **발견**: 2026-09-08, 프로덕션 사용현황 집계 중 `audit_log.user_id` NULL 을 추적
> **성격**: 원인 규명 완료. 이 문서는 문제를 해결하지 않는다.

---

## 한 줄

`POST /farms/{farm_id}/sync` 로 들어온 모든 쓰기의 감사기록에 **`user_id` 가 없다.**
인증은 통과했는데 누가 넣었는지는 남지 않는다.

---

## 실측

### 관측 — 프로덕션

최근 10일 활동 7건 중 **6건이 `user_id` NULL** 이었다. 전부 `CREATE mating` 계열.

```
09-07 02:17  CREATE mating           user 없음   US
09-06 18:19  CREATE mating           user 없음   US
09-05 23:21  DELETE matings          user 있음   US
09-05 15:58  CREATE pregnancy_check  user 없음   US
09-05 15:49  CREATE mating           user 없음   US
09-05 15:41  CREATE mating           user 없음   US
09-05 15:37  CREATE mating           user 없음   US
```

### 원인 — 헬퍼가 `user_id` 를 받지 않는다

이 저장소에는 감사기록 헬퍼가 **둘** 있고, 한쪽에만 행위자가 있다.

```
api/app/services/event_service.py:147
    async def _audit(db, user_id, farm_id, action, entity_type, entity_id, new_value)
                         ^^^^^^^  있음

api/app/services/sync_service.py:143
    def _audit(farm_id, entity_type, entity_id, action, new_value)
                                                        ^ user_id 자체가 파라미터에 없다
```

### 사용자를 몰라서가 아니다 — 확인하고 버린다

sync 엔드포인트는 인증을 **통과시킨 뒤** 신원을 서비스로 넘기지 않는다.

```
api/app/routers/base/sync.py:24
    @router.post("/{farm_id}/sync",
                 dependencies=[require_farm_role(*_ENTRY_ROLES)])   ← 역할 검사함
    async def sync(body, farm=Depends(get_farm_context), db=...):    ← JWT·멤버십 검증함
        return await process_sync(db, farm, body)                    ← 사용자는 안 넘김

api/app/services/sync_service.py:996
    async def process_sync(db, farm, req)                            ← 받을 자리가 없다
```

즉 **"누구인지 확인한 다음 잊어버린다."** 권한 판정에는 썼는데 기록에는 안 남긴다.

### 부수 관측 — `entity_type` 표기가 두 갈래다

```
sync_service           "mating" · "farrowing" · "weaning" · "pregnancy_check"   (단수)
event_service          "matings" · "farrowings" · "weanings"                    (복수)
```

프로덕션 집계가 이 분기를 그대로 보여준다(`matings` 123 vs `mating` 8).
즉 **단수 = 모바일 동기화 경로, 복수 = 웹 REST 경로**로 읽힌다.

★ 이 표기 차이는 관리자 감사 화면의 필터를 둘로 쪼갠다. 한쪽만 걸면 절반이
  안 보인다.

---

## 영향

```
감사 추적       CLAUDE.md 핵심 설계원칙 5 "모든 CUD → audit_log" 는 지켜지고 있으나,
                행위자가 빠져 "누가 했는가" 를 답하지 못한다.

CONSENT-EVIDENCE  ★ 이것이 이 문서를 법무 트랙에 두는 이유다.
                동의 증빙을 locale·해시·채널까지 정교화해도, 그 옆의 감사기록이
                사람을 특정하지 못하면 "이 농장에서 누가 무엇을 했는가" 가
                끊긴다. 증빙 강화보다 앞에 놓고 볼 값어치가 있다.

모바일 우선 시장  VN·MX 등 오프라인 입력 비중이 큰 시장일수록 NULL 비율이 커진다.
                지금 US 유입에서 이미 6/7 이다.

관리자 화면      entity_type 두 갈래 때문에 필터가 절반만 잡는다.
```

## ★ "감사기록이 조작 가능하다"는 뜻이 아니다

행위자가 **비어 있는** 것이지 **틀린** 것이 아니다. `farm_id`·시각·엔티티·변경내용은
정상 기록된다. 인증·권한 검사도 정상 동작한다. 과대평가하지 않는다.

---

## 고치려면

작아 보이지만 확인이 필요하다.

```
1  sync 라우터가 CurrentUser 를 받아 process_sync 에 넘긴다.
2  sync_service._audit 에 user_id 파라미터를 추가한다.
   ★ audit_log.user_id 는 이미 nullable 이므로 스키마 변경은 없다.

3  기존 NULL 행을 소급 채우지 않는다. 누가 했는지 모르는 것을 추정으로 채우면
   감사기록이 아니라 창작이 된다. NULL 로 남기고 "이 시점 이전은 미귀속" 을 적는다.

4  entity_type 표기 통일은 별건이다. 지금 바꾸면 기존 행과 새 행이 갈라진다 —
   읽기 시점 정규화가 안전하다(앞서 Admin Audit Phase 1 C 로 제안된 방식).
```

## 왜 지금 고치지 않았나

이번에 받은 범위는 **판독**이었다. 그리고 이것은 감사·귀속 경계 변경이라
`3`(소급 처리 방침)과 `4`(표기 통일 방식)에 결정이 붙는다. 승인 없이 끼워 넣지 않는다.

---

## 관련

```
api/app/services/sync_service.py:143        user_id 없는 헬퍼
api/app/services/sync_service.py:996        사용자를 받지 않는 진입점
api/app/routers/base/sync.py:24             인증하고 넘기지 않는 라우터
api/app/services/event_service.py:147       행위자를 남기는 쪽(대조군)
api/app/db/models/platform.py:163           audit_log.user_id — 이미 nullable
docs/planning/common/2026-08_monthly-report.md §2-1   NULL 6/7 관측
```
