// «O'zimga sarmoya» (U16c, uy/SPEC 2G). Bekzod: daromad 12 000 000 → «Bir soatim
// qancha?»: qo'lda 10 296 000, kuniga 11 soat, 26 kun → 36 000 so'm, ikki barobar maqsad 72 000,
// soat chegarasi eslatmasi → bilim rejalari: «Elektr montaj asoslari» (kurs + amaliyot,
// byudjet 1 500 000) va «Buxgalteriya»; uchinchisi — 2 ta faol reja chegarasi → 1 soat 30 daqiqa
// o'qish → xarajat «O'zimga sarmoya» belgisi bilan rejaga bog'lanadi: sarflandi 1 200 000,
// daromadning 10 % → kurs tekshiruvi: daromad kafolati — qizil → «Ilm zakoti» → natija: yangi
// hisobsiz — xabar; 12 870 000 bilan qayta hisob → 45 000, farq 9 000 (25 %).
import assert from "node:assert/strict";
import { after, afterEach, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard } from "../lib/flows.mjs";

const PLAN1 = "Elektr montaj asoslari";

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

async function waitIn(app, el, fragment) {
  await app.b.waitUntil(async () => (await el.getText()).includes(fragment), { timeout: 15000, timeoutMsg: `yo'q: ${fragment}` });
}

async function answer(app, dialog, question, reply) {
  const group = await dialog.$(`.//div[@role='radiogroup'][.//p[contains(., "${question}")]]`);
  await group.waitForDisplayed();
  await app.choose(reply, group);
}

async function newPlan(app, skill, paths, { budget, hours } = {}) {
  await app.click("Yangi reja");
  const d = await app.region("Yangi bilim rejasi");
  await app.type("Koʻnikma", skill, d);
  for (const p of paths) await app.choose(p, d);
  if (budget) await app.type("Byudjet (ixtiyoriy)", budget, d);
  await app.type("Haftasiga soat", hours ?? "3", d);
  await app.click("Rejani ochish", d);
  return d;
}

describe("O'zimga sarmoya", () => {
  let app;
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`learn-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("L1. daromad va «Bir soatim qancha?» — soat chegarasi eslatmasi", async () => {
    app = await startApp();
    await onboard(app, { rhythm: "Oylik maosh" });
    await app.b.keys(["Control", "n"]);
    await app.type("Summa", "12 000 000");
    await app.type("Manba", "Taksi");
    await app.click("Saqlash");
    await app.click("Bu safar emas");
    await app.b.$('[role="dialog"]').waitForExist({ reverse: true });

    await app.nav("Oʻzimga sarmoya");
    const card = await app.region("Bir soatim qancha? — Bekzod", "section");
    await waitIn(app, card, "Hali hisoblanmagan");
    await app.type("Oylik daromad (boʻsh — avtomatik)", "10 296 000", card);
    await app.type("Kuniga soat", "11", card);
    await app.type("Kuniga daqiqa", "0", card);
    await app.type("Oyda ish kunlari", "26", card);
    await app.click("Hisoblash va saqlash", card);
    await waitIn(app, card, "36 000 soʻm");
    assert.match(await (await card.$('[data-testid="hour-double"]')).getText(), /72 000 soʻm/);
    assert.match(await card.getText(), /qoʻlda kiritilgan/);
    assert.match(await card.getText(), /Oyiga ish vaqti: 286 soat/);
    assert.match(await (await card.$('[data-testid="hour-ceiling"]')).getText(), /Soatni yana koʻpaytirish oʻrniga/);
    await noAxe(app, "learning-hour");
    await app.b.execute(() => document.querySelector('[aria-label="Bir soatim qancha? — Bekzod"]')?.scrollIntoView({ block: "start" }));
    await app.shot("desktop-104-learning-hour");
  });

  it("L2. bilim rejalari: ikkitasi ochiladi, uchinchisi — 2 ta faol reja chegarasi", async () => {
    let d = await newPlan(app, PLAN1, ["Kurs", "Amaliyot"], { budget: "1 500 000" });
    await d.waitForExist({ reverse: true });
    const card = await app.region(`Bilim rejasi: ${PLAN1}`, "section");
    await waitIn(app, card, "Byudjet: 1 500 000 soʻm · sarflandi: 0 soʻm");
    assert.match(await card.getText(), /Boshlangʻich nuqta: 36 000 soʻm \/ soat/);
    d = await newPlan(app, "Buxgalteriya", ["Kitob"]);
    await d.waitForExist({ reverse: true });
    d = await newPlan(app, "Ingliz tili", ["Ustoz"]);
    await waitIn(app, d, "koʻpi bilan 2 ta faol reja");
    await noAxe(app, "learning-plan-limit");
    await app.click("Bekor qilish", d);
    await d.waitForExist({ reverse: true });
  });

  it("L3. o'qish vaqti: 1 soat 30 daqiqa", async () => {
    const card = await app.region(`Bilim rejasi: ${PLAN1}`, "section");
    await app.type("Oʻqish, soat", "1", card);
    await app.type("Oʻqish, daqiqa", "30", card);
    await app.click("Vaqtni yozish", card);
    await waitIn(app, card, "Jami oʻqildi: 1 soat 30 daqiqa");
  });

  it("L4. xarajat «O'zimga sarmoya» belgisi bilan rejaga — kartada sarflangan va oylik ulush", async () => {
    await app.nav("Xarajatlar");
    await app.type("Summa", "1 200 000");
    await app.selectText("Kategoriya", "Boshqa");
    await app.choose("Oʻzimga sarmoya (bilim, malaka)");
    await app.selectText("Bilim rejasi (ixtiyoriy)", PLAN1);
    await noAxe(app, "expense-self-investment");
    await app.click("Saqlash");
    await app.waitText("1 200 000 soʻm");

    await app.nav("Oʻzimga sarmoya");
    const card = await app.region(`Bilim rejasi: ${PLAN1}`, "section");
    await waitIn(app, card, "sarflandi: 1 200 000 soʻm");
    assert.match(await app.text("learn-self-investment"), /1 200 000 soʻm — daromadning 10 %/);
    await app.nav("Oylik audit");
    await app.waitText("1 200 000 soʻm — daromadning 10 %");
    await app.nav("Oʻzimga sarmoya");
  });

  it("L5. kurs tekshiruvi: daromad kafolati — qizil", async () => {
    await app.click("Kursni tekshirish", await app.region(`Bilim rejasi: ${PLAN1}`, "section"));
    const dialog = await app.x("//div[@role='dialog']");
    assert.equal(await (await app.button("Kurs yoki ustoz taklifi", dialog)).getAttribute("aria-pressed"), "true");
    for (const [q, r] of [
      ["boylik", "Yoʻq"],
      ["«Sir»", "Yoʻq"],
      ["kafolatlanyaptimi", "Ha"],
      ["Dastur va amaliy natija", "Ha"],
      ["Oʻqituvchining", "Bilmayman"],
      ["Shoshiltirishyaptimi", "Yoʻq"],
      ["olib kelsangiz", "Yoʻq"],
      ["Sinov darsi", "Ha"],
    ]) {
      await answer(app, dialog, q, r);
    }
    await app.click("Tekshirish", dialog);
    const result = await app.testId("offer-result");
    await result.waitForDisplayed();
    const text = await result.getText();
    assert.match(text, /Qizil: pul toʻlamang/);
    assert.match(text, /Hech kim kelajakdagi daromadingizni kafolatlay olmaydi/);
    assert.match(text, /namunalarini yoki shogirdlarini soʻrang/);
    await noAxe(app, "course-check-red");
    await app.b.execute(() => document.querySelector('[data-testid="offer-result"]')?.scrollIntoView({ block: "end" }));
    await app.shot("desktop-106-course-check-red");
    await app.click("Yopish", dialog);
    await dialog.waitForExist({ reverse: true });
  });

  it("L6. «Ilm zakoti»: hamkasbga rozetka ulashni o'rgatdi", async () => {
    await app.click("Oʻrgatganimni yozish");
    const d = await app.region("Ilm zakoti: oʻrgatish yozuvi");
    await app.type("Nimani oʻrgatdi", "Rozetka ulash", d);
    await app.type("Kimga (ixtiyoriy): ism yoki «qoʻshni», «xodim»", "hamkasb", d);
    await app.type("Qancha vaqt, daqiqa (ixtiyoriy)", "45", d);
    await app.click("Saqlash", d);
    await d.waitForExist({ reverse: true });
    await app.b.waitUntil(async () => (await app.text("teach-count")).includes("Shu oy: 1 marta oʻrgatildi"));
    await app.waitText("kimga: hamkasb");
  });

  it("L7. natijani o'lchash: yangi hisobsiz — xabar; qayta hisobdan keyin farq va foiz", async () => {
    let card = await app.region(`Bilim rejasi: ${PLAN1}`, "section");
    await app.click("Natijani oʻlchash", card);
    await waitIn(app, card, "hisobini yangidan saqlang");
    const hour = await app.region("Bir soatim qancha? — Bekzod", "section");
    await app.type("Oylik daromad (boʻsh — avtomatik)", "12 870 000", hour);
    await app.click("Hisoblash va saqlash", hour);
    await waitIn(app, hour, "45 000 soʻm");
    card = await app.region(`Bilim rejasi: ${PLAN1}`, "section");
    await app.click("Natijani oʻlchash", card);
    const r = await card.$('[data-testid="plan-result"]');
    await r.waitForDisplayed();
    await waitIn(app, r, "Farq: 9 000 soʻm (25 %)");
    assert.match(await r.getText(), /36 000 soʻm → 45 000 soʻm \/ soat/);
    await noAxe(app, "learning-result");
    await app.b.execute(() => document.querySelector('[data-testid="plan-result"]')?.scrollIntoView({ block: "center" }));
    await app.shot("desktop-105-learning-plans");
  });
});
