# 가입·인증 rate limit 기본값 — 근거 (2026-09-16)

> **성격**: 제품 정책이 아니라 **운영 기본값**이다. 승인 대기 중인 정책을 코드에
> 확정하지 않는다는 규율(CLAUDE.md)에 따라, 여기 적은 값은 전부 env 로 덮을 수 있고
> 실제 트래픽을 본 뒤 조정하는 것을 전제로 한다.

---

## 왜 지금 넣는가

```
/auth/register           속도 제한 0건
/onboarding/complete     속도 제한 0건
2026-09-11 전수 확인 — slowapi·limiter·throttle 어느 것도 없다
```

지금은 노출이 없다. G-3 가 배포되면 모든 법역이 451 이고, 배포 전에도 H13 허용목록으로
US 외는 막힌다. **가입이 다시 열리는 순간 무제한이 된다.**

★ 이것을 성능 항목으로 분류하지 않는다. 스팸 가입은 계정마다 이메일·이름·농장명이
남으므로 **개인정보 대량 수집**이고, 우리가 그것을 막을 수단 없이 수집 경로를 열어두는
것 자체가 법무 트랙과 같은 축이다.

---

## 기본값과 근거

| 버킷 | 기본값 | 적용 경로 | 근거 |
|---|---|---|---|
| `signup` | **5 / 시간** | `/auth/register` · `/onboarding/complete` | 한 농장이 한 번 가입한다. 재시도·오타 수정을 넉넉히 봐도 시간당 5회면 정상 사용자가 닿지 않는다. 같은 사무실에서 여러 계정을 만드는 경우(조직 관리자가 직원 계정 생성)는 이 경로가 아니라 인증된 `/members` 경로다 |
| `auth` | **20 / 분** | `/auth/login` · `/auth/password-reset/request` · `/auth/password-reset/confirm` | 비밀번호 오타·자동완성 재시도를 흡수하되 크리덴셜 스터핑 속도는 아니다 |

```
설정      settings.rate_limit_signup_per_hour  (env: RATE_LIMIT_SIGNUP_PER_HOUR)
          settings.rate_limit_auth_per_minute  (env: RATE_LIMIT_AUTH_PER_MINUTE)
비활성    0 이하 → 제한 없음 (개발·테스트 기본)
```

★ **값이 코드 여러 곳에 흩어지지 않는다.** 라우터는 버킷 이름만 알고, 숫자는 settings
한 곳에서 온다. `limiter()` 가 한도를 호출 시점에 읽으므로 import 시점에 굳지 않는다.

---

## 설계 결정 네 가지

### 1. Redis — 프로세스 메모리 카운터를 쓰지 않는다

API 는 워커 여러 개로 뜬다. 프로세스 안에 카운터를 두면 **한도가 워커 수만큼 곱해진다**
(워커 4개면 실제 20/시간). 이미 `core/cache.py` 가 Redis 를 쓰고 있어 새 의존성이
아니다. 키 공간만 `pigos:rl:` 로 분리했다.

### 2. 식별자는 `X-Real-IP` — `X-Forwarded-For` 는 읽지 않는다

프로덕션 실측(`~/pigos/nginx/nginx.conf`):

```
proxy_set_header X-Real-IP $remote_addr;    ← 매 요청 덮어쓴다 (3곳 전부)
X-Forwarded-For                             ← 설정하지 않는다
```

즉 `X-Real-IP` 는 우리 프록시가 만들고, 클라이언트가 보낸 값은 통과하지 못한다.
반면 `X-Forwarded-For` 는 **아무나 붙일 수 있고 우리가 만들지 않으므로** 신뢰할 근거가
없다. 그래서 읽지 않는다 — 읽으면 헤더 한 줄로 한도를 무한히 우회할 수 있다.

프록시 구성이 바뀌면 `rate_limit.client_key` 하나만 고친다.

### 3. Redis 장애 시 fail-open — 그리고 eligibility 는 fail-closed

```
rate limit    Redis 죽음 → 통과시킨다. 남용 완화이지 인가가 아니다.
              캐시 장애로 정상 농가 가입이 전면 중단되는 쪽이 더 나쁘다
eligibility   어떤 경우에도 통과시키지 않는다. 실패하면 막는다
```

논쟁 여지가 있는 선택이라 코드 주석과 여기 양쪽에 적는다. 두 계층의 실패 방향이
**반대**라는 것이 핵심이다.

### 4. ★ rate limit 은 eligibility 를 대신하지 않는다

```
누가 가입할 수 있는가     eligibility.assert_country_entry_allowed   (B-9, 단일 진입점)
얼마나 자주 시도하는가    rate_limit
```

rate limit 에 국가·법역 판단을 넣지 않는다. 넣는 순간 가입 허용 판단이 두 군데가 되고,
그것이 B-9 에서 정리한 바로 그 문제다. 테스트가 이 경계를 고정한다.

---

## 429 응답 계약

```
status    429
detail    "RATE_LIMITED:{bucket}"        기존 "SIGNUP_BLOCKED:{reason}" 과 같은 모양
header    Retry-After: {남은 초}
```

새 status·새 포맷을 발명하지 않았다 — 모바일 두 클라이언트가 이미 `detail` 문자열을
파싱하는 구조다(§9-7-2).

★ 모바일·웹이 429 를 어떻게 보여줄지는 **아직 없다**. `PLATFORM_PARITY` §9-9 로 등재.

---

## 남은 것

```
운영 관측    429 가 실제로 얼마나 나가는지 볼 수단이 없다 (관측 baseline 과 같은 항목)
값 조정      실제 가입 트래픽을 본 뒤. 지금 값은 측정이 아니라 판단이다
클라이언트   429 안내 문구 — PLATFORM_PARITY §9-9
```
