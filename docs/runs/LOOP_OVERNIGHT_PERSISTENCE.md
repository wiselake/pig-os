# 밤샘 RUN — LEGAL-P0-CONSENT-LEDGER-PERSISTENCE

> 작성 2026-09-03. 이 RUN 하나만 한다. 끝나기 전에 iOS consent · CONSENT-EVIDENCE 로 넘어가지 않는다.

## 목표

`POST /consent/record` · `/consent/withdraw` 가 **요청이 끝난 뒤에도 남는다**는 것을
증명 가능한 형태로 만든다. 지금은 200 을 주고 rollback 된다.

## 하드규칙

```
push 금지 · deploy 금지 · production 변경 금지
법무 빈칸(HUMAN_INPUT_QUEUE.md) 날조 금지
1변경 = 1커밋 · trailer 포함
검증 통과 후에만 커밋 (pytest 전체 + ruff)
막히거나 애매하면 멈추고 리포트
```

## 이번 RUN 범위 밖 — 손대지 않는다

```
farm.active 와 철회 권리의 관계          별도 결정 (대표 방향: 종속시키지 않는 쪽)
org admin 의 legal-consent authority     canonical 유지, 임의로 좁히지 않는다
farm_id=None 모델 의미 변경              CONSENT-EVIDENCE 소관
consent evidence schema / migration
login mandatory-consent gate
production deploy
```

## 순서 (뒤집지 않는다)

```
1  판독 — 코드 변경 0
   1-1  consent write 함수 call graph 전수
   1-2  이 저장소의 transaction owner / commit convention 실측
   1-3  service 내부 commit 이 다른 업무 atomicity 를 깨는 경로가 있는지
   1-4  get_db 의 요청 종료 semantics 재증명 (추론 아닌 실측)

2  transaction owner 확정

3  persistence 테스트 경로 신설 — ★ 코드 수정보다 먼저 (RED 확보)

4  commit 구현 (최소)

5  전체 회귀 + 반증(수정 제거 시 실패)
```

## 필수 성공 계약

```
record   2xx → 요청 세션 완전 종료 → **완전히 새로운 DB 세션** → ledger row 존재
withdraw 2xx → fresh session → 철회 상태가 실제 DB 에 존재
실패     commit/DB 실패 시 → 2xx 금지 → fresh session 에서 부분 기록 없음
```

## 테스트 하네스 규율 — 이번 RUN 의 핵심

```
★ 검증 대상인 commit 을 테스트 코드가 무력화하면 안 된다.

현재 conftest 의 commit→flush monkeypatch(conftest.py:114)는
이 P0 의 증거로 사용 금지. 그 fixture 는 테스트 격리용이므로
전역에서 제거하지 않는다 — 기존 격리를 깨뜨리게 된다.

대신 별도 persistence 경로를 만든다:
    기존 integration fixture   격리 방식 그대로 유지
    persistence fixture        commit override 없음
                               request session 과 verification session 분리
                               테스트 종료 시 자기가 만든 행만 정리
```

## 보고 항목 (끝나고 이 순서로)

```
transaction owner
root cause
수정 위치
fresh-session persistence 증거
failure rollback 증거
기존 API response contract 영향
전체 pytest / ruff 결과
```
