// @vitest-environment node
/**
 * 아이콘 스케일 가드 — `lib/ui/icon.ts` 의 규율을 강제한다.
 *
 * ## 왜
 *
 * 이모지를 lucide 아이콘으로 바꾸는 것만으로는 품질이 올라가지 않는다.
 * 2026-09-09 실측에서 `size={}` 가 16종, `strokeWidth` 가 10종이었고, 크기를
 * `className="w-4 h-4"` 로 주는 경로가 따로 13건 있었다. 아이콘으로 통일해 놓고도
 * 같은 줄의 두 아이콘이 1px 씩 어긋나 있었다.
 *
 * 이 파일은 그 축이 다시 벌어지는 것을 막는다. 값을 늘려야 하면 `icon.ts` 의
 * 스케일을 고치고 여기 상수를 함께 옮긴다 — 호출부에 리터럴을 흘리지 않는다.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { ICON, STROKE } from "../lib/ui/icon";

const SRC = resolve(__dirname, "..");
const ROOTS = ["app", "components"];
const SKIP_DIR = new Set(["node_modules", ".next", "dist", "build", "coverage"]);

const SIZES = new Set<number>(Object.values(ICON));
const STROKES = new Set<number>(Object.values(STROKE));

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
    else if (/\.tsx?$/.test(name)) out.push(full);
  }
  return out;
}

const FILES = ROOTS.flatMap((r) => walk(join(SRC, r)));

function scan(pattern: RegExp, keep: (value: number, line: string) => boolean): string[] {
  const offenders: string[] = [];
  for (const full of FILES) {
    const rel = relative(SRC, full).replace(/\\/g, "/");
    readFileSync(full, "utf-8")
      .split("\n")
      .forEach((line, i) => {
        for (const m of line.matchAll(pattern)) {
          const value = Number(m[m.length - 1]);
          if (!keep(value, line)) offenders.push(`${rel}:${i + 1}: ${m[0]}  |  ${line.trim().slice(0, 60)}`);
        }
      });
  }
  return offenders;
}

describe("icon scale", () => {
  it("scans a non-trivial number of files", () => {
    // 스캔이 조용히 0건이 되면 가드가 통과하는 게 아니라 사라진 것이다.
    expect(FILES.length).toBeGreaterThan(50);
  });

  it("every size={} comes from the ICON scale", () => {
    expect(scan(/size=\{(\d+(?:\.\d+)?)\}/g, (v) => SIZES.has(v))).toEqual([]);
  });

  it("every strokeWidth={} comes from the STROKE set", () => {
    // 기본값(2)은 애초에 명시하지 않는 것이 규율이지만, 명시했다면 집합 안이어야 한다.
    expect(scan(/strokeWidth=\{(\d+(?:\.\d+)?)\}/g, (v) => STROKES.has(v))).toEqual([]);
  });

  it("icon size is not set through w-N h-N classes", () => {
    // lucide 의 size 는 width·height 를 함께 잡는다. 클래스 방식은 위 스케일 검사에
    // 잡히지 않아 조용히 빠져나간다.
    const offenders: string[] = [];
    for (const full of FILES) {
      const rel = relative(SRC, full).replace(/\\/g, "/");
      readFileSync(full, "utf-8")
        .split("\n")
        .forEach((line, i) => {
          for (const m of line.matchAll(/<([A-Z]\w+)\s+className="w-\d+ h-\d+"/g)) {
            offenders.push(`${rel}:${i + 1}: ${m[0]}`);
          }
        });
    }
    expect(offenders).toEqual([]);
  });
});
