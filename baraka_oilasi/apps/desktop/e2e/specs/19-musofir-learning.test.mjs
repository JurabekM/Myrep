// Musofir «O'zimga sarmoya» (M6, musofir/SPEC 6A), haqiqiy ilovada. Bobur aka (Koreya, KRW): o'tgan 3 oy —
// 2 600 000 / 2 600 000 + 150 000 boshqa daromad / 2 600 000 von, joriy oy 2 700 000, kurs 1 KRW = 9,1 so'm
// → chet eldagi xarajat 135 000 «Sarmoya (o'qish)» belgisi bilan (oy hisobida alohida qator, 5 %) →
// «Hunardan ishga»da «Payvandlash ustaxonasi» → bir soati 12 045 von (10 soat × 22 kun), so'mda faqat kurs
// bilan ≈ 109 609,50 → ikki maqsadli rejalar: uyda — payvandlash (g'oyaga bog'langan), chet elda — ish
// joyidagi koreys tili; 3-faol reja — chegara → «Ilm zakoti»: hamyurtiga hujjatlar bo'yicha yordam →
// kurs tekshiruvi «chet elda ish kafolati» savoli bilan — qizil. Har ekran axe bilan.
import assert from "node:assert/strict";
import { after, afterEach, before, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard } from "../lib/flows.mjs";

const pad = (n) => String(n).padStart(2, "0");
const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/** `k` oy oldingi oyning `day`-kuni (ISO). */
function monthsAgo(k, day = 10) {
  const d = new Date();
  return iso(new Date(d.getFullYear(), d.getMonth() - k, day));
}

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

async function waitValue(app, id, fragment) {
  await app.b.waitUntil(async () => (await app.text(id)).includes(fragment), { timeout: 15000, timeoutMsg: `${id}: ${fragment} yo'q` });
}

async function scrollTo(app, selector, block = "start") {
  await app.b.execute((s, b) => document.querySelector(s)?.scrollIntoView({ block: b }), selector, block);
}

/** Musofir yozuvi: `action` — tugma (yo'q bo'lsa Ctrl+N — maosh). */
async function entry(app, action, { amount, date, invest = false }) {
  if (action) await app.click(action, await app.region("Yozuv qoʻshish"));
  else await app.b.keys(["Control", "n"]);
  const dialog = await app.x("//div[@role='dialog']");
  await app.type("Summa (KRW)", amount, dialog);
  if (date) await app.setDate("Sana (boʻsh — bugun)", date, dialog);
  if (invest) await app.choose("Sarmoya (oʻqish)", dialog);
  await app.click("Saqlash", dialog);
  await dialog.waitForExist({ reverse: true });
  // Daromaddan keyin o'z ulushi taklifi — bu sinovda keyinroq.
  if (!action || action === "Boshqa daromad") await app.click("Keyinroq");
}

describe("Musofir: Oʻzimga sarmoya", () => {
  let app;
  before(async () => {
    app = await startApp();
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`mfl-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("L1. sozlash, 3 oy daromad, kurs, «Sarmoya» belgili xarajat va «Hunardan ishga» g'oyasi", async () => {
    await onboard(app, { household: "Bobur akaning oilasi", name: "Bobur", spaces: ["Musofir"], rhythm: "Oylik maosh" });
    await app.click("Musofir", await app.region("Makonlar"));
    const form = await app.region("Musofir makonini sozlash", "form");
    await app.selectText("Ish valyutasi", "Koreya voni (KRW)", form);
    await app.click("Saqlash", form);
    await (await app.testId("mf-fund")).waitForDisplayed();
    for (const k of [3, 2, 1]) await entry(app, null, { amount: "2 600 000", date: monthsAgo(k) });
    await entry(app, "Boshqa daromad", { amount: "150 000", date: monthsAgo(2, 20) });
    await entry(app, null, { amount: "2 700 000", date: monthsAgo(0, 1) });
    const rate = await app.region("Valyuta kursi", "form");
    await app.type("1 KRW necha UZS", "9,1", rate);
    await app.click("Kursni saqlash", rate);
    await (await app.testId("mf-rate")).waitForDisplayed();

    await entry(app, "Xarajat", { amount: "135 000", invest: true });
    await waitValue(app, "mf-self-investment", "135 000 KRW");
    const row = await app.x("//tr[.//td[@data-testid='mf-self-investment']]");
    assert.match(await row.getText(), /shundan «Sarmoya \(oʻqish\)».*5 %/s);
    await noAxe(app, "mf-self-investment");

    await app.click("«Hunardan ishga»ni ochish", await app.region("Qaytgandan keyin ish", "section"));
    await app.click("Yangi gʻoya");
    const idea = await app.region("Gʻoya hisobi", "form");
    await app.type("Gʻoya nomi", "Payvandlash ustaxonasi", idea);
    await app.type("1-narsa", "Payvandlash apparati", idea);
    await app.type("1-narsa narxi", "12 000 000", idea);
    for (const label of ["Oylik kirim", "Oylik xarajat"]) {
      const inputs = await idea.$$(`.//label[.//span[normalize-space()='${label}']]//input`);
      for (const [i, el] of inputs.entries()) {
        await el.setValue(label === "Oylik kirim" ? ["5 000 000", "7 000 000", "9 000 000"][i] : "4 000 000");
      }
    }
    await app.click("Hisoblash va saqlash", idea);
    await idea.waitForExist({ reverse: true });
    await app.click("Musofir", await app.region("Makonlar"));
  });

  it("L2. bir soatim: 12 045 von, soʻmda faqat kurs bilan ≈ 109 609,50", async () => {
    await app.nav("Oʻzimga sarmoya");
    const card = await app.testId("mfl-hour");
    await card.waitForDisplayed();
    await waitValue(app, "mfl-months", "2 750 000 KRW");
    assert.match(await card.getText(), /Hali hisoblanmagan/);
    await app.click("Hisoblash va saqlash", card);
    await waitValue(app, "mfl-hour-value", "12 045 KRW");
    await waitValue(app, "mfl-hour-double", "24 090 KRW");
    const home = await app.testId("mfl-hour-home");
    assert.match(await home.getText(), /≈ 109 609,50 soʻm \/ soat/);
    assert.match(await home.getText(), /1 KRW = 9,1 UZS/);
    assert.match(await app.text("mfl-hour"), /oxirgi oylar oʻrtachasi \(3 oy\)/);
    assert.match(await app.text("mfl-self-investment"), /135 000 KRW — daromadning 5 %/);
    await noAxe(app, "mf-learning-hour");
    await scrollTo(app, '[data-testid="mfl-hour"]');
    await app.shot("desktop-110-mf-learning-hour");
  });

  it("L3. ikki maqsad: uyda — g'oyaga bog'langan, chet elda — til; 3-faol reja chegarada", async () => {
    await app.click("Yangi reja");
    let dialog = await app.region("Yangi bilim rejasi");
    await app.choose("uyda daromad beradigan hunar", dialog);
    await app.type("Koʻnikma", "Payvandlash", dialog);
    const select = await app.field("«Hunardan ishga» gʻoyasi (ixtiyoriy)", dialog);
    await select.waitUntil(async () => (await select.getText()).includes("Payvandlash ustaxonasi"), { timeout: 15000, timeoutMsg: "g'oya yo'q" });
    await select.selectByIndex(1);
    await app.choose("Ustoz", dialog);
    await app.type("Haftasiga soat", "4", dialog);
    await noAxe(app, "mf-plan-dialog");
    await app.click("Rejani ochish", dialog);
    await dialog.waitForExist({ reverse: true });
    await app.waitText("Gʻoya: Payvandlash ustaxonasi");

    for (const [skill, path] of [
      ["Ish joyidagi koreys tili", "Kurs"],
      ["Forklift guvohnomasi", "Kurs"],
    ]) {
      await app.click("Yangi reja");
      dialog = await app.region("Yangi bilim rejasi");
      await app.type("Koʻnikma", skill, dialog);
      await app.choose(path, dialog);
      await app.type("Haftasiga soat", "3", dialog);
      await app.click("Rejani ochish", dialog);
      if (skill.startsWith("Forklift")) {
        await app.b.waitUntil(async () => (await dialog.getText()).includes("koʻpi bilan 2 ta faol reja"), { timeout: 15000, timeoutMsg: "chegara xatosi yo'q" });
        await app.click("Bekor qilish", dialog);
      }
      await dialog.waitForExist({ reverse: true });
    }
    const abroad = await app.region("Bilim rejasi: Ish joyidagi koreys tili");
    assert.match(await abroad.getText(), /Chet elda/);
    assert.match(await abroad.getText(), /Boshlangʻich nuqta: 12 045 KRW \/ soat/);
    await noAxe(app, "mf-learning-plans");
    await scrollTo(app, '[aria-label="Bilim rejasi: Payvandlash"]');
    await app.shot("desktop-111-mf-learning-plans");
  });

  it("L4. «Ilm zakoti» — hujjatlar bo'yicha yordam; kurs tekshiruvi chet eldagi ish kafolati bilan", async () => {
    await app.click("Oʻrgatganimni yozish");
    const d = await app.region("Ilm zakoti: oʻrgatish yozuvi");
    await app.click("Hujjatlar", d);
    await app.type("Nimani oʻrgatdi", "Yashash kartasi hujjatlari", d);
    await app.type("Kimga (ixtiyoriy): ism yoki «yangi kelgan hamyurt»", "Yangi kelgan hamyurt", d);
    await app.click("Saqlash", d);
    await d.waitForExist({ reverse: true });
    await waitValue(app, "mfl-teach-count", "1 marta");
    await app.waitText("kimga: Yangi kelgan hamyurt");

    await app.click("Kursni tekshirish", await app.region("Bilim rejasi: Ish joyidagi koreys tili"));
    const dialog = await app.x("//div[@role='dialog']");
    const groups = await dialog.$$(".//div[@role='radiogroup']");
    assert.equal(groups.length, 9);
    const answers = ["Yoʻq", "Yoʻq", "Yoʻq", "Ha", "Ha", "Yoʻq", "Yoʻq", "Ha", "Ha"];
    for (const [i, g] of groups.entries()) await app.choose(answers[i], g);
    assert.match(await groups[8].getText(), /Kursdan keyin chet elda ish kafolatlanyaptimi\?/);
    await app.click("Tekshirish", dialog);
    const r = await app.testId("offer-result");
    await r.waitForDisplayed();
    assert.match(await r.getText(), /Qizil: pul toʻlamang/);
    assert.match(await r.getText(), /chet elda ish vaʼda qilinmoqda/);
    await noAxe(app, "mf-course-check");
    await app.b.execute(() => document.querySelector('[data-testid="offer-result"]')?.scrollIntoView({ block: "center" }));
    await app.shot("desktop-112-mf-course-check");
  });
});
