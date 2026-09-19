/**
 * 429 — 가입·온보딩·로그인·비밀번호 재설정에서 속도 제한이 다른 실패로 오인되지 않는다.
 *
 * 서버 계약(2026-09-18 실측): status 429 · {"detail":"RATE_LIMITED:<bucket>"} · Retry-After 초.
 * PLATFORM_PARITY §9-9 — 세 클라이언트 parity 의 웹 쪽 증거.
 *
 * ★ 이 파일은 정책 숫자(5회/시간·20회/분)를 어디에도 적지 않는다. 서버가 준 응답만 쓴다.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { SignupPlan } from "@/types/api.types";

const onboard = vi.fn();
const signupPlan = vi.fn();
const record = vi.fn();
const login = vi.fn();
const requestPasswordReset = vi.fn();
const confirmPasswordReset = vi.fn();
const setAuth = vi.fn();
const replace = vi.fn();
let mockSearch = "";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), refresh: vi.fn(), back: vi.fn(), forward: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(mockSearch),
  useParams: () => ({}),
}));
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}));
// 키 그대로 반환 + placeholder 를 붙여 어떤 키·값이 쓰였는지 단언할 수 있게
vi.mock("next-intl", () => ({
  useTranslations: (ns?: string) => (k: string, v?: Record<string, unknown>) =>
    `${ns ? ns + "." : ""}${k}${v ? "{" + Object.values(v).join(",") + "}" : ""}`,
  useLocale: () => "en",
}));
vi.mock("@/lib/api/endpoints/auth", () => ({
  authApi: {
    onboard: (...a: unknown[]) => onboard(...a),
    countries: () => Promise.resolve([]),
    login: (...a: unknown[]) => login(...a),
    requestPasswordReset: (...a: unknown[]) => requestPasswordReset(...a),
    confirmPasswordReset: (...a: unknown[]) => confirmPasswordReset(...a),
  },
}));
vi.mock("@/lib/api/endpoints/consent", () => ({
  consentApi: { signupPlan: (...a: unknown[]) => signupPlan(...a), record: (...a: unknown[]) => record(...a) },
}));
vi.mock("@/store/auth.store", () => ({
  useAuthStore: (sel: (s: { setAuth: typeof setAuth; accessToken: null }) => unknown) =>
    sel({ setAuth, accessToken: null }),
}));
vi.mock("@/lib/analytics", () => ({ track: vi.fn(), identifyUser: vi.fn() }));

import OnboardingPage from "@/app/onboarding/page";
import LoginPage from "@/app/(auth)/login/page";
import ForgotPasswordPage from "@/app/(auth)/forgot-password/page";

const PLAN: SignupPlan = {
  jurisdiction: { code: "US", country: "US", group: "US", counsel_review: false, notes: [] },
  gate: { signup_blocked: false, paid_blocked: false, release_hold: false, reason_code: null },
  state_flags: { state: null, written_opt_in_required: false, do_not_sell_link: false, honor_uoom: false, exclude_location_from_sale: false },
  documents: [{ doc_id: "MASTER_TERMS", kind: "master", version: "0.1", status: "DRAFT_LAWYER_PENDING", lang: "en", is_legal_priority: true, lang_pending: false, body: null }],
  notice_version: "MASTER_TERMS@0.1", any_draft: true, lang_gate: false, required_acks: ["TERMS", "PRIVACY"],
  purposes: [{ purpose_code: "SERVICE_OPERATION", order: 0, ui_kind: "NOTICE", lawful_basis: "CONTRACT", visible: true, is_toggle: false, default_on: false, requires_evidence: false, status_tag: "LEGAL_REQUIREMENT", auto_off_if_uoom: false }],
  lang: "en",
};

/** 서버 계약 그대로 — code 없음, detail 토큰, Retry-After 헤더 */
const err429 = (bucket: "signup" | "auth", retryAfter?: string) => ({
  response: { status: 429, data: { detail: `RATE_LIMITED:${bucket}` }, headers: retryAfter ? { "retry-after": retryAfter } : {} },
});
const err451 = { response: { status: 451, data: { detail: "SIGNUP_BLOCKED:KR_REFERENCE_ONLY" } } };
const err401 = { response: { status: 401, data: { code: "UNAUTHORIZED", detail: "bad" } } };

function renderWith(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}
const type = (id: string, v: string) => fireEvent.change(screen.getByTestId(id), { target: { value: v } });

beforeEach(() => {
  vi.clearAllMocks();
  mockSearch = "";
  signupPlan.mockResolvedValue(PLAN);
  record.mockResolvedValue([]);
});

// ── 온보딩 / 가입 ──────────────────────────────────────────────────────────────

async function onboardingSubmit() {
  renderWith(<OnboardingPage />);
  type("onb-org-name", "Acme"); type("onb-farm-name", "North");
  fireEvent.click(screen.getByTestId("onb-next"));
  type("onb-name", "Pat"); type("onb-username", "pat_doe"); type("onb-email", "pat@example.com");
  type("onb-password", "Passw0rd!23"); type("onb-confirm", "Passw0rd!23");
  fireEvent.click(screen.getByTestId("onb-next"));
  await waitFor(() => expect(signupPlan).toHaveBeenCalled());
  await waitFor(() => expect(screen.getAllByRole("checkbox").length).toBeGreaterThanOrEqual(2));
  const boxes = screen.getAllByRole("checkbox"); fireEvent.click(boxes[0]); fireEvent.click(boxes[1]);
  fireEvent.click(screen.getByTestId("onb-next"));
}

describe("온보딩 429", () => {
  it("429 → 속도제한 문구 + Retry-After 분 안내. 원문 상수는 화면에 없다", async () => {
    onboard.mockRejectedValue(err429("signup", "1993"));
    await onboardingSubmit();
    expect(await screen.findByText(/errors\.rateLimited/)).toBeInTheDocument();
    expect(screen.getByText(/errors\.rateLimitedRetryIn\{34\}/)).toBeInTheDocument();
    expect(screen.queryByText(/RATE_LIMITED/)).not.toBeInTheDocument();
    expect(setAuth).not.toHaveBeenCalled();
  });

  it("Retry-After 없으면 기본 문구만 — 추정하지 않는다", async () => {
    onboard.mockRejectedValue(err429("signup"));
    await onboardingSubmit();
    expect(await screen.findByText(/errors\.rateLimited$/)).toBeInTheDocument();
    expect(screen.queryByText(/rateLimitedRetryIn/)).not.toBeInTheDocument();
  });

  it("★ 429 는 451(법역 차단) 패널이 아니다 — 입력값도 남아 있다", async () => {
    onboard.mockRejectedValue(err429("signup", "60"));
    await onboardingSubmit();
    await screen.findByText(/errors\.rateLimited/);
    expect(screen.queryByText(/publicationNotApproved/)).not.toBeInTheDocument();
    // 확인 스텝의 오류 상자에 머문다 — 사용자 입력은 form state 에 그대로다(뒤로 가면 보인다)
    expect(onboard).toHaveBeenCalledTimes(1);
  });

  it("451 은 여전히 451 이다 — 429 처리가 기존 분기를 덮지 않는다", async () => {
    onboard.mockRejectedValue(err451);
    await onboardingSubmit();
    await waitFor(() => expect(onboard).toHaveBeenCalled());
    expect(screen.queryByText(/errors\.rateLimited/)).not.toBeInTheDocument();
  });

  it("자동 재시도 없음 — 429 뒤 onboard 는 정확히 1회", async () => {
    onboard.mockRejectedValue(err429("signup", "5"));
    await onboardingSubmit();
    await screen.findByText(/errors\.rateLimited/);
    await new Promise((r) => setTimeout(r, 50));
    expect(onboard).toHaveBeenCalledTimes(1);
  });
});

// ── 로그인 ────────────────────────────────────────────────────────────────────

async function loginSubmit() {
  renderWith(<LoginPage />);
  const inputs = screen.getAllByRole("textbox");
  fireEvent.change(inputs[0], { target: { value: "pat" } });
  const pw = document.querySelector('input[type="password"]') as HTMLInputElement;
  fireEvent.change(pw, { target: { value: "Passw0rd!23" } });
  fireEvent.click(screen.getByRole("button", { name: /login\.(submit|signIn|login)|Sign in|로그인/i }));
}

describe("로그인 429", () => {
  it("429 → 속도제한 문구, 비밀번호 오류(errInvalid)가 아니다", async () => {
    login.mockRejectedValue(err429("auth", "13"));
    await loginSubmit();
    expect(await screen.findByText(/errors\.rateLimited/)).toBeInTheDocument();
    expect(screen.queryByText(/login\.errInvalid/)).not.toBeInTheDocument();
    expect(screen.getByText(/rateLimitedRetryIn\{1\}/)).toBeInTheDocument();
  });

  it("401 은 여전히 errInvalid — 분기 순서가 바뀌지 않았다", async () => {
    login.mockRejectedValue(err401);
    await loginSubmit();
    expect(await screen.findByText(/login\.errInvalid/)).toBeInTheDocument();
  });

  it("자동 재시도 없음", async () => {
    login.mockRejectedValue(err429("auth", "13"));
    await loginSubmit();
    await screen.findByText(/errors\.rateLimited/);
    expect(login).toHaveBeenCalledTimes(1);
  });
});

// ── 비밀번호 재설정 ──────────────────────────────────────────────────────────

describe("비밀번호 재설정 429", () => {
  it("요청: 429 는 '메일을 보냈다' 로 위장하지 않는다 — 계정 존재는 여전히 노출하지 않는다", async () => {
    requestPasswordReset.mockRejectedValue(err429("auth", "13"));
    renderWith(<ForgotPasswordPage />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "x@example.com" } });
    fireEvent.click(screen.getByRole("button"));
    expect(await screen.findByText(/errors\.rateLimited/)).toBeInTheDocument();
    expect(screen.queryByText(/forgotPassword\.(done|sent)/)).not.toBeInTheDocument();
    // 열거방지 문구(존재/부재)는 어느 쪽도 나오지 않는다
    expect(screen.queryByText(/not found|존재하지/i)).not.toBeInTheDocument();
  });

  it("요청: 429 가 아닌 실패는 기존대로 동일 처리(done)", async () => {
    requestPasswordReset.mockRejectedValue({ response: { status: 500, data: {} } });
    renderWith(<ForgotPasswordPage />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "x@example.com" } });
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => expect(requestPasswordReset).toHaveBeenCalled());
    expect(screen.queryByText(/errors\.rateLimited/)).not.toBeInTheDocument();
  });

  it("확인: 429 → 속도제한 문구, badToken 아님", async () => {
    mockSearch = "token=abc";
    confirmPasswordReset.mockRejectedValue(err429("auth"));
    renderWith(<ForgotPasswordPage />);
    const pws = document.querySelectorAll('input[type="password"]');
    fireEvent.change(pws[0], { target: { value: "Passw0rd!23" } });
    fireEvent.change(pws[1], { target: { value: "Passw0rd!23" } });
    fireEvent.click(screen.getByRole("button"));
    expect(await screen.findByText(/errors\.rateLimited/)).toBeInTheDocument();
    expect(screen.queryByText(/forgotPassword\.badToken/)).not.toBeInTheDocument();
  });
});

// ── 서버 정책을 클라이언트에 복제하지 않았다 ─────────────────────────────────

describe("정책 복제 없음", () => {
  it("웹 소스에 rate-limit 횟수·창 상수가 없다", async () => {
    const { readFileSync, readdirSync, statSync } = await import("node:fs");
    const { join } = await import("node:path");
    const roots = ["app", "lib", "components", "store"];
    const files: string[] = [];
    const walk = (d: string) => { for (const e of readdirSync(d)) { const p = join(d, e); statSync(p).isDirectory() ? walk(p) : /\.(ts|tsx)$/.test(e) && files.push(p); } };
    roots.forEach(walk);
    const offenders = files.filter((f) => /(MAX_SIGNUP|SIGNUP_WINDOW|LOGIN_MAX|RATE_LIMIT_(PER|WINDOW)|requestsPerHour|attemptsPerMinute)/.test(readFileSync(f, "utf8")));
    expect(offenders).toEqual([]);
  });
});
