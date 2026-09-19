/**
 * API 에러 매퍼 — 실패 종류마다 사용자가 할 행동이 갈리는지.
 *
 * 2026-08-25 장애에서 로그인 500·가입 실패·대시보드 오류가 전부
 * `Server error. Please try again.` 하나였다. 이 테스트가 고정하는 것은 문구가 아니라
 * **구분 자체**다 — 재시도하면 되는 것, 사용자가 고쳐야 하는 것, 문의해야 하는 것.
 */
import { describe, expect, it } from "vitest";

import { resolveApiError, withRequestId } from "@/lib/api/errors";

const axiosErr = (status: number, data?: unknown) => ({ response: { status, data } });

describe("resolveApiError — 백엔드 code 우선", () => {
  it.each([
    ["UNAUTHORIZED", 401, "unauthorized"],
    ["FORBIDDEN", 403, "forbidden"],
    ["NOT_FOUND", 404, "notFound"],
    ["CONFLICT", 409, "conflict"],
    ["VALIDATION_ERROR", 422, "validation"],
    ["PERIOD_LOCKED", 423, "periodLocked"],
    ["DB_UNAVAILABLE", 503, "dbUnavailable"],
    ["INTERNAL_ERROR", 500, "serverError"],
  ])("code %s → %s", (code, status, kind) => {
    expect(resolveApiError(axiosErr(status, { code })).kind).toBe(kind);
  });

  it("code 가 status 보다 우선한다 — 같은 status 에 여러 의미가 있다", () => {
    // 409 는 보통 CONFLICT 지만, 백엔드가 다른 의미를 붙였다면 그걸 따른다.
    const r = resolveApiError(axiosErr(409, { code: "PERIOD_LOCKED" }));
    expect(r.kind).toBe("periodLocked");
  });
});

describe("resolveApiError — code 없는 응답 폴백", () => {
  it.each([
    [401, "unauthorized"],
    [403, "forbidden"],
    [429, "rateLimited"],
    [502, "dbUnavailable"],
    [504, "timeout"],
  ])("status %i → %s", (status, kind) => {
    expect(resolveApiError(axiosErr(status)).kind).toBe(kind);
  });

  it("모르는 status 는 generic 으로 떨어지되 죽지 않는다", () => {
    expect(resolveApiError(axiosErr(418)).kind).toBe("generic");
  });

  it("★ code 가 빈 문자열이어도 status 폴백을 탄다", () => {
    // `code && BY_CODE[code]` 로 쓰면 "" 가 그대로 kind 가 돼 번역 키를 못 찾고
    // 화면에 빈 문자열이 뜬다(tsc 가 잡아준 실제 버그).
    expect(resolveApiError(axiosErr(503, { code: "" })).kind).toBe("dbUnavailable");
    expect(resolveApiError(axiosErr(500, { code: "" })).messageKey).toBe("serverError");
  });

  it("모르는 code 는 status 폴백을 탄다 — 백엔드가 새 code 를 추가해도 안 깨진다", () => {
    expect(resolveApiError(axiosErr(423, { code: "SOME_NEW_CODE" })).kind).toBe("periodLocked");
  });

  it("응답 본문이 문자열·null 이어도 죽지 않는다 (프록시가 만든 에러 페이지)", () => {
    expect(resolveApiError(axiosErr(502, "<html>Bad Gateway</html>")).kind).toBe("dbUnavailable");
    expect(resolveApiError(axiosErr(500, null)).kind).toBe("serverError");
  });
});

describe("응답이 없는 실패", () => {
  it("타임아웃과 네트워크 끊김을 구분한다", () => {
    // 안내가 다르다: 타임아웃 → "잠시 후 재시도", 네트워크 → "연결 확인"
    expect(resolveApiError({ code: "ECONNABORTED" }).kind).toBe("timeout");
    expect(resolveApiError({ message: "timeout of 10000ms exceeded" }).kind).toBe("timeout");
    expect(resolveApiError({ message: "Network Error" }).kind).toBe("network");
  });

  it("null·undefined 로도 깨지지 않는다", () => {
    expect(resolveApiError(null).kind).toBe("network");
    expect(resolveApiError(undefined).kind).toBe("network");
  });
});

describe("재시도 가능 여부", () => {
  it("★ 인프라 일시 장애는 재시도 가능, 코드 결함은 아니다", () => {
    expect(resolveApiError(axiosErr(503, { code: "DB_UNAVAILABLE" })).retryable).toBe(true);
    expect(resolveApiError(axiosErr(500, { code: "INTERNAL_ERROR" })).retryable).toBe(false);
  });

  it("사용자가 고쳐야 하는 것은 재시도 대상이 아니다", () => {
    for (const s of [403, 409, 422, 423]) {
      expect(resolveApiError(axiosErr(s)).retryable).toBe(false);
    }
  });
});

describe("추적 ID", () => {
  it("500 응답의 request_id 를 꺼내 문구에 붙인다", () => {
    const r = resolveApiError(axiosErr(500, { code: "INTERNAL_ERROR", request_id: "ab12cd34ef56" }));
    expect(r.requestId).toBe("ab12cd34ef56");
    expect(withRequestId("문제가 발생했습니다", r.requestId)).toContain("ab12cd34ef56");
  });

  it("ID 가 없으면 괄호를 붙이지 않는다 — 빈 괄호는 오류처럼 보인다", () => {
    expect(withRequestId("문제가 발생했습니다", undefined)).toBe("문제가 발생했습니다");
  });
});

describe("화면별 override", () => {
  it("로그인 화면의 401 은 '세션 만료'가 아니다 — 맥락에 따라 뜻이 다르다", () => {
    const r = resolveApiError(axiosErr(401, { code: "UNAUTHORIZED" }), {
      unauthorized: "validation",
    });
    expect(r.kind).toBe("validation");
    expect(r.messageKey).toBe("validation");
  });
});

describe("메시지 키 계약", () => {
  it("messageKey 는 errors 네임스페이스에 실재하는 키여야 한다", async () => {
    const en = (await import("@/messages/en.json")).default as { errors: Record<string, string> };
    const kinds = [
      axiosErr(401), axiosErr(403), axiosErr(404), axiosErr(409), axiosErr(422),
      axiosErr(423), axiosErr(429), axiosErr(500), axiosErr(503), axiosErr(504),
      axiosErr(418), { message: "Network Error" }, { code: "ECONNABORTED" },
    ].map((e) => resolveApiError(e).messageKey);

    for (const k of new Set(kinds)) {
      expect(en.errors[k], `errors.${k} 가 en.json 에 없다 — 화면에 키 이름이 그대로 노출된다`)
        .toBeTruthy();
    }
  });
});

// ── 429 — rate limit (PLATFORM_PARITY §9-9) ───────────────────────────────────
//
// 서버 계약(실측 2026-09-18, api/app/core/rate_limit.py):
//   status 429 · body {"detail": "RATE_LIMITED:<bucket>"} (code 없음) · Retry-After: <초>
// 클라이언트는 서버가 준 것만 쓴다. 5회/시간 같은 정책 숫자를 여기서 재현하지 않는다.
import { parseRetryAfter, rateLimitMessage } from "@/lib/api/errors";

const rl = (retryAfter?: string, detail = "RATE_LIMITED:signup") => ({
  response: { status: 429, data: { detail }, headers: retryAfter === undefined ? {} : { "retry-after": retryAfter } },
});

describe("resolveApiError — 429", () => {
  it("429 는 rateLimited 이고 재시도 가능하다 — code 가 없어도", () => {
    const r = resolveApiError(rl("1993"));
    expect(r.kind).toBe("rateLimited");
    expect(r.retryable).toBe(true);
    expect(r.code).toBeUndefined();
  });

  it("Retry-After 초를 싣는다", () => {
    expect(resolveApiError(rl("1993")).retryAfterSeconds).toBe(1993);
    expect(resolveApiError(rl("13")).retryAfterSeconds).toBe(13);
  });

  it("헤더 키 대소문자에 안 흔들린다", () => {
    const e = { response: { status: 429, data: { detail: "RATE_LIMITED:auth" }, headers: { "Retry-After": "7" } } };
    expect(resolveApiError(e).retryAfterSeconds).toBe(7);
  });

  it.each([
    [undefined, "없음"],
    ["", "빈 문자열"],
    ["abc", "숫자 아님"],
    ["-5", "음수"],
    ["0", "0"],
    ["99999999", "하루 초과"],
  ])("Retry-After %s (%s) → undefined 로 폴백, 여전히 rateLimited", (raw) => {
    const r = resolveApiError(rl(raw));
    expect(r.kind).toBe("rateLimited");
    expect(r.retryAfterSeconds).toBeUndefined();
  });

  it("HTTP-date 형식도 초로 환산한다 (프록시가 바꿔 보내는 경우)", () => {
    const now = Date.UTC(2026, 8, 18, 12, 0, 0);
    const date = new Date(now + 90_000).toUTCString();
    expect(parseRetryAfter(date, now)).toBe(90);
  });

  it("detail 토큰만으로도 429 를 식별한다 — 프록시가 status 를 바꿔도", () => {
    const e = { response: { status: 503, data: { detail: "RATE_LIMITED:signup" } } };
    expect(resolveApiError(e).kind).toBe("rateLimited");
  });

  it("★ 429 ≠ 451 — 법역·게시 차단은 rateLimited 가 아니다", () => {
    const r = resolveApiError({ response: { status: 451, data: { detail: "SIGNUP_BLOCKED:KR_REFERENCE_ONLY" } } });
    expect(r.kind).not.toBe("rateLimited");
    expect(r.retryable).toBe(false);
  });

  it("★ 429 ≠ 401 — 비밀번호 오류로 오인되지 않는다", () => {
    expect(resolveApiError(rl("13", "RATE_LIMITED:auth")).kind).not.toBe("unauthorized");
  });

  it("문구: Retry-After 있으면 분 단위 안내를 덧붙이고, 없으면 기본 문장만", () => {
    const tErr = (k: string, v?: Record<string, string | number>) => (v ? `${k}:${v.minutes}` : k);
    expect(rateLimitMessage(tErr, { retryAfterSeconds: undefined })).toBe("rateLimited");
    expect(rateLimitMessage(tErr, { retryAfterSeconds: 13 })).toBe("rateLimited rateLimitedRetryIn:1");
    expect(rateLimitMessage(tErr, { retryAfterSeconds: 1993 })).toBe("rateLimited rateLimitedRetryIn:34");
  });
});
