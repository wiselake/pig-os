import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithClient } from "../test-utils";

// 설정→데이터·프라이버시: 목적별 (필요 버전, 기록 버전) + 철회/제외 액션. next-intl 전역 mock((k)=>k).
// ★ 입력은 GET /consent/diff 하나다. farms.list · signupPlan · current 는 부르지 않는다.
const REQ = "MASTER_TERMS@0.2+GLOBAL_PRIVACY_NOTICE@0.2";
const h = vi.hoisted(() => {
  const REQ = "MASTER_TERMS@0.2+GLOBAL_PRIVACY_NOTICE@0.2";
  const state = {
    activeFarmId: "f1" as string | null,
    items: [] as {
      purpose_code: string; required_version: string; recorded_version: string | null;
      recorded_status: string | null;
    }[],
  };
  return Object.assign(state, {
    withdraw: vi.fn(() => Promise.resolve({ purpose_code: "AI_MODEL_TRAINING", consent_status: "WITHDRAWN" })),
    farmsList: vi.fn(),
    signupPlan: vi.fn(),
    current: vi.fn(),
    diff: vi.fn(() => Promise.resolve({ any_draft: false, required_version: REQ, items: state.items })),
  });
});
const { farmsList, signupPlan, current, diff } = h;

vi.mock("@/store/auth.store", () => ({
  useAuthStore: (sel: (s: { activeFarmId: string | null }) => unknown) => sel({ activeFarmId: h.activeFarmId }),
}));
vi.mock("@/lib/api/endpoints/farms", () => ({ farmsApi: { list: h.farmsList } }));
vi.mock("@/lib/api/endpoints/consent", () => ({
  consentApi: { diff: h.diff, withdraw: h.withdraw, signupPlan: h.signupPlan, current: h.current },
}));

const baseItems = () => [
  { purpose_code: "SERVICE_OPERATION", required_version: REQ, recorded_version: REQ, recorded_status: "NOTICE_GIVEN" },
  { purpose_code: "AI_MODEL_TRAINING", required_version: REQ, recorded_version: "MASTER_TERMS@0.1+GLOBAL_PRIVACY_NOTICE@0.1", recorded_status: "GRANTED" },
  { purpose_code: "ANON_AGG_STATS", required_version: REQ, recorded_version: REQ, recorded_status: "EXCLUSION_REQUESTED" },
  { purpose_code: "NAMED_RESEARCH", required_version: REQ, recorded_version: null, recorded_status: null },
];

import DataPrivacyPage from "@/app/(app)/settings/data/page";

describe("DataPrivacyPage (설정 데이터·프라이버시)", () => {
  beforeEach(() => {
    h.activeFarmId = "f1";
    h.items = baseItems();
    h.withdraw.mockClear(); farmsList.mockClear(); signupPlan.mockClear(); current.mockClear(); diff.mockClear();
  });

  it("★ 국가는 서버가 정한다 — diff 만 부르고 farms.list · signupPlan · current 는 부르지 않는다", async () => {
    renderWithClient(<DataPrivacyPage />);
    await screen.findByText("purpose.SERVICE_OPERATION.label");
    expect(diff).toHaveBeenCalledWith("f1");
    expect(farmsList).not.toHaveBeenCalled();
    expect(signupPlan).not.toHaveBeenCalled();
    expect(current).not.toHaveBeenCalled();
  });

  it("목적마다 필요 버전과 기록 버전을 나란히 보여준다 — 판정은 하지 않는다", async () => {
    renderWithClient(<DataPrivacyPage />);
    await screen.findByText("purpose.AI_MODEL_TRAINING.label");
    // 바뀐 목적 하나에만 '동의 이후 변경됨' 표식, 기록 없는 목적엔 '기록 없음'
    expect(screen.getAllByText("diff.changed")).toHaveLength(1);
    expect(screen.getAllByText("diff.never")).toHaveLength(1);
    expect(screen.getAllByText("diff.required")).toHaveLength(4);
    // 계정 단위 판정 문구 같은 것은 없다
    expect(screen.queryByText(/reconsent|needs/i)).not.toBeInTheDocument();
  });

  it("visible 목적 라벨 렌더", async () => {
    renderWithClient(<DataPrivacyPage />);
    expect(await screen.findByText("purpose.SERVICE_OPERATION.label")).toBeInTheDocument();
    expect(screen.getByText("purpose.AI_MODEL_TRAINING.label")).toBeInTheDocument();
  });

  it("계약이행 목적(SERVICE_OPERATION)은 철회 불가 안내", async () => {
    renderWithClient(<DataPrivacyPage />);
    expect(await screen.findByText("action.contractRequired")).toBeInTheDocument();
  });

  it("GRANTED 옵트인은 철회 버튼 → 클릭 시 withdraw 호출, 이후 diff 를 다시 읽는다", async () => {
    renderWithClient(<DataPrivacyPage />);
    // AI_MODEL_TRAINING(GRANTED) 과 NAMED_RESEARCH(기록 없음) 둘 다 버튼이 있다 — 순서대로 첫 번째
    const [btn] = await screen.findAllByText("action.WITHDRAWN");
    fireEvent.click(btn);
    await waitFor(() =>
      expect(h.withdraw).toHaveBeenCalledWith({ purpose_code: "AI_MODEL_TRAINING", farm_id: "f1", action: "WITHDRAWN" }),
    );
    await waitFor(() => expect(diff.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it("이미 제외요청된 목적은 액션 버튼 없음", async () => {
    renderWithClient(<DataPrivacyPage />);
    await screen.findByText("purpose.ANON_AGG_STATS.label");
    // ANON_AGG_STATS 는 EXCLUSION_REQUESTED 상태 → 액션 버튼(action.EXCLUSION_REQUESTED) 미노출
    expect(screen.queryByText("action.EXCLUSION_REQUESTED")).not.toBeInTheDocument();
  });
});
