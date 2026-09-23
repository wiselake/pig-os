import { existsSync, readdirSync, readFileSync } from "fs";
import { join, resolve } from "path";

import { describe, it, expect } from "vitest";

// B-2 (2026-09-23): PigPlan 데이터는 DELIVERED — 입고·구매·배송이다. 입고 영역(feed.delivered.*)의 문구와 코드는
// 급여·섭취·소비·FCR 로 읽히면 안 된다. FCR 은 CONSUMED / GROUP_ATTRIBUTED 계열 데이터가 생겼을 때만 연결한다(D-15b 보류).
const LOCALES = ["en", "ko", "zh", "es", "vi", "th", "pt", "ru"] as const;
const ALL = /FCR|feed\s*conversion/i;
const FORBIDDEN: Record<(typeof LOCALES)[number], RegExp> = {
  en: /consum|intake|\bfed\b|feeding/i,
  ko: /급여|섭취|소비/,
  zh: /采食|消耗|饲喂|料肉比/,
  es: /consum|ingesta|alimentad|suministrad/i,
  vi: /tiêu thụ|cho ăn|ăn vào/i,
  th: /การบริโภค|ให้อาหาร|กินได้/,
  pt: /consum|ingest|fornecid|alimentad/i,
  ru: /потреблен|скармлив|конверси/i,
};

type Msgs = { feed: { fedTitle: string; delivered: Record<string, string> } };
const load = (l: string): Msgs => JSON.parse(readFileSync(resolve("messages", `${l}.json`), "utf8"));

describe("B-2 입고 영역 문구 — 급여·소비·FCR 표현 0", () => {
  for (const l of LOCALES) {
    it(`${l}: feed.delivered.* 에 금지 표현이 없다`, () => {
      const d = load(l).feed.delivered;
      expect(Object.keys(d).length).toBeGreaterThan(0);
      const hits = Object.entries(d).filter(([, v]) => ALL.test(v) || FORBIDDEN[l].test(v));
      expect(hits).toEqual([]);
    });

    it(`${l}: 검사식이 빈 껍데기가 아니다 — 급여 영역 제목(fedTitle)에는 걸린다`, () => {
      expect(FORBIDDEN[l].test(load(l).feed.fedTitle)).toBe(true);
    });
  }
});

// 입고 화면·API 클라이언트 코드에 효율 지표 경로가 없다 (영역 A 컴포넌트는 components/feed/ 아래에 둔다)
const CODE = [
  "app/(app)/feed/page.tsx",
  "lib/api/endpoints/feed.ts",
  ...(existsSync(resolve("components/feed"))
    ? readdirSync(resolve("components/feed")).map((f) => join("components/feed", f))
    : []),
];
const METRIC_PATH = /["'`](FCR|FEED_COST_PER_KG_GAIN|FEED_QTY_PER_HEAD|FEED_COST_PER_PIG|ADG)["'`]|\bfcr\s*\(/;

describe("B-2 입고·사료 화면 코드 — FCR 계열 지표 경로 0", () => {
  for (const f of CODE) {
    it(`${f}`, () => {
      const src = readFileSync(resolve(f), "utf8");
      const lines = src.split("\n").map((ln, i) => [i + 1, ln] as const).filter(([, ln]) => METRIC_PATH.test(ln));
      expect(lines).toEqual([]);
    });
  }
});
