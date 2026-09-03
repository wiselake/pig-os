import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithClient } from "../test-utils";

// next-intl/next-navigation은 setup 전역 mock((k)=>k). auth/consent/farms만 개별 mock.
const h = vi.hoisted(() => ({
  activeFarmId: "f1" as string | null,
  accessToken: "tok" as string | null,
  farms: [{ id: "f1", country: "KR" }] as { id: string; country: string }[],
  current: [{ notice_version: "MASTER_TERMS@0.1" }] as { notice_version: string | null }[],
  planVersion: "MASTER_TERMS@0.2",
}));

vi.mock("@/store/auth.store", () => ({
  useAuthStore: (sel: (s: { activeFarmId: string | null; accessToken: string | null }) => unknown) =>
    sel({ activeFarmId: h.activeFarmId, accessToken: h.accessToken }),
}));
vi.mock("@/lib/api/endpoints/farms", () => ({
  farmsApi: { list: vi.fn(() => Promise.resolve(h.farms)) },
}));
vi.mock("@/lib/api/endpoints/consent", () => ({
  consentApi: {
    current: vi.fn(() => Promise.resolve(h.current)),
    signupPlan: vi.fn(() => Promise.resolve({ notice_version: h.planVersion })),
  },
}));

import AmendmentBanner from "@/components/consent/AmendmentBanner";

describe("AmendmentBanner (개정 재고지)", () => {
  beforeEach(() => {
    h.activeFarmId = "f1";
    h.accessToken = "tok";
    h.farms = [{ id: "f1", country: "KR" }];
    h.current = [{ notice_version: "MASTER_TERMS@0.1" }];
    h.planVersion = "MASTER_TERMS@0.2";
  });

  it("기록 버전 != 현재 문서 버전이면 배너 노출", async () => {
    renderWithClient(<AmendmentBanner />);
    expect(await screen.findByText("amendment.title")).toBeInTheDocument();
    expect(screen.getByText("amendment.review")).toBeInTheDocument();
  });

  it("버전 일치면 아무것도 렌더 안 함(null)", async () => {
    h.planVersion = "MASTER_TERMS@0.1"; // current와 동일 → outdated=false
    renderWithClient(<AmendmentBanner />);
    await waitFor(() => expect(screen.queryByText("amendment.title")).not.toBeInTheDocument());
  });

  it("닫기 버튼 클릭 시 배너 사라짐", async () => {
    renderWithClient(<AmendmentBanner />);
    const title = await screen.findByText("amendment.title");
    expect(title).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("dismiss"));
    expect(screen.queryByText("amendment.title")).not.toBeInTheDocument();
  });
});

// ── CHARACTERIZATION — 이 배너가 다루지 **않는** 것 ─────────────────────────
//
// `LEGAL_P0_MANDATORY_CONSENT_LOGIN_GATE.md` 는 "AmendmentBanner 는 게이트가
// 아니다" 라고 적었다. 문서에 주장만 적어두면 몇 달 뒤 누군가 "동의 배너가
// 있으니 커버된다" 고 오해한다. 그 주장을 여기서 실제 동작으로 고정한다.
//
// ★ 아래는 결함 재현이 아니라 **경계 확인**이다. 배너는 설계상 "동의가 낡았을
//   때"의 고지이며, "동의가 아예 없을 때"나 "강제"는 처음부터 범위 밖이다.
//   범위를 넓히는 것은 LEGAL-P0-MANDATORY-CONSENT-LOGIN-GATE 의 일이다.
describe("AmendmentBanner 경계 (게이트가 아님)", () => {
  beforeEach(() => {
    h.activeFarmId = "f1";
    h.accessToken = "tok";
    h.farms = [{ id: "f1", country: "KR" }];
    h.current = [{ notice_version: "MASTER_TERMS@0.1" }];
    h.planVersion = "MASTER_TERMS@0.2";
  });

  it("동의 기록이 0행이면 배너가 뜨지 않는다 — 프로덕션 원장이 정확히 이 상태다", async () => {
    // AmendmentBanner.tsx:44  `if (!current?.length || !plan) return false`
    // 동의를 한 번도 남기지 않은 사용자에게는 아무 표시도 없다. 즉 원장 0행
    // 상태를 이 배너로는 절대 발견할 수 없다.
    h.current = [];
    renderWithClient(<AmendmentBanner />);
    await waitFor(() => expect(screen.queryByText("amendment.title")).not.toBeInTheDocument());
  });

  it("notice_version 이 null 인 기록만 있어도 배너가 뜨지 않는다", async () => {
    // 버전을 남기지 못한 행은 비교 대상이 되지 못한다(`c.notice_version &&`).
    // 증빙이 부실할수록 오히려 조용해진다.
    h.current = [{ notice_version: null }];
    renderWithClient(<AmendmentBanner />);
    await waitFor(() => expect(screen.queryByText("amendment.title")).not.toBeInTheDocument());
  });

  it("닫기는 기록되지 않는다 — 다시 마운트하면 그대로 다시 뜬다", async () => {
    // dismissed 는 컴포넌트 로컬 state 다. 서버에 "고지했고 사용자가 확인했다"는
    // 흔적이 남지 않는다 — 고지 이행의 증거로 쓸 수 없다는 뜻이다.
    const first = renderWithClient(<AmendmentBanner />);
    await screen.findByText("amendment.title");
    fireEvent.click(screen.getByLabelText("dismiss"));
    expect(screen.queryByText("amendment.title")).not.toBeInTheDocument();
    first.unmount();

    renderWithClient(<AmendmentBanner />);
    expect(await screen.findByText("amendment.title")).toBeInTheDocument();
  });

  it("배너는 아무것도 막지 않는다 — 링크 하나뿐, 차단 UI 가 없다", async () => {
    // 게이트라면 진행을 막는 요소가 있어야 한다. 실제로는 설정으로 가는 링크와
    // 닫기 버튼뿐이다. 강제 재동의는 법무 판정 후 별도 계층의 일이다.
    renderWithClient(<AmendmentBanner />);
    await screen.findByText("amendment.title");
    const review = screen.getByText("amendment.review");
    expect(review.closest("a")).toHaveAttribute("href", "/settings/data");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
