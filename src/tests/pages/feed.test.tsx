import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { feedApi } from "@/lib/api/endpoints/feed";

import { renderWithClient } from "../test-utils";

// 역할을 테스트마다 바꾸기 위해 hoisted 가변 홀더 사용(vi.mock 팩토리에서 참조).
const h = vi.hoisted(() => ({ role: "FARM_WORKER" }));

vi.mock("@/store/auth.store", () => ({
  useAuthStore: (sel: (s: { activeFarmId: string | null; user: { role: string } }) => unknown) =>
    sel({ activeFarmId: "farm-1", user: { role: h.role } }),
}));
const summaryMock = vi.hoisted(() => ({
  value: {
    farm_id: "farm-1", period: { start: "2026-08-01", end: "2026-08-31", grain: "calendar_month", partial: false },
    quantity_basis: "AS_RECORDED", currency: "USD", formula_version: "FEED_ENGINE.v1", no_data: false,
    metrics: {
      FEED_QTY: { value: 1500, unit: "kg", provenance: "ACTUAL", reason: null, evidence: {}, status: { status: "normal", reason: "no_policy" } },
      // 부분 원가 — 값은 null, 부분합은 evidence. 화면은 이것을 0 으로 그리면 안 된다.
      FEED_COST: { value: null, unit: "currency", provenance: "INSUFFICIENT", reason: "cost_incomplete",
                   evidence: { partial_cost: 1000, uncosted_rows: 1 }, status: { status: "insufficient", reason: "cost_incomplete" } },
      FEED_UNIT_PRICE: { value: 1, unit: "currency/kg", provenance: "DERIVED", reason: null, evidence: {}, status: null },
      FEED_MIX_SHARE: { value: 0.6667, unit: "ratio", provenance: "DERIVED", reason: null, evidence: { shares: { grower: 0.6667, finisher: 0.3333 }, dominant_type: "grower" }, status: null },
      FEED_QTY_CHANGE: { value: 600, unit: "kg", provenance: "DERIVED", reason: null, evidence: { comparison_grain: "calendar_month" }, status: null },
      FEED_COST_CHANGE: { value: null, unit: "currency", provenance: "INSUFFICIENT", reason: "cost_incomplete", evidence: {}, status: null },
    },
    findings: [{ rule_id: "feed.cost_incomplete", kpi: "FEED_COST", severity: "info", detail: {} }],
    provenance: { source_systems: ["pigos_manual"], contract_versions: [], rows: 2 },
  },
}));

vi.mock("@/lib/api/endpoints/farms", () => ({
  farmsApi: { get: vi.fn().mockResolvedValue({ id: "farm-1", currency: "KRW" }) },
}));
vi.mock("@/lib/api/endpoints/feed", () => ({
  feedApi: {
    list: vi.fn().mockResolvedValue([
      { id: "f1", record_date: "2026-06-01", feed_type: "비육", quantity_kg: 1200, unit_cost: null, currency: null },
    ]),
    create: vi.fn().mockResolvedValue({}),
    delete: vi.fn(),
    summary: vi.fn().mockImplementation(async () => summaryMock.value),
    months: vi.fn().mockResolvedValue([
      { period: "2026-07", quantity_basis: "AS_RECORDED", currency: "USD", rows: 1, feed_qty_kg: 900, feed_cost: 900, feed_cost_reason: null, partial_cost: null, unit_price: 1, dominant_type: "grower" },
      { period: "2026-08", quantity_basis: "AS_RECORDED", currency: "USD", rows: 2, feed_qty_kg: 1500, feed_cost: null, feed_cost_reason: "cost_incomplete", partial_cost: 1000, unit_price: 1, dominant_type: "grower" },
    ]),
  },
}));

import FeedPage from "@/app/(app)/feed/page";

describe("FeedPage 권한 게이팅 (H4)", () => {
  beforeEach(() => { h.role = "FARM_WORKER"; });

  it("WORKER에게는 삭제 버튼이 보이지 않는다 (백엔드 DELETE는 MANAGE 전용)", async () => {
    h.role = "FARM_WORKER";
    renderWithClient(<FeedPage />);
    // 레코드는 로드되어 표시됨
    expect(await screen.findByText("1200")).toBeInTheDocument();
    // 삭제 버튼(t("delete") → 키 "delete")은 없어야 함
    expect(screen.queryByText("delete")).not.toBeInTheDocument();
  });

  it("OWNER에게는 삭제 버튼이 보인다", async () => {
    h.role = "FARM_OWNER";
    renderWithClient(<FeedPage />);
    expect(await screen.findByText("1200")).toBeInTheDocument();
    expect(screen.getByText("delete")).toBeInTheDocument();
  });

  it("VIEWER에게는 입력 폼과 삭제 버튼 모두 없다", async () => {
    h.role = "VIEWER";
    renderWithClient(<FeedPage />);
    expect(await screen.findByText("1200")).toBeInTheDocument();
    expect(screen.queryByText("delete")).not.toBeInTheDocument();
    // 입력 폼 추가 버튼(t("add"))도 없음 (canEntry=false)
    expect(screen.queryByText("add")).not.toBeInTheDocument();
  });
});


describe("FeedPage 입력 폼 — 단가·통화 (P0 INPUT UX FIX)", () => {
  beforeEach(() => { h.role = "FARM_OWNER"; });

  it("단가·통화 필드가 있고, 단가를 비우면 currency 도 null 로 보낸다", async () => {
    renderWithClient(<FeedPage />);
    expect(await screen.findByText("1200")).toBeInTheDocument();
    expect(screen.getByLabelText("unitCost")).toBeInTheDocument();
    expect(screen.getByLabelText("currency")).toBeInTheDocument();
    fireEvent.change(screen.getAllByRole("spinbutton")[0], { target: { value: "4400" } });
    fireEvent.click(screen.getByText("save"));
    await screen.findByText("1200");
    expect(feedApi.create).toHaveBeenCalledWith("farm-1", expect.objectContaining({ quantity_kg: 4400, unit_cost: null, currency: null }));
  });

  it("단가를 넣으면 kg 당 단가와 농장 통화(기본값)를 보낸다", async () => {
    renderWithClient(<FeedPage />);
    await screen.findByText("1200");
    const inputs = screen.getAllByRole("spinbutton");
    fireEvent.change(inputs[0], { target: { value: "4400" } });
    fireEvent.change(screen.getByLabelText("unitCost"), { target: { value: "582" } });
    fireEvent.click(screen.getByText("save"));
    await screen.findByText("1200");
    expect(feedApi.create).toHaveBeenLastCalledWith("farm-1", expect.objectContaining({ unit_cost: 582, currency: "KRW" }));
  });
});

describe("FeedPage 월 결과 — null 은 0 이 아니다", () => {
  beforeEach(() => { h.role = "FARM_WORKER"; });

  it("수량·단가·전월대비를 그리고, 원가는 부분 금액 + 빠진 행 수로 표시한다(0 없음)", async () => {
    renderWithClient(<FeedPage />);
    const box = await screen.findByTestId("feed-summary");
    await waitFor(() => expect(box).toHaveTextContent("1,500"));
    expect(box).toHaveTextContent("+600");
    expect(box).toHaveTextContent("costPartial");        // t("costPartial", {n}) — 키 기반 렌더(테스트 i18n)
    expect(box).toHaveTextContent("grower 67%");
    expect(box.textContent).not.toMatch(/0 USD/);   // 부분원가를 0 으로 그리지 않는다
    expect(box).toHaveTextContent("1,000*");              // months 표의 부분원가 표기
  });

  it("행이 없는 달은 no_data 안내만 보인다", async () => {
    summaryMock.value = { ...summaryMock.value, no_data: true, metrics: {} };
    renderWithClient(<FeedPage />);
    const box = await screen.findByTestId("feed-summary");
    await waitFor(() => expect(box).toHaveTextContent("noDataMonth"));
    expect(box.textContent).not.toContain("+600");        // 카드 없음 — 월 표(이력)는 그대로 남는다
  });
});
