import { readFileSync } from "fs";
import { resolve } from "path";

import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, screen, waitFor } from "@testing-library/react";

import { renderWithClient } from "../test-utils";

// D-15a · Q-0 · B-1 · 기획서 v0.2 §4·§6 — 입고 영역은 서버 판정만 따른다.
const h = vi.hoisted(() => ({
  sources: null as unknown,
  summary: null as unknown,
  months: [] as unknown[],
}));

vi.mock("@/lib/api/endpoints/feed", () => ({
  feedApi: {
    sources: vi.fn().mockImplementation(async () => h.sources),
    summary: vi.fn().mockImplementation(async () => h.summary),
    months: vi.fn().mockImplementation(async () => h.months),
  },
}));

import { feedApi } from "@/lib/api/endpoints/feed";
import DeliveredArea from "@/components/feed/DeliveredArea";

// 부정 단언("그리지 않는다·요청하지 않는다")은 sources 응답이 렌더에 반영되고 뒤따르는 쿼리가 시작될 시간을 준 뒤에 한다.
// 이것 없이 단언하면 컴포넌트가 무엇을 하든 통과한다(W6 음성 증명 M30 이 그렇게 통과했다).
async function settle() {
  await waitFor(() => expect(feedApi.sources).toHaveBeenCalled());
  await act(async () => { await new Promise((r) => setTimeout(r, 60)); });
}

const VISIBLE = (rows: number, status = "SUCCEEDED") => ({
  as_recorded: { rows: 0 },
  delivered: { visibility: "REFERENCE_VISIBLE", rows, last_sync: { completed_at: "2026-09-23T00:20:00+00:00", watermark_to: null }, latest_run_status: status },
});
const HIDDEN = { as_recorded: { rows: 0 }, delivered: { visibility: "HIDDEN", rows: null, last_sync: null, latest_run_status: null } };
const SUMMARY = (partial = false) => ({
  farm_id: "farm-1", period: { start: "2026-08-01", end: "2026-08-31", grain: "calendar_month", partial },
  quantity_basis: "DELIVERED", currency: "KRW", formula_version: "FEED_ENGINE.v1", no_data: false, findings: [],
  provenance: { source_systems: ["pigplan"], contract_versions: [], rows: 3 },
  metrics: {
    FEED_QTY: { value: 691900, unit: "kg", provenance: "ACTUAL", reason: null, evidence: {}, status: null },
    FEED_COST: { value: null, unit: "currency", provenance: "INSUFFICIENT", reason: "cost_incomplete",
                 evidence: { partial_cost: 264917590, coverage_rows: 0.8333 }, status: null },
    FEED_UNIT_PRICE: { value: 600.1, unit: "currency/kg", provenance: "DERIVED", reason: null, evidence: {}, status: null },
    FEED_MIX_SHARE: { value: 0.62, unit: "ratio", provenance: "DERIVED", reason: null, evidence: { shares: { grower: 0.62, finisher: 0.38 } }, status: null },
    FEED_QTY_CHANGE: partial
      ? { value: null, unit: "kg", provenance: "INSUFFICIENT", reason: "partial_period", evidence: {}, status: null }
      : { value: 33140, unit: "kg", provenance: "DERIVED", reason: null, evidence: {}, status: null },
  },
});

describe("DeliveredArea — 서버 판정만 따른다", () => {
  beforeEach(() => {
    vi.mocked(feedApi.summary).mockClear();
    vi.mocked(feedApi.months).mockClear();
    h.summary = SUMMARY();
    h.months = [];
  });

  it("HIDDEN 이면 아무것도 그리지 않고 입고 요약을 요청하지도 않는다", async () => {
    h.sources = HIDDEN;
    renderWithClient(<DeliveredArea farmId="farm-1" period="2026-08" />);
    await settle();
    expect(screen.queryByTestId("feed-area-delivered")).toBeNull();
    expect(feedApi.summary).not.toHaveBeenCalled();
    expect(feedApi.months).not.toHaveBeenCalled();
  });

  it("응답 조작: 서버가 HIDDEN 이면 요약 응답에 데이터가 있어도 그리지 않는다", async () => {
    h.sources = HIDDEN;
    h.summary = SUMMARY();                                    // 누가 요약을 채워 둬도
    renderWithClient(<DeliveredArea farmId="farm-1" period="2026-08" />);
    await settle();
    expect(document.body.textContent).not.toContain("691,900");
  });

  it("노출이어도 입고 행이 0 이면(매핑 42 중 33 농장) 영역이 없다 — 0 kg 로 그리지 않는다", async () => {
    h.sources = VISIBLE(0);
    renderWithClient(<DeliveredArea farmId="farm-1" period="2026-08" />);
    await settle();
    expect(screen.queryByTestId("feed-area-delivered")).toBeNull();
    expect(feedApi.summary).not.toHaveBeenCalled();
  });

  it("노출 + 행 있음: 제목·배송 기준·데이터 기준일·입고량, 원가는 부분합이 아니라 '일부만 있음(행 %)'", async () => {
    h.sources = VISIBLE(3);
    renderWithClient(<DeliveredArea farmId="farm-1" period="2026-08" />);
    const box = await screen.findByTestId("feed-area-delivered");
    await waitFor(() => expect(box).toHaveTextContent("691,900"));
    expect(box).toHaveTextContent("delivered.title");
    expect(box).toHaveTextContent("delivered.basis");
    expect(screen.getByTestId("feed-delivered-asof")).toHaveTextContent("delivered.asOf");
    expect(box).toHaveTextContent("delivered.costPartial");
    expect(box.textContent).not.toContain("264,917,590");       // 부분합을 입고비로 쓰지 않는다
    expect(box).toHaveTextContent("+33,140");                  // 완료월 비교
    expect(box.textContent).not.toMatch(/benchmark|FCR/i);
  });

  it("진행 중인 달: MTD 배지, 비교 없음", async () => {
    h.sources = VISIBLE(3);
    h.summary = SUMMARY(true);
    renderWithClient(<DeliveredArea farmId="farm-1" period="2026-09" />);
    await screen.findByTestId("feed-delivered-mtd");
    expect(screen.getByTestId("feed-area-delivered").textContent).not.toContain("mChange");
  });

  it("마지막 동기화가 실패여도 값은 남기고 실패를 표시한다", async () => {
    h.sources = VISIBLE(3, "SOURCE_UNAVAILABLE");
    renderWithClient(<DeliveredArea farmId="farm-1" period="2026-08" />);
    await waitFor(() => expect(screen.getByTestId("feed-area-delivered")).toHaveTextContent("691,900"));
    expect(screen.getByTestId("feed-delivered-asof")).toHaveTextContent("delivered.syncFailed");
  });
});

describe("DeliveredArea 소스 — 클라이언트는 노출을 스스로 판정하지 않는다", () => {
  const src = readFileSync(resolve("components/feed/DeliveredArea.tsx"), "utf8");
  it("국가·관할·시장으로 판정하는 코드가 없다", () => {
    expect(src).not.toMatch(/\b(country|jurisdiction|market|region)\b/);
  });
  it("벤치마크 없음", () => {
    expect(src.replace(/\/\/.*$/gm, "")).not.toMatch(/benchmark/i);
  });
});
