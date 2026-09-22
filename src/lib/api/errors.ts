/**
 * API 에러 → 사용자에게 보여줄 종류 매핑.
 *
 * ## 왜 필요한가
 *
 * 2026-08-25 장애에서 사용자가 본 것은 전부 `Server error. Please try again.` 하나였다.
 * 로그인 500·가입 실패·대시보드 오류가 같은 문구라서
 *   "다시 하면 되나?"  "내가 뭘 잘못했나?"  "문의해야 하나?"
 * 를 구분할 수 없었다.
 *
 * ★ 이 파일의 원칙: **사용자가 다음에 할 행동이 다르면 다른 메시지여야 한다.**
 *   - 재시도하면 되는 것      네트워크·타임아웃·503(DB 일시 장애)·429
 *   - 사용자가 고쳐야 하는 것  422 입력 오류·409 충돌·423 기간 잠금·403 권한
 *   - 문의해야 하는 것        500 (추적 ID 를 함께 보여준다)
 *
 * 분기 기준은 **백엔드가 주는 `code`** 이고 HTTP status 는 보조다.
 * (code 계약: api/app/core/exceptions.py · 테스트 tests/unit/test_error_contract.py)
 */

export type ApiErrorKind =
  | "network"
  | "timeout"
  | "unauthorized"
  | "forbidden"
  | "notFound"
  | "conflict"
  | "validation"
  | "periodLocked"
  | "rateLimited"
  | "dbUnavailable"
  | "serverError"
  | "generic";

export interface ResolvedApiError {
  kind: ApiErrorKind;
  /** `errors` 네임스페이스의 키. next-intl `useTranslations("errors")` 로 쓴다. */
  messageKey: ApiErrorKind;
  /** 500·503 응답의 추적 ID. 문의 시 로그와 잇는 유일한 단서다. */
  requestId?: string;
  /** 그대로 다시 시도하면 성공할 수 있는가 — 버튼에 "다시 시도"를 띄울지 결정한다. */
  retryable: boolean;
  status?: number;
  /** 백엔드 code 원문(로깅·디버깅용). UI 문구로 쓰지 않는다. */
  code?: string;
  /**
   * 429 의 `Retry-After` 헤더(초). 서버가 준 값만 싣는다 — 클라이언트가 정책을 추정해서
   * 만들지 않는다. 없거나·정수가 아니거나·0 이하·하루를 넘으면 undefined (일반 안내로 폴백).
   */
  retryAfterSeconds?: number;
}

/** Retry-After 상한. 이보다 크면 서버 오류로 보고 버린다 — 하루 넘게 잠그는 정책은 없다. */
const RETRY_AFTER_MAX_SECONDS = 86_400;

/**
 * `Retry-After` 를 초 단위 정수로. 서버 계약(api/app/core/rate_limit.py)은 delta-seconds 만
 * 보내지만, 프록시가 HTTP-date 로 바꿔 보낼 수 있어 그것도 받는다.
 *
 * ★ 서버 정책(5회/시간 등)을 여기서 재현하지 않는다. 값이 없으면 없는 것이다.
 */
export function parseRetryAfter(raw: unknown, now: number = Date.now()): number | undefined {
  if (typeof raw !== "string" && typeof raw !== "number") return undefined;
  const s = String(raw).trim();
  if (!s) return undefined;
  let seconds: number;
  if (/^\d+$/.test(s)) {
    seconds = Number(s);
  } else {
    const at = Date.parse(s);
    if (Number.isNaN(at)) return undefined;
    seconds = Math.ceil((at - now) / 1000);
  }
  if (!Number.isFinite(seconds) || seconds <= 0 || seconds > RETRY_AFTER_MAX_SECONDS) return undefined;
  return seconds;
}

/** 백엔드 code → 표시 종류. status 보다 우선한다(같은 status 에 여러 의미가 있다). */
const BY_CODE: Record<string, ApiErrorKind> = {
  UNAUTHORIZED: "unauthorized",
  FORBIDDEN: "forbidden",
  NOT_FOUND: "notFound",
  CONFLICT: "conflict",
  VALIDATION_ERROR: "validation",
  PERIOD_LOCKED: "periodLocked",
  DB_UNAVAILABLE: "dbUnavailable",
  INTERNAL_ERROR: "serverError",
};

/** code 가 없는 응답(구버전 API·프록시가 만든 에러)을 위한 폴백. */
const BY_STATUS: Record<number, ApiErrorKind> = {
  400: "validation",
  401: "unauthorized",
  403: "forbidden",
  404: "notFound",
  409: "conflict",
  422: "validation",
  423: "periodLocked",
  429: "rateLimited",
  500: "serverError",
  502: "dbUnavailable",
  503: "dbUnavailable",
  504: "timeout",
};

const RETRYABLE: ReadonlySet<ApiErrorKind> = new Set<ApiErrorKind>([
  "network",
  "timeout",
  "rateLimited",
  "dbUnavailable",
]);

interface AxiosLike {
  code?: string;
  message?: string;
  response?: { status?: number; data?: unknown; headers?: Record<string, unknown> };
}

function bodyOf(err: AxiosLike): { code?: string; request_id?: string; detail?: unknown } {
  const d = err.response?.data;
  return d && typeof d === "object" ? (d as { code?: string; request_id?: string; detail?: unknown }) : {};
}

/** axios 는 헤더 키를 소문자로 정규화하지만, 다른 어댑터·테스트 대역은 아닐 수 있다. */
function headerOf(err: AxiosLike, name: string): unknown {
  const h = err.response?.headers;
  if (!h) return undefined;
  const lower = name.toLowerCase();
  for (const k of Object.keys(h)) if (k.toLowerCase() === lower) return h[k];
  return undefined;
}

/**
 * 429·451 은 `code` 없이 `detail: "TOKEN:qualifier"` 로 온다(FastAPI HTTPException 경로).
 * status 가 이미 답을 주지만, 프록시가 status 를 바꿔 보내는 경우를 위해 토큰도 본다.
 */
function detailToken(detail: unknown): string | undefined {
  return typeof detail === "string" ? detail.split(":")[0] : undefined;
}

/**
 * 어떤 형태의 실패든 하나의 표시 종류로 정규화한다.
 *
 * @param overrides 화면별 예외. 예를 들어 로그인 화면의 401 은 "세션 만료"가 아니라
 *   "아이디/비밀번호 불일치"다 — 같은 status 라도 맥락에 따라 뜻이 다르므로 호출 측이 덮는다.
 */
export function resolveApiError(
  err: unknown,
  overrides?: Partial<Record<ApiErrorKind, ApiErrorKind>>,
): ResolvedApiError {
  const e = (err ?? {}) as AxiosLike;
  const status = e.response?.status;
  const { code, request_id: requestId, detail } = bodyOf(e);

  let kind: ApiErrorKind;
  if (status === undefined) {
    // 응답 자체가 없음 = 요청이 서버까지 못 갔거나 답을 못 받았다.
    // ECONNABORTED 는 axios 의 타임아웃 코드다 — 네트워크 끊김과 구분해야
    // "연결 확인"과 "잠시 후 재시도" 중 맞는 안내를 할 수 있다.
    kind = e.code === "ECONNABORTED" || /timeout/i.test(e.message ?? "") ? "timeout" : "network";
  } else if (status === 429 || detailToken(detail) === "RATE_LIMITED") {
    // ★ 429 는 code 가 없다 — rate_limit.py 가 HTTPException 으로 던져 {detail} 만 온다.
    //   BY_CODE 를 먼저 보면 (없으니) status 폴백으로 오긴 하지만, 뜻을 여기서 명시한다:
    //   이것은 입력 오류도 권한 오류도 아니고, 451(법역·게시 차단)과도 다르다.
    kind = "rateLimited";
  } else {
    // `code &&` 를 쓰면 code 가 빈 문자열일 때 "" 가 그대로 kind 가 된다(타입·런타임 모두 오류).
    // 존재 여부만 보고 조회한 뒤 ?? 로 폴백한다.
    kind = (code ? BY_CODE[code] : undefined) ?? BY_STATUS[status] ?? "generic";
  }

  const finalKind = overrides?.[kind] ?? kind;
  const retryAfterSeconds =
    finalKind === "rateLimited" ? parseRetryAfter(headerOf(e, "retry-after")) : undefined;
  return {
    kind: finalKind,
    messageKey: finalKind,
    requestId,
    retryable: RETRYABLE.has(finalKind),
    status,
    code,
    retryAfterSeconds,
  };
}

/**
 * 429 안내 문구 — 기본 문장에, 서버가 Retry-After 를 줬을 때만 대략의 대기 시간을 덧붙인다.
 * 값이 없거나 이상하면 기본 문장만. 카운트다운·버튼 잠금은 이 트랙의 범위가 아니다.
 *
 * @param tErr `useTranslations("errors")`
 */
export function rateLimitMessage(
  tErr: (key: string, values?: Record<string, string | number>) => string,
  e: Pick<ResolvedApiError, "retryAfterSeconds">,
): string {
  const base = tErr("rateLimited");
  if (!e.retryAfterSeconds) return base;
  const minutes = Math.max(1, Math.ceil(e.retryAfterSeconds / 60));
  return `${base} ${tErr("rateLimitedRetryIn", { minutes })}`;
}

/**
 * 문구 뒤에 추적 ID를 붙인다 — 500 계열에서만 의미가 있다.
 * 사용자가 이 값을 알려주면 서버 로그에서 그 요청 하나를 정확히 찾을 수 있다.
 */
export function withRequestId(message: string, requestId?: string): string {
  return requestId ? `${message} (${requestId})` : message;
}
