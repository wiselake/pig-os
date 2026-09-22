// @vitest-environment node
/**
 * 이모지 회귀 가드 (R7) — 소스 전체에 picto 이모지·저품질 글리프가 없어야 한다.
 *
 * 표준 아이콘 시스템 = lucide-react. 텍스트에 글리프를 섞지 않는다:
 * 문자열 안의 "✓"는 색·크기·정렬을 못 잡고, 8개 로케일에 같은 글리프가 복제되며,
 * 스크린리더가 읽는다. 아이콘은 컴포넌트로 렌더하고 `aria-hidden` 을 붙인다.
 *
 * ★ 2026-09-09 — 파일 목록 방식에서 전수 스캔으로 교체.
 *   기존 가드는 9개 파일만 검사해서 admin/·support·messages 가 통째로 새어 있었다.
 *   실측 결과 107줄이 걸렸다. 목록은 새 화면이 생길 때마다 뒤처진다.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";

import { describe, expect, it } from "vitest";

const SRC = resolve(__dirname, "..");
const ROOTS = ["app", "components", "lib", "messages", "store", "hooks", "i18n"];
const EXT = /\.(tsx?|jsx?|json|css)$/;
const SKIP_DIR = new Set(["node_modules", ".next", "dist", "build", "coverage"]);

/**
 * 금지 문자.
 * - picto 이모지 전 범위(U+1F300~1FAFF, U+2600~27BF, 국기)
 * - 텍스트에 섞이던 저품질 글리프: ✓ ✔ ✕ ✖ ★ ☆ ⚠
 * 의도된 기호는 대상이 아니다 — → ← ⌘ · × — ○ ● 등.
 */
const BANNED =
  /[\u{1F300}-\u{1FAFF}\u{1F1E6}-\u{1F1FF}\u{2600}-\u{27BF}\u{2713}\u{2714}\u{2715}\u{2716}\u{2605}\u{2606}\u{26A0}]/u;

/**
 * 주석을 걷어낸 코드 부분만 남긴다 — 코드 주석의 ★ 는 UI 가 아니다.
 * 후행 주석(`return; // ★ …`)도 대상이므로 줄 시작만 보면 안 된다.
 * 앞에 공백이 있는 `//` 만 자른다 → `https://` 는 살아남는다.
 */
function codePart(line: string): string {
  const s = line.trim();
  if (s.startsWith("//") || s.startsWith("*") || s.startsWith("/*")) return "";
  return line.replace(/\s\/\/.*$/, "");
}

function walk(dir: string, out: string[] = []): string[] {
  let entries: string[];
  try {
    entries = readdirSync(dir);
  } catch {
    return out;
  }
  for (const name of entries) {
    if (SKIP_DIR.has(name)) continue;
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (EXT.test(name)) out.push(full);
  }
  return out;
}

const FILES = ROOTS.flatMap((r) => walk(join(SRC, r)));

describe("emoji regression guard", () => {
  it("scans a non-trivial number of files", () => {
    // 스캔이 조용히 0건이 되면 가드가 통과하는 게 아니라 사라진 것이다.
    expect(FILES.length).toBeGreaterThan(50);
  });

  it("no picto emoji or low-quality glyph in source", () => {
    const offenders: string[] = [];
    for (const full of FILES) {
      const rel = relative(SRC, full).replace(/\\/g, "/");
      const lines = readFileSync(full, "utf-8").split("\n");
      lines.forEach((line, i) => {
        const code = codePart(line);
        if (BANNED.test(code)) offenders.push(`${rel}:${i + 1}: ${line.trim().slice(0, 70)}`);
      });
    }
    expect(offenders).toEqual([]);
  });
});
