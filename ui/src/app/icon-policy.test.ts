import { readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

// Testlar ui/ papkasidan ishga tushiriladi (pnpm -C ui test): manba papkasi shu yerdan topiladi.
const SRC_DIR = resolve(process.cwd(), "src");

/**
 * Taqiqlangan ikonkalar (feedback-islomiy-grafika): cho'chqa (piggy bank), bank binosi, odam va
 * hayvon tasvirlari, qimor, alkogol, din ramzlari, foiz belgisi va qo'l tasviri.
 * Ism to'liq moslanadi: masalan, «Banknote» (naqd pul) taqiqlanmagan.
 */
const FORBIDDEN_ICON =
  /^(PiggyBank|Landmark|Users?|UserRound|UserCheck|User|Baby|Dices?|Spade|Club|Beer|Wine|Martini|Church|Cross|Percent|Bird|Cat|Dog|Fish|Rabbit|Turtle|Bug|Handshake|Bitcoin)\d*$/;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      return sourceFiles(path);
    }
    const isAppSource = /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name);
    return isAppSource ? [path] : [];
  });
}

/** Fayl matnidan lucide-react'dan import qilingan ikonka nomlarini ajratib oladi. */
function lucideIconNames(source: string): string[] {
  const names: string[] = [];
  const importPattern = /import\s+(?:type\s+)?\{([^}]*)\}\s*from\s*["']lucide-react["']/g;

  for (const match of source.matchAll(importPattern)) {
    for (const specifier of (match[1] ?? "").split(",")) {
      const name = specifier
        .replace(/^\s*type\s+/, "")
        .split(/\s+as\s+/)[0]
        ?.trim();
      if (name) {
        names.push(name);
      }
    }
  }
  return names;
}

describe("ikonka siyosati", () => {
  it("taqiqlangan ikonkalar ishlatilmaydi", () => {
    const violations = sourceFiles(SRC_DIR).flatMap((file) =>
      lucideIconNames(readFileSync(file, "utf8"))
        .filter((name) => FORBIDDEN_ICON.test(name))
        .map((name) => `${file}: ${name}`),
    );

    expect(violations).toEqual([]);
  });

  it("navigatsiyaning barcha bo'limlari ikonkaga ega", () => {
    const navigationSource = readFileSync(join(SRC_DIR, "app", "navigation.ts"), "utf8");

    // 11 ta bo'lim + LucideIcon turi
    expect(lucideIconNames(navigationSource).length).toBeGreaterThanOrEqual(11);
  });
});
