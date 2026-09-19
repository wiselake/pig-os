/**
 * Node 버전 PREFLIGHT — 테스트 실행 전에 환경을 검사한다.
 *
 * ## 왜
 *
 * 2026-09-09 실측: 이 저장소는 `engines.node ">=22.12.0 <23"` 을 선언하고
 * `.nvmrc` 에 22.23.2 를 적어두고도, 실제로는 v20.11.1 위에서 돌고 있었다.
 * 선언은 있는데 **아무도 강제하지 않았다.**
 *
 * 그 결과가 조용하지 않았다.
 *   v20.11.1  → vitest 기동 자체가 안 됨
 *   v22.11.0  → jsdom 38건이 "테스트 실패" 처럼 보임 (실제로는 require(esm) 기본값 문제)
 * 후자를 덮으려고 `NODE_OPTIONS=--experimental-require-module` 이 test 스크립트에
 * 들어가 있었다. 버전 불일치를 플래그로 가린 것이다.
 *
 * ## 이 스크립트가 지키는 구분
 *
 * **환경이 틀린 것과 코드가 틀린 것은 다른 사건이다.**
 * 환경 실패는 종료 코드 78 로 나간다 — vitest 의 실패 코드(1)와 겹치지 않으므로
 * CI·RUN 게이트가 "테스트 실패"로 오탐하지 않는다.
 */
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

/** 환경 부적합. 테스트 실패(1)와 구분되어야 하므로 별도 코드를 쓴다. */
const EXIT_ENVIRONMENT_INVALID = 78;

const here = dirname(fileURLToPath(import.meta.url));
const pkg = JSON.parse(readFileSync(resolve(here, "..", "package.json"), "utf-8"));
const range = pkg.engines?.node;

if (!range) {
  console.error("ENVIRONMENT_INVALID: package.json has no engines.node to check against.");
  process.exit(EXIT_ENVIRONMENT_INVALID);
}

const parse = (v) => v.trim().replace(/^v/, "").split(".").map(Number);
const cmp = (a, b) => {
  for (let i = 0; i < 3; i++) {
    const x = a[i] ?? 0;
    const y = b[i] ?? 0;
    if (x !== y) return x < y ? -1 : 1;
  }
  return 0;
};

/**
 * `>=22.12.0 <23` 형태만 지원한다 — 이 저장소가 쓰는 문법이 그것뿐이다.
 * 해석할 수 없는 범위를 만나면 통과시키지 않는다. 검사할 수 없는 것을
 * 통과로 처리하면 가드가 있으나 마나가 된다(fail-closed).
 */
function satisfies(version, spec) {
  const v = parse(version);
  for (const clause of spec.trim().split(/\s+/)) {
    const m = /^(>=|>|<=|<|=)?(\d+(?:\.\d+)?(?:\.\d+)?)$/.exec(clause);
    if (!m) return { ok: false, reason: `unsupported range syntax: "${clause}"` };
    const [, op = "=", target] = m;
    const c = cmp(v, parse(target));
    const ok =
      op === ">=" ? c >= 0 : op === ">" ? c > 0 : op === "<=" ? c <= 0 : op === "<" ? c < 0 : c === 0;
    if (!ok) return { ok: false, reason: null };
  }
  return { ok: true, reason: null };
}

const actual = process.versions.node;
const { ok, reason } = satisfies(actual, range);

if (!ok) {
  console.error(
    reason
      ? `ENVIRONMENT_INVALID: cannot evaluate engines.node "${range}" — ${reason}`
      : `ENVIRONMENT_INVALID: node ${actual} not in engines ${range}. Run \`nvm use\`.`,
  );
  process.exit(EXIT_ENVIRONMENT_INVALID);
}

// NODE_OPTIONS 로 덮어 쓰던 과거를 되돌리지 않도록 함께 본다.
if ((process.env.NODE_OPTIONS ?? "").includes("--experimental-require-module")) {
  console.error(
    "ENVIRONMENT_INVALID: NODE_OPTIONS=--experimental-require-module is set.\n" +
      "  It was a workaround for node < 22.12 and is no longer needed. Unset it.",
  );
  process.exit(EXIT_ENVIRONMENT_INVALID);
}
