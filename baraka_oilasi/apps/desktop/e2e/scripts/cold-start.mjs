// Sovuq start: ilova jarayoni ishga tushirilgandan UI'ning birinchi IPC chaqiruvigacha (sahifa
// yuklangan, React ishga tushgan, qulf/sozlash ekrani chizilmoqda). Release build bilan:
//   node scripts/cold-start.mjs [binar] [marta]
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const bin = process.argv[2] ?? resolve(import.meta.dirname, "../../../../target/release/baraka-desktop");
const runs = Number(process.argv[3] ?? 5);
const profile = mkdtempSync(join(tmpdir(), "baraka-cold-"));

function once() {
  return new Promise((ok, fail) => {
    const t0 = performance.now();
    const p = spawn(bin, [], {
      env: { ...process.env, BARAKA_STARTUP_TRACE: "1", XDG_DATA_HOME: join(profile, "data"), APPDATA: join(profile, "data"), HOME: join(profile, "home") },
      stdio: ["ignore", "ignore", "pipe"],
    });
    const timer = setTimeout(() => {
      p.kill();
      fail(new Error("15 s ichida UI ishga tushmadi"));
    }, 15000);
    let buf = "";
    p.stderr.on("data", (d) => {
      buf += String(d);
      const m = /startup_ms=(\d+)\n/.exec(buf);
      if (m) {
        clearTimeout(timer);
        const wall = Math.round(performance.now() - t0);
        p.kill();
        p.on("exit", () => ok({ wall, inside: Number(m[1]) }));
      }
    });
  });
}

const results = [];
for (let i = 0; i < runs; i++) results.push(await once());
const walls = results.map((r) => r.wall).sort((a, b) => a - b);
console.log(results.map((r, i) => `${i + 1}: ${r.wall} ms (jarayon ichida ${r.inside} ms)`).join("\n"));
console.log(`birinchi (sovuq): ${results[0].wall} ms; mediana: ${walls[Math.floor(walls.length / 2)]} ms`);
