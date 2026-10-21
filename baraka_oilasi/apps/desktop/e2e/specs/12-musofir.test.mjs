// Musofir (M1, musofir/SPEC 2–4): Rustam aka, Koreya. Onboarding'da Musofir → sozlash (KRW, o'z ulushi
// 20 %, maqsad 120 mln so'm, qaytish 13 oydan keyin) → o'tgan 3 oy (maosh 2 600 000 von, jamg'armaga
// 520/500/540 ming, qolgani uyga) → shu oy: maosh (Ctrl+N) va ulush taklifi, xarajatlar, uyga 1 200 000 +
// komissiya → kurssiz so'mdagi qiymat yo'q → kurs 9,1: 54,6 mln, qaytishda 3 884 000 kam → ulush qo'yildi:
// qo'lda 215 000, maqsadga yetadi. Har bir ekran axe bilan.
import assert from "node:assert/strict";
import { after, afterEach, before, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard } from "../lib/flows.mjs";

const pad = (n) => String(n).padStart(2, "0");
const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/** `k` oy oldingi oyning 25-kuni (ISO). */
function monthsAgo(k) {
  const d = new Date();
  return iso(new Date(d.getFullYear(), d.getMonth() - k, 25));
}

/** Bugundan 13 oy keyingi xuddi shu kun — to'liq 13 oy (oy oxiri bo'lsa, oxirgi kun). */
function returnDate() {
  const d = new Date();
  const last = new Date(d.getFullYear(), d.getMonth() + 14, 0).getDate();
  return iso(new Date(d.getFullYear(), d.getMonth() + 13, Math.min(d.getDate(), last)));
}

/** Skrinshot uchun ish maydonining boshiga qaytish. */
async function top(app) {
  await app.b.execute(() => document.getElementById("main")?.scrollTo(0, 0));
}

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

async function waitValue(app, id, fragment) {
  await app.b.waitUntil(async () => (await app.text(id)).includes(fragment), { timeout: 15000, timeoutMsg: `${id}: ${fragment} yo'q` });
}

async function entry(app, action, { amount, date, category, fee, received, note }) {
  if (action) await app.click(action, await app.region("Yozuv qoʻshish"));
  const dialog = await app.x("//div[@role='dialog']");
  await app.type("Summa (KRW)", amount, dialog);
  if (category) await app.selectText("Kategoriya", category, dialog);
  if (fee) await app.type("Komissiya (KRW)", fee, dialog);
  if (received) await app.type("Uyda olingan summa (UZS)", received, dialog);
  if (date) await app.setDate("Sana (boʻsh — bugun)", date, dialog);
  if (note) await app.type("Izoh", note, dialog);
  await app.click("Saqlash", dialog);
  await dialog.waitForExist({ reverse: true });
}

describe("Musofir: o'z ulushi va qaytish jamg'armasi", () => {
  let app;
  before(async () => {
    app = await startApp();
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`mf-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("M1. onboarding: Musofir makoni va sozlash ustasi", async () => {
    await onboard(app, { household: "Rustam akaning oilasi", name: "Rustam", spaces: ["Musofir"], rhythm: "Oylik maosh" });
    await app.click("Musofir", await app.region("Makonlar"));
    const form = await app.region("Musofir makonini sozlash", "form");
    const nav = await (await app.b.$("nav")).getText();
    assert.ok(nav.includes("Bosh sahifa") && !nav.includes("Kelajagim"), nav);
    await app.type("Mamlakat", "Koreya", form);
    await app.selectText("Ish valyutasi", "Koreya voni (KRW)", form);
    assert.equal(await (await app.field("Oʻz ulushi (%)", form)).getValue(), "20");
    await app.type("Qaytish jamgʻarmasi maqsadi (soʻmda)", "120 000 000", form);
    await app.setDate("Qaytish sanasi (taxminiy)", returnDate(), form);
    await noAxe(app, "mf-setup");
    await app.shot("desktop-88-mf-setup");
    await app.click("Saqlash", form);
    await (await app.testId("mf-fund")).waitForDisplayed();
  });

  it("M2. o'tgan 3 oy: maosh, o'z ulushi jamg'armaga, qolgani uyga", async () => {
    await entry(app, "Qoʻldagi pul (boshlangʻich)", { amount: "150 000", date: monthsAgo(3) });
    await entry(app, "Jamgʻarma (boshlangʻich)", { amount: "4 440 000", date: monthsAgo(3) });
    for (const [k, fund, sent] of [
      [3, "520 000", "2 080 000"],
      [2, "500 000", "2 100 000"],
      [1, "540 000", "2 060 000"],
    ]) {
      await app.b.keys(["Control", "n"]);
      await entry(app, null, { amount: "2 600 000", date: monthsAgo(k) });
      // Taklif — keyinroq (o'tgan oylarni tarixdan kiritayapmiz).
      await app.click("Keyinroq");
      await entry(app, "Jamgʻarmaga", { amount: fund, date: monthsAgo(k) });
      await entry(app, "Uyga yuborish", { amount: sent, date: monthsAgo(k) });
    }
    await waitValue(app, "mf-fund", "6 000 000");
  });

  it("M3. shu oy: maosh va ulush taklifi, xarajat, uyga yuborish", async () => {
    await app.b.keys(["Control", "n"]);
    await entry(app, null, { amount: "2 600 000", note: "Zavod" });
    await waitValue(app, "mf-offer", "520 000 KRW");
    await noAxe(app, "mf-offer");
    await app.click("Keyinroq");
    for (const [category, amount] of [
      ["Turar joy ijarasi", "400 000"],
      ["Oziq-ovqat", "350 000"],
      ["Telefon va internet", "60 000"],
    ]) {
      await entry(app, "Xarajat", { amount, category });
    }
    await entry(app, "Uyga yuborish", { amount: "1 200 000", fee: "5 000", received: "10 900 000" });
    await waitValue(app, "mf-sent", "1 200 000");
    await waitValue(app, "mf-share-gap", "520 000");
    await (await app.testId("mf-warning-NO_SHARE")).waitForDisplayed();
    // Kurs yo'q — so'mdagi qiymat taxmin qilinmaydi.
    await app.waitText("Kurs kiritilmagan");
    assert.equal(await (await app.testId("mf-fund-home")).isExisting(), false);
  });

  it("M4. kurs 9,1: so'mda 54,6 mln, qaytishda 3 884 000 kam", async () => {
    const form = await app.region("Valyuta kursi", "form");
    await app.type("1 KRW necha UZS", "9,1", form);
    await app.type("Manba (bank, oʻtkazma ilovasi)", "Bank", form);
    await app.click("Kursni saqlash", form);
    await waitValue(app, "mf-fund-home", "54 600 000");
    await waitValue(app, "mf-fund-status", "3 884 000");
    await waitValue(app, "mf-projected", "116 116 000");
    await noAxe(app, "mf-home-behind");
    await top(app);
    await app.shot("desktop-89-mf-home-behind");
  });

  it("M5. ulush qo'yildi: qo'lda 215 000, maqsadga yetadi", async () => {
    await entry(app, "Jamgʻarmaga", { amount: "520 000" });
    await waitValue(app, "mf-fund", "6 520 000");
    await waitValue(app, "mf-pocket", "215 000");
    await waitValue(app, "mf-fund-status", "maqsadga yetasiz");
    assert.equal(await (await app.testId("mf-share-gap")).isExisting(), false);
    await noAxe(app, "mf-home-on-track");
    await top(app);
    await app.shot("desktop-90-mf-home-on-track");
  });
});
