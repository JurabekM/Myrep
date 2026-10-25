// Haqiqiy desktop ilova ustida E2E: tauri-driver → WebKitWebDriver (Linux) / msedgedriver
// (Windows) → baraka-desktop. Har bir profil — alohida vaqtinchalik papka (toza baza).
//
// Talab: `pnpm --dir ../ui build` va `cargo build --features tauri/custom-protocol` (debug —
// `BARAKA_DEV_SHIFT_DAYS` va `BARAKA_E2E_FILES` faqat debug build'da ishlaydi), `tauri-driver`.
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { remote } from "webdriverio";

// Yadro «bugun»ni xonadon vaqt mintaqasida (standart Asia/Tashkent) hisoblaydi. Testdagi sanalar
// (`new Date()`) va ilova ham shu mintaqada bo'lsin — aks holda UTC 19:00–24:00 oralig'ida (tungi CI)
// sanalar bir kunga farq qiladi. Bu import'dan keyin yaratilgan barcha `Date` lar uchun amal qiladi.
process.env.TZ = process.env.BARAKA_E2E_TZ ?? "Asia/Tashkent";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../../../..");
const exe = process.platform === "win32" ? "baraka-desktop.exe" : "baraka-desktop";
export const APP = process.env.BARAKA_APP ?? join(root, "target", "debug", exe);
export const OUT = resolve(here, "..", ".out");
const require = createRequire(import.meta.url);
const AXE = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");

let port = 4444;

/** Yangi profil bilan ilovani ochadi. `shiftDays` — yadro soati (debug), `profile` — avvalgi profil. */
export async function startApp({ shiftDays = 0, profile } = {}) {
  const dir = profile ?? mkdtempSync(join(tmpdir(), "baraka-e2e-"));
  const files = join(dir, "files");
  mkdirSync(files, { recursive: true });
  mkdirSync(OUT, { recursive: true });
  const env = {
    ...process.env,
    XDG_DATA_HOME: join(dir, "data"),
    APPDATA: join(dir, "data"),
    LOCALAPPDATA: join(dir, "data"),
    HOME: join(dir, "home"),
    BARAKA_INSECURE_DEV_SECRET: "1",
    BARAKA_E2E_FILES: files,
    BARAKA_DEV_SHIFT_DAYS: String(shiftDays),
    WEBKIT_DISABLE_COMPOSITING_MODE: "1",
  };
  const myPort = port++;
  const nativePort = myPort + 100;
  // O'z jarayon guruhida (Linux/macOS): to'xtatishda tauri-driver bilan birga WebKitWebDriver va
  // ilovaning o'zi ham o'ladi — aks holda ular test runner'ning stderr quvurini ochiq ushlab,
  // `node --test` testlar tugagach ham chiqmaydi (tungi CI 6 soat osilib qoldi).
  const driver = spawn("tauri-driver", ["--port", String(myPort), "--native-port", String(nativePort)], {
    env,
    stdio: ["ignore", "ignore", "inherit"],
    detached: process.platform !== "win32",
  });
  await waitPort(myPort);
  const started = Date.now();
  const browser = await remote({
    hostname: "127.0.0.1",
    port: myPort,
    logLevel: "error",
    waitforTimeout: 15000,
    capabilities: { "tauri:options": { application: APP }, "wdio:enforceWebDriverClassic": true },
  });
  await browser.$("h1").waitForExist({ timeout: 30000 });
  const startupMs = Date.now() - started;
  const app = new App(browser, dir, files);
  app.startupMs = startupMs;
  app.stop = async () => {
    try {
      // WebKit localStorage'ni (til, shrift) diskka ~1 s kechikish bilan yozadi — darhol o'ldirilsa,
      // qayta ochilganda sozlama yo'qoladi (sekin CI runner'da).
      await sleep(1500);
      await browser.deleteSession();
    } finally {
      await stopTree(driver);
    }
  };
  return app;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Avval SIGTERM (ilova va WebKit o'zini yopib ulgursin), 3 s ichida chiqmasa — butun guruhga SIGKILL. */
async function stopTree(child) {
  const signal = (sig) => {
    try {
      if (process.platform !== "win32") process.kill(-child.pid, sig);
      else child.kill();
    } catch {
      child.kill(sig);
    }
  };
  const exited = new Promise((r) => (child.exitCode !== null || child.signalCode !== null ? r() : child.once("exit", r)));
  signal("SIGTERM");
  await Promise.race([exited, sleep(3000)]);
  if (process.platform !== "win32") signal("SIGKILL");
}

async function waitPort(p) {
  for (let i = 0; i < 50; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${p}/status`);
      if (r.ok) return;
    } catch {
      // hali ochilmagan
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`tauri-driver ${p} portda ochilmadi`);
}

/** Ekran bilan ishlash: ko'rinadigan o'zbekcha matn va yorliqlar bo'yicha (foydalanuvchi kabi). */
export { xq };

export class App {
  constructor(browser, dir, files) {
    this.b = browser;
    this.dir = dir;
    this.files = files;
  }

  /** Forma maydoni: `<label>` ichidagi yorliq matni yoki `aria-label` bo'yicha (foydalanuvchi kabi). */
  field(name, within) {
    const ctl = "(self::input or self::select or self::textarea)";
    const at = within ? "." : "";
    const xp = `(${at}//label[.//span[normalize-space()=${xq(name)}]]//*[${ctl}] | ${at}//*[${ctl} and @aria-label=${xq(name)}])[1]`;
    return (within ?? this.b).$(xp);
  }

  /** `type="date"` maydon: ko'rinishi lokalga bog'liq (WebKit), shuning uchun qiymat ISO bilan React orqali beriladi. */
  async setDate(name, iso, within) {
    const el = await this.field(name, within);
    await el.waitForDisplayed();
    await this.b.execute(
      (e, v) => {
        const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
        set.call(e, v);
        e.dispatchEvent(new Event("input", { bubbles: true }));
        e.dispatchEvent(new Event("change", { bubbles: true }));
      },
      el,
      iso,
    );
  }

  async type(name, value, within) {
    const el = await this.field(name, within);
    await el.waitForDisplayed();
    await el.clearValue();
    await el.setValue(value);
  }

  async selectText(name, text, within) {
    const el = await this.field(name, within);
    await el.waitForDisplayed();
    await el.selectByVisibleText(text);
  }

  /** Ota element: `role`/`aria-label` yoki XPath. */
  async region(ariaLabel, tag = "*") {
    const el = await this.b.$(`//${tag}[@aria-label=${xq(ariaLabel)}]`);
    await el.waitForDisplayed();
    return el;
  }

  /** XPath bo'yicha element (ko'rinishini kutadi). */
  async x(xpath) {
    const el = await this.b.$(xpath);
    await el.waitForDisplayed();
    return el;
  }

  /** Imzo maydoniga sichqoncha bilan chiziq chizadi (pointer down → bir necha move → up). */
  async draw(canvas) {
    await canvas.waitForDisplayed();
    const pts = [
      [-200, 10],
      [-120, -30],
      [-40, 25],
      [40, -20],
      [120, 30],
      [200, -5],
    ];
    let a = this.b.action("pointer", { parameters: { pointerType: "mouse" } }).move({ origin: canvas, x: pts[0][0], y: pts[0][1] }).down();
    for (const [x, y] of pts.slice(1)) a = a.move({ origin: canvas, x, y, duration: 80 }).pause(30);
    await a.up().perform();
  }

  /** Tugma: aniq matn yoki aria-label bo'yicha; `within` — ota element. */
  async button(text, within) {
    const scope = within ?? this.b;
    const xp = `.//button[normalize-space()=${xq(text)} or @aria-label=${xq(text)}]`;
    const el = await scope.$(within ? xp : xp.slice(1));
    await el.waitForClickable();
    return el;
  }

  async click(text, within) {
    await (await this.button(text, within)).click();
  }

  /** Radio/checkbox yoki boshqa elementni yorliq matni (bir qismi) bo'yicha bosish. */
  async choose(labelPart, within) {
    const xp = `.//label[contains(normalize-space(), ${xq(labelPart)})]`;
    const el = await (within ?? this.b).$(within ? xp : xp.slice(1));
    await el.waitForClickable();
    await el.click();
  }

  async select(name, value, within) {
    const el = await this.field(name, within);
    await el.selectByAttribute("value", value);
  }

  async nav(label) {
    await this.click(label, await this.b.$(`nav`));
  }

  testId(id) {
    return this.b.$(`[data-testid="${id}"]`);
  }

  async text(id) {
    const el = await this.testId(id);
    await el.waitForDisplayed();
    return el.getText();
  }

  async heading() {
    const h = await this.b.$("h1");
    await h.waitForDisplayed();
    return h.getText();
  }

  /** Matn ekranda paydo bo'lguncha kutadi. */
  async waitText(fragment, timeout = 15000) {
    await this.b.waitUntil(async () => (await this.b.$("body").getText()).includes(fragment), {
      timeout,
      timeoutMsg: `ekranda yo'q: ${fragment}`,
    });
  }

  async bodyText() {
    return this.b.$("body").getText();
  }

  async shot(name) {
    await this.b.saveScreenshot(join(OUT, `${name}.png`));
  }

  /**
   * Haqiqiy webview'da axe-core (WCAG 2.x A/AA, kontrast ham — bu yerda ranglar hisoblanadi).
   * Natija: `qoida: element` qatorlari.
   */
  async axe() {
    // Strict CSP (`unsafe-eval` yo'q) sahifada `new Function`ni taqiqlaydi; WebDriver skripti esa
    // CSP'dan tashqarida bajariladi — axe manbasi shu skript tanasining o'zida.
    await this.b.execute(`${AXE}\n;window.axe = axe;`);
    return this.b.executeAsync((done) => {
      window.axe
        .run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] } })
        .then((r) => done(r.violations.flatMap((v) => v.nodes.map((n) => `${v.id}: ${n.target.join(" ")} ${n.failureSummary ?? ""}`.slice(0, 300)))))
        .catch((e) => done([`axe xatosi: ${e}`]));
    });
  }

  /** E2E papkasiga yozilgan oxirgi fayl nomlari. */
  saved() {
    return readdirSync(this.files);
  }

  writeNote(name, text) {
    writeFileSync(join(OUT, name), text);
  }
}

/** XPath satri (qo'shtirnoq va apostroflar bilan ham). */
function xq(s) {
  if (!s.includes('"')) return `"${s}"`;
  if (!s.includes("'")) return `'${s}'`;
  return `concat(${s
    .split('"')
    .map((p) => `"${p}"`)
    .join(`, '"', `)})`;
}
