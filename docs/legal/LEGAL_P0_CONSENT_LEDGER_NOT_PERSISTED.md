# LEGAL-P0-CONSENT-LEDGER-NOT-PERSISTED

> **상태**: `OPEN — NOT REMEDIATED` · 수정하지 않음(승인 대기)
> **발견**: 2026-09-03, LEGAL-P0-CONSENT-FARM-AUTHORITY 듀얼 리뷰 중
> **성격**: 사실 기록. 이 문서는 문제를 해결하지 않는다.

---

## 한 줄

`POST /consent/record` 와 `/consent/withdraw` 는 **commit 을 하지 않는다.**
200 을 반환하고, 기록한 행은 요청이 끝날 때 rollback 된다.

---

## 실측 (코드 판독, 2026-09-03)

### 1) 세션은 commit 없이 닫힌다

```
api/app/core/dependencies.py:36

    async def get_db() -> AsyncSession:
        async with AsyncSessionLocal() as session:
            yield session
```

`async with` 종료 = `session.close()`. 열려 있던 트랜잭션은 커밋되지 않고 버려진다.

### 2) consent 경로 어디에도 commit 이 없다

```
api/app/routers/base/consent.py        db.commit  0건
api/app/services/consent_service.py    db.commit  0건 — flush 만 (227, 283줄)
api/app/main.py                        commit     0건 (미들웨어 없음)
```

### 3) ★ 다른 곳은 전부 한다 — 이 서비스만 빠졌다

라우터가 아니라 **서비스**가 커밋하는 것이 이 코드베이스의 패턴이다.

```
event_service          12        threshold_service       2
auth_service            5        task_service            2
farm_service            4        feed_service            2
notification_service    3        sync_service            1
device_service          3        insight_service         1
                                 chat_service            1

consent_service         0   ←   쓰기를 하는 유일한 0
```

`0` 인 나머지 서비스(`kpi_service`·`jurisdiction`·`eligibility`·`terms_renderer`
·`report_service` …)는 전부 읽기 전용/순수 함수다. **쓰기를 하면서 커밋하지 않는
서비스는 `consent_service` 하나뿐이다.**

---

## 왜 지금까지 아무도 몰랐나 — 테스트가 구조적으로 못 잡는다

```
api/tests/integration/conftest.py:114

    async def mock_commit():
        await session.flush()

    session.commit = mock_commit          ← commit 을 flush 로 대체
```

테스트 세션은 격리를 위해 `commit` 을 `flush` 로 바꿔 끼운다. 그래서

```
커밋 누락        →  테스트에서는 flush 와 구분 불가        →  전원 통과
_ledger_count    →  같은 트랜잭션 안에서 읽음              →  행이 보인다
```

통합 테스트 1389건이 전부 통과하면서도 이 부류의 결함은 **원리적으로** 검출되지
않는다. `test_record_over_http_writes_the_ledger` 조차 rollback 되는 원장을 상대로
통과한다.

★ 이것은 그 fixture 를 탓하는 게 아니다. 테스트 격리에는 합리적인 설계다.
  다만 **"커밋했는가"는 이 스위트가 답할 수 없는 질문**이라는 뜻이고, 그 층은
  별도 수단으로 봐야 한다.

---

## 영향

```
동의 기록 유실     record 가 200 을 주고 아무것도 남기지 않는다

fail-closed 무력화 LEGAL-P0-WEB-CONSENT-FAIL-CLOSED(e064e60)는 record 200 을
                   로그인 확정 조건으로 삼는다. 200 은 오므로 가입은 진행되고,
                   원장은 비어 있다. 어디에서도 오류가 나지 않는다.
                   ★ 방금 만든 fail-closed 가 이 상태에서는 무의미하다

FARM-AUTHORITY     귀속을 옳게 만들어도 저장되지 않으면 의미가 없다

철회               사용자가 철회해도 남지 않는다. 법적으로 더 나쁘다
```

## ★ "프로덕션 원장 0행의 원인"이라고 단정하지 않는다

그렇게 쓰고 싶은 유혹이 있으나, 근거가 부족하다.

```
PRODUCTION_CONSENT_LEDGER_AUDIT_20260902.md
    docker logs pigos-api | grep '/api/v1/consent/...'   →  요청 0건
```

**애초에 호출이 없었다.** 호출이 없으면 커밋 여부와 무관하게 0행이다. 따라서 이
결함은 원장 0행의 *충분조건이 되었을* 잠복 결함이지, 관측된 0행의 입증된 원인이
아니다. 둘을 구분해서 적는다.

확실한 것은 이것이다 — **앞으로 호출이 들어와도 여전히 0행이다.**

---

## 고치려면

한 줄짜리 변경으로 보이지만 확인이 필요하다.

```
1  두 핸들러(record·withdraw)에서 커밋한다.
   ★ 라우터가 아니라 서비스에서 하는 것이 이 코드베이스 패턴이다
     (event_service·auth_service 와 같은 층)

2  거부 경로가 무엇도 남기지 않는지 재확인.
   422(ack 누락) · 451(국가 차단) · 403(농장 권한)은 전부 첫 write 이전에
   raise 하므로 현재는 문제없다. 커밋을 넣은 뒤 이것을 다시 증명해야 한다

3  ★ 테스트로는 증명할 수 없다 (위 참조).
   실제 세션 기준 검증 수단이 따로 필요하다 —
   commit 오버라이드를 걸지 않은 별도 fixture, 또는 배포 후 실측
```

`3` 때문에 이 건은 "한 줄 고치고 끝"이 아니다. 검증 수단을 같이 만들어야 한다.

---

## 왜 이번에 고치지 않았나

승인받은 범위는 `LEGAL-P0-CONSENT-FARM-AUTHORITY`(귀속 권한)였다. 이것은 **쓰기
지속성**이라는 다른 축이고, 검증 수단 신설이 따라붙는다. 승인 없이 끼워 넣지 않는다.

---

## 관련

```
api/app/core/dependencies.py:36                  커밋 없이 닫히는 세션
api/app/routers/base/consent.py:43,58            두 엔드포인트
api/app/services/consent_service.py:227,283      flush 만 하는 지점
api/tests/integration/conftest.py:114            commit→flush 대체 (검출 불가 원인)
docs/legal/PRODUCTION_CONSENT_LEDGER_AUDIT_20260902.md   원장 0행 · 요청 0건
e064e60                                          이 결함이 무력화하는 fail-closed
f4d9c3f                                          farm 귀속 권한 (이 결함 위에서는 무의미)
```
