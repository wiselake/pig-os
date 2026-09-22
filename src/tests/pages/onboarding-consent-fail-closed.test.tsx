/**
 * LEGAL-P0-WEB-CONSENT-FAIL-CLOSED — 동의 기록이 성공해야 가입이 성립한다.
 *
 * ## 왜 생겼나 (2026-09-03 실측)
 *
 * 이전 onboarding/page.tsx 는 이랬다.
 *
 *     setAuth(...); document.cookie = "pigos_session=1"; router.replace("/")
 *     if (consentState && planStatus === "ready") {
 *       try { await consentApi.record(...) } catch { }      ← 삼킴
 *     }
 *
 * 순서와 try/catch 둘 다 문제였다. plan 을 못 받아도, record 가 422/451/5xx 여도,
 * 네트워크가 끊겨도 사용자는 대시보드에 들어갔고 DB 에는 org·user·farm 만 남고
 * consent_ledger 는 비었다. 프로덕션 원장이 0행인 유력한 경로가 이것이다.
 *
 * ## 이 파일이 잠그는 계약
 *
 *     동의 기록 성공  →  setAuth · persistent cookie · 대시보드 진입
 *     그 외 전부      →  셋 다 없음 + 사용자에게 오류
 *
 * ★ "선택 목적 전부 OFF" 는 실패가 아니다. 필수 약관·개인정보만 필수다.
 *   그것까지 막으면 옵트인이 옵트인이 아니게 된다 — 아래에서 함께 고정한다.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { SignupPlan } from "@/types/api.types";

const setAuth = vi.fn();
const replace = vi.fn();
const onboard = vi.fn();
const signupPlan = vi.fn();
const record = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), refresh: vi.fn(), back: vi.fn(), forward: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/onboarding",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
vi.mock("next-intl", () => ({
  useTranslations: () => (k: string) => k,   // 키 그대로 → 문구 변경에 테스트가 흔들리지 않는다
  useLocale: () => "en",
}));
vi.mock("@/lib/api/endpoints/auth", () => ({
  authApi: { onboard: (...a: unknown[]) => onboard(...a), countries: () => Promise.resolve([]) },
}));
vi.mock("@/lib/api/endpoints/consent", () => ({
  consentApi: {
    signupPlan: (...a: unknown[]) => signupPlan(...a),
    record: (...a: unknown[]) => record(...a),
  },
}));
vi.mock("@/store/auth.store", () => ({
  useAuthStore: (sel: (s: { setAuth: typeof setAuth }) => unknown) => sel({ setAuth }),
}));
vi.mock("@/lib/analytics", () => ({ track: vi.fn(), identifyUser: vi.fn() }));

import OnboardingPage from "@/app/onboarding/page";

const PLAN: SignupPlan = {
  jurisdiction: { code: "US", country: "US", group: "US", counsel_review: false, notes: [] },
  gate: { signup_blocked: false, paid_blocked: false, release_hold: false, reason_code: null },
  state_flags: {
    state: null, written_opt_in_required: false, do_not_sell_link: false,
    honor_uoom: false, exclude_location_from_sale: false,
  },
  documents: [
    { doc_id: "MASTER_TERMS", kind: "master", version: "0.1", status: "DRAFT_LAWYER_PENDING",
      lang: "en", is_legal_priority: true, lang_pending: false, body: null },
  ],
  notice_version: "MASTER_TERMS@0.1",
  any_draft: true,
  lang_gate: false,
  required_acks: ["TERMS", "PRIVACY"],
  purposes: [
    { purpose_code: "SERVICE_OPERATION", order: 0, ui_kind: "NOTICE", lawful_basis: "CONTRACT",
      visible: true, is_toggle: false, default_on: false, requires_evidence: false,
      status_tag: "LEGAL_REQUIREMENT", auto_off_if_uoom: false },
    // 선택 목적 — 끄고 가입해도 정상이어야 한다
    { purpose_code: "AI_MODEL_TRAINING", order: 1, ui_kind: "OPT_IN", lawful_basis: "CONSENT",
      visible: true, is_toggle: true, default_on: false, requires_evidence: true,
      status_tag: null, auto_off_if_uoom: false },
  ],
  lang: "en",
};

const ONBOARD_OK = {
  user_id: "u-1", farm_id: "f-1", access_token: "AT-temp", refresh_token: "RT-1",
};

function axiosErr(status: number, detail?: string) {
  return { response: { status, data: detail ? { detail } : {} } };
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}><OnboardingPage /></QueryClientProvider>);
}

const type = (id: string, v: string) =>
  fireEvent.change(screen.getByTestId(id), { target: { value: v } });

/** step 0·1 을 채우고 확인 스텝까지 이동. */
async function goToReviewStep() {
  renderPage();
  type("onb-org-name", "Acme");
  type("onb-farm-name", "North");
  fireEvent.click(screen.getByTestId("onb-next"));
  type("onb-name", "Pat");
  type("onb-username", "pat_doe");
  type("onb-email", "pat@example.com");
  type("onb-password", "Passw0rd!23");
  type("onb-confirm", "Passw0rd!23");
  fireEvent.click(screen.getByTestId("onb-next"));
  await waitFor(() => expect(signupPlan).toHaveBeenCalled());
}

/** 필수 약관·개인정보 동의 체크. */
async function ackMandatory() {
  await waitFor(() => expect(screen.getAllByRole("checkbox").length).toBeGreaterThanOrEqual(2));
  const boxes = screen.getAllByRole("checkbox");
  fireEvent.click(boxes[0]);
  fireEvent.click(boxes[1]);
}

const submit = () => fireEvent.click(screen.getByTestId("onb-next"));

/** ★ 실패 시 절대 일어나면 안 되는 3가지. */
function expectNoSignupCompletion() {
  expect(setAuth).not.toHaveBeenCalled();
  expect(replace).not.toHaveBeenCalled();
  expect(document.cookie).not.toContain("pigos_session=1");
}

beforeEach(() => {
  vi.clearAllMocks();
  document.cookie = "pigos_session=; path=/; max-age=0";
  onboard.mockResolvedValue(ONBOARD_OK);
  signupPlan.mockResolvedValue(PLAN);
  record.mockResolvedValue([]);
});

// ── 1. 정상 경로 — 기존 계약 유지 ───────────────────────────────────────────

describe("정상 가입", () => {
  it("record 성공 후에야 setAuth·쿠키·대시보드 진입이 일어난다", async () => {
    await goToReviewStep();
    await ackMandatory();
    submit();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
    expect(record).toHaveBeenCalledTimes(1);
    expect(setAuth).toHaveBeenCalledTimes(1);
    expect(document.cookie).toContain("pigos_session=1");
  });

  it("동의 기록은 auth store 가 아니라 방금 받은 토큰으로 호출된다", async () => {
    // store 에 아직 저장하지 않으므로 인터셉터가 쓸 토큰이 없다 —
    // 명시 주입이 빠지면 401 로 원장이 다시 비게 된다.
    await goToReviewStep();
    await ackMandatory();
    submit();

    await waitFor(() => expect(record).toHaveBeenCalled());
    expect(record.mock.calls[0][1]).toBe("AT-temp");
    const body = record.mock.calls[0][0] as Record<string, unknown>;
    expect(body).toMatchObject({
      farm_id: "f-1", selected_country: "US", farm_country: "US",
      lang: "en", terms_ack: true, privacy_ack: true, collection_context: "UI_SIGNUP",
    });
  });

  it("선택 목적을 전부 OFF 로 둬도 가입은 정상 완료된다", async () => {
    // 옵트인을 사실상 강제하지 않는다는 계약.
    await goToReviewStep();
    await ackMandatory();   // 선택 토글은 건드리지 않는다
    submit();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
    const choices = (record.mock.calls[0][0] as { choices: { granted: boolean }[] }).choices;
    expect(choices.every((c) => c.granted === false)).toBe(true);
  });
});

// ── 2. 필수 동의 미체크 → 제출 자체가 불가 ──────────────────────────────────

describe("필수 동의 미체크", () => {
  it("약관·개인정보를 체크하지 않으면 제출 버튼이 비활성", async () => {
    await goToReviewStep();
    await waitFor(() => expect(screen.getAllByRole("checkbox").length).toBeGreaterThanOrEqual(2));
    expect(screen.getByTestId("onb-next")).toBeDisabled();
    expect(onboard).not.toHaveBeenCalled();
  });

  it("한쪽만 체크해도 여전히 비활성", async () => {
    await goToReviewStep();
    await waitFor(() => expect(screen.getAllByRole("checkbox").length).toBeGreaterThanOrEqual(2));
    fireEvent.click(screen.getAllByRole("checkbox")[0]);
    expect(screen.getByTestId("onb-next")).toBeDisabled();
  });
});

// ── 3. plan 을 못 받으면 계정을 만들지도 않는다 ─────────────────────────────

describe("plan unavailable", () => {
  it("plan 조회 실패 시 제출 불가 — 고아 계정을 만들지 않는다", async () => {
    // ★ 이전에는 canProceed 가 `return true` 였다. 서버에 org·user·farm 만
    //   만들어 놓고 동의는 못 받는 상태가 실제로 가능했다.
    signupPlan.mockRejectedValue(axiosErr(500));
    await goToReviewStep();

    await waitFor(() => expect(screen.getByTestId("onb-consent-plan-error")).toBeInTheDocument());
    expect(screen.getByTestId("onb-next")).toBeDisabled();
    submit();
    expect(onboard).not.toHaveBeenCalled();
    expectNoSignupCompletion();
  });

  it("안내 문구는 messages 파일에서 온다 — 인라인 로케일 분기 없음", async () => {
    signupPlan.mockRejectedValue(axiosErr(500));
    await goToReviewStep();
    await waitFor(() =>
      expect(screen.getByTestId("onb-consent-plan-error")).toHaveTextContent("consentPlanUnavailable"));
  });
});

// ── 4. record 실패 — 전부 fail-closed ───────────────────────────────────────

describe.each([
  ["422 검증 실패", axiosErr(422, "INVALID_CONSENT_PAYLOAD"), "INVALID_CONSENT_PAYLOAD"],
  ["451 국가 차단", axiosErr(451, "SIGNUP_BLOCKED:HOLD_D07"), "SIGNUP_BLOCKED:HOLD_D07"],
  ["500 서버 오류", axiosErr(500), "consentRecordFailed"],
  ["네트워크 단절", new Error("Network Error"), "consentRecordFailed"],
])("동의 기록 실패 — %s", (_label, err, expectedMessage) => {
  it("가입이 완료되지 않고 사유가 표시된다", async () => {
    record.mockRejectedValue(err);
    await goToReviewStep();
    await ackMandatory();
    submit();

    await waitFor(() => expect(record).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText(expectedMessage as string)).toBeInTheDocument());
    expectNoSignupCompletion();
  });
});

// ── 5. 가입 자체가 막히면 동의 API 를 부르지 않는다 ─────────────────────────

describe("/onboarding/complete 실패", () => {
  it("451 이면 consent record 를 호출하지 않는다", async () => {
    // 서버 국가 게이트(LEGAL-P0-CONSENT-AUTHORITY)가 먼저 막는 경우.
    onboard.mockRejectedValue(axiosErr(451, "SIGNUP_BLOCKED:HOLD_D07"));
    await goToReviewStep();
    await ackMandatory();
    submit();

    await waitFor(() => expect(screen.getByText("SIGNUP_BLOCKED:HOLD_D07")).toBeInTheDocument());
    expect(record).not.toHaveBeenCalled();
    expectNoSignupCompletion();
  });
});

// ── 6. 차단 법역은 확인 스텝에서 이미 막힌다 ────────────────────────────────

describe("차단 법역", () => {
  it("signup_blocked plan 이면 필수 체크를 해도 제출 불가", async () => {
    signupPlan.mockResolvedValue({
      ...PLAN,
      gate: { signup_blocked: true, paid_blocked: false, release_hold: false, reason_code: "HOLD_D07" },
    });
    await goToReviewStep();
    await waitFor(() => expect(screen.getByTestId("onb-next")).toBeDisabled());
    submit();
    expect(onboard).not.toHaveBeenCalled();
    expectNoSignupCompletion();
  });
});


// ── 게시 미승인(G-3) — 오류가 아니라 안내다 ─────────────────────────────────

describe("게시 문서 미승인", () => {
  const rejectWith = (detail: string) => ({ response: { data: { detail } } });

  it("451 PUBLICATION_NOT_APPROVED 는 원문 코드가 아니라 안내 문구로 나온다", async () => {
    onboard.mockRejectedValue(rejectWith("PUBLICATION_NOT_APPROVED"));
    await goToReviewStep();
    await ackMandatory();
    submit();

    await waitFor(() => expect(screen.getByText("publicationNotApproved")).toBeInTheDocument());
    expect(screen.getByText("publicationNotApprovedTitle")).toBeInTheDocument();
    // ★ 이것이 이 테스트의 요점 — 사용자에게 영문 코드가 보이면 장애로 읽힌다.
    expect(screen.queryByText(/PUBLICATION_NOT_APPROVED/)).not.toBeInTheDocument();
    expectNoSignupCompletion();
  });

  it("다른 451(SIGNUP_BLOCKED) 은 기존대로 서버 사유를 그대로 보여준다", async () => {
    onboard.mockRejectedValue(rejectWith("SIGNUP_BLOCKED:KR_REFERENCE_ONLY"));
    await goToReviewStep();
    await ackMandatory();
    submit();

    // 안내 패널로 삼키지 않는다 — 국가 차단은 별개 사유이고 계약이 이미 있다.
    await waitFor(() =>
      expect(screen.getByText("SIGNUP_BLOCKED:KR_REFERENCE_ONLY")).toBeInTheDocument(),
    );
    expect(screen.queryByText("publicationNotApproved")).not.toBeInTheDocument();
    expectNoSignupCompletion();
  });
});
