// Bekzod ssenariysi (D15 / V15) — hozir mavjud funksiyalar bilan (OQ-P12: U3–U7 hali yo'q):
// daromad → ulush → xarajat → audit → qarz → 70/20/10 → «Qarzsiz kun» → qarz yopilishi →
// [bir oydan keyin] darvoza ochiq → Sherzod bilan musharaka (9/9, imzolar) → kassa daftari →
// davr taqsimoti (1,4 mln) → vazifa hodisasi («bot ishdan chiqdi») → oylik ko'rik va bayonnoma →
// zaxira nusxa. Har bir ekran haqiqiy webview'da axe-core bilan tekshiriladi.
//
// Vaqt: A bosqichi — bugun (yadro soati = haqiqiy); B bosqichi — ilova `BARAKA_DEV_SHIFT_DAYS=20`
// bilan qayta ochiladi, shunda A dagi xarajatlar «o'tgan oy» bo'ladi (darvoza o'tgan to'liq
// oylar bo'yicha hisoblanadi).
import assert from "node:assert/strict";
import { after, afterEach, before, describe, it } from "node:test";

import { startApp, xq } from "../lib/app.mjs";
import { onboard, unlock } from "../lib/flows.mjs";

const SHIFT = 20;

/** Yadro soati bo'yicha sana (`DD.MM.YYYY`), `shift` kun keyin. */
function day(shift, plus = 0) {
  const d = new Date();
  d.setDate(d.getDate() + shift + plus);
  return `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`;
}

/** B bosqichidagi oyning `n`-kuni (yadro soati bo'yicha). */
function inMonth(n) {
  const d = new Date();
  d.setDate(d.getDate() + SHIFT);
  return `${String(n).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`;
}

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

describe("Bekzod ssenariysi", () => {
  let app;
  let profile;
  before(async () => {
    app = await startApp();
    profile = app.dir;
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("A1. onboarding: kunlik naqd, qarzim bor → qarzlar ekrani", async () => {
    await onboard(app, { members: [{ name: "Mohira" }, { name: "Jasur", child: true }], rhythm: "Har kuni naqd", debts: true });
    assert.equal(await (await app.b.$('nav button[aria-current="page"]')).getText(), "Qarzlar");
  });

  it("A2. qarz: Akmal akadan 1,5 mln (foizsiz, jadval bilan)", async () => {
    await app.click("Qarz qoʻshish");
    const form = await app.region("Qarz qoʻshish", "form");
    await app.type("Kreditor (ism yoki bank)", "Akmal aka", form);
    await app.type("Hozirgi qoldiq", "1 500 000", form);
    await app.type("Sababi", "uy taʼmiri", form);
    await app.type("Sana 1", day(0, 40), form);
    await app.type("Summa 1", "1 500 000", form);
    await noAxe(app, "qarz qo'shish");
    await app.click("Saqlash", form);
    const card = await app.region("Akmal aka", "article");
    await app.waitText("1 500 000");
    await app.shot("bekzod-a2-debt");
    assert.match(await card.getText(), /Qarindosh/);
  });

  it("A3. daromad (Ctrl+N) va ulush «Kelajagim»ga", async () => {
    await app.nav("Bosh sahifa");
    await (await app.testId("nudge-INCOME_TODAY")).waitForDisplayed();
    await app.b.keys(["Control", "n"]);
    await app.type("Summa", "6 000 000");
    await app.type("Manba", "Taksi");
    await noAxe(app, "daromad oynasi");
    await app.click("Saqlash");
    await app.click("Boshqa summa");
    await app.type("Boshqa summa", "3 500 000");
    await app.click("Ajratish");
    await app.b.$('[role="dialog"]').waitForExist({ reverse: true });
    await app.b.waitUntil(async () => (await app.text("kpi-paid-to-self")).includes("3 500 000"));
    await noAxe(app, "bosh sahifa");
    await app.shot("bekzod-a3-home");
  });

  it("A4. xarajat (zarur) va oylik audit", async () => {
    await app.nav("Xarajatlar");
    await app.type("Summa", "500 000");
    await app.selectText("Kategoriya", "Oziq-ovqat");
    await app.click("Saqlash");
    await app.waitText("500 000");
    await noAxe(app, "xarajatlar");
    await app.nav("Oylik audit");
    await (await app.testId("gap")).waitForDisplayed();
    await noAxe(app, "audit");
    await app.shot("bekzod-a4-audit");
  });

  it("A5. «Qarzdan chiqish» 70/20/10 va «Qarzsiz kun»", async () => {
    await app.nav("Qarzdan chiqish");
    await app.click("Yoqish");
    await app.waitText("«Qarzdan chiqish» rejimi");
    await app.waitText("Qarzsiz kun — qoʻshimcha toʻlov bilan");
    await noAxe(app, "qarzdan chiqish");
    await app.shot("bekzod-a5-payoff");
    await app.nav("Bosh sahifa");
    await (await app.testId("kpi-debt-free")).waitForDisplayed();
  });

  it("A6. qarz yopildi → «Qarzsiz kun keldi!» → bo'shagan pul Kelajagimga", async () => {
    await app.nav("Qarzlar");
    const card = await app.region("Akmal aka", "article");
    await app.click("Toʻlov yozish", card);
    await app.type("Summa", "1 500 000", card);
    await app.click("Saqlash", card);
    const dialog = await app.b.$('[role="dialog"]');
    await dialog.waitForDisplayed();
    assert.match(await dialog.getText(), /Qarzsiz kun keldi!/);
    await noAxe(app, "nishonlash");
    await app.shot("bekzod-a6-celebration");
    await app.click("Keyinroq", dialog);
    await dialog.waitForExist({ reverse: true });
    assert.match(await (await app.region("Akmal aka", "article")).getText(), /Yopilgan/);
  });

  it("B0. bir oydan keyin: ilova qayta ochiladi (yadro soati +20 kun)", async () => {
    await app.stop();
    app = await startApp({ profile, shiftDays: SHIFT });
    await unlock(app);
  });

  it("B1. musharaka: Bekzod (kapital va mehnat, biz) va Sherzod (kapital egasi)", async () => {
    await app.nav("Sheriklik");
    await app.click("Yangi sheriklik");
    await app.type("Sheriklik nomi", "Taksi va tikuv ustaxonasi");
    await app.choose("Musharaka");
    const p1 = await party(app, "P1");
    await app.type("P1: toʻliq ism-sharif", "Bekzod Karimov", p1);
    await app.select("Roli", "BOTH", p1);
    await app.choose("Bu — biz", p1);
    const p2 = await party(app, "P2");
    await app.type("P2: toʻliq ism-sharif", "Sherzod Rahimov", p2);
    await app.select("Roli", "CAPITAL_PROVIDER", p2);
    await noAxe(app, "sheriklik 1-qadam");
    await app.click("Saqlash va keyingisi");
    await app.waitText("Qoralama");
  });

  it("B2. hissalar, vazifa, foyda, hisob yurituvchi, ajralish, hakam, muddat → 9/9", async () => {
    await step(app, "Kim nima qoʻshadi?");
    for (const [name, kind, what, amount, label] of [
      ["Bekzod Karimov", "MONEY", "Aylanma mablagʻ", "4 000 000", "Summa"],
      ["Sherzod Rahimov", "EQUIPMENT", "Tikuv uskunasi", "6 000 000", "Kelishilgan narxi"],
    ]) {
      const block = await app.x(`//div[contains(@class,"rounded")][p[normalize-space()=${xq(name)}]]`);
      await app.click("+ Hissa qoʻshish", block);
      await app.select("Turi", kind, block);
      await app.type("Nima", what, block);
      await app.type(label, amount, block);
    }
    await app.click("Saqlash va keyingisi");

    await app.type("Vazifa", "Telegram-bot orqali buyurtmalarni qabul qilish");
    await app.selectText("Masʼul", "Bekzod Karimov");
    await app.type("Bajarilmasa nima boʻladi", "1 kun ichida xabar beradi, buyurtmalar telefon orqali qabul qilinadi");
    await app.click("Saqlash va keyingisi");
    await app.click("Saqlash va keyingisi"); // 4. foyda 50/50
    await app.click("Saqlash va keyingisi"); // 5. zarar — kapitalga mutanosib
    await app.type("Pul qayerda turadi", "Bekzodning kartasida");
    await app.selectText("Hisobni kim yuritadi", "Bekzod Karimov");
    await app.click("Saqlash va keyingisi");
    await app.type("Ulush qanday baholanadi", "Bozor narxida, ikki tomon kelishgan baholovchi orqali");
    await app.type("Qachon va qanday toʻlanadi", "3 oy ichida, teng qismlarda");
    await app.click("Saqlash va keyingisi");
    await app.type("Hakam (toʻliq ism)", "Hasan Yusupov");
    await app.type("Tomonlarga aloqasi", "mahalla oqsoqoli");
    await app.type("1-guvoh", "Jamshid Aliyev");
    await app.click("Saqlash va keyingisi");
    await app.type("Boshlanish sanasi", inMonth(1));
    await app.type("Qayta koʻrib chiqish sanasi", nextYear(inMonth(1)));
    await app.click("Saqlash");
    await app.waitText("9 / 9 savolga javob berildi");
    await app.waitText("9 / 9 — shartnomani imzolash mumkin.");
    await noAxe(app, "sheriklik 9-qadam");
    await app.shot("bekzod-b2-nine-of-nine");
  });

  it("B3. imzolar: tomonlar, guvoh va hakam shu qurilmada", async () => {
    await step(app, "Imzolar");
    for (const name of ["Bekzod Karimov", "Sherzod Rahimov", "Jamshid Aliyev", "Hasan Yusupov"]) {
      await app.click(`${name} imzolaydi`);
      const dialog = await app.region(`${name}: imzo`, "div");
      await app.draw(await dialog.$('canvas[aria-label="Imzo maydoni"]'));
      if (name === "Bekzod Karimov") await noAxe(app, "imzo oynasi");
      await app.click("Imzolash", dialog);
      await dialog.waitForExist({ reverse: true });
      await app.x(`//img[@alt=${xq(`${name} imzosi`)}]`);
    }
    await app.waitText("1-versiyani hamma imzoladi.");
    await app.shot("bekzod-b3-signed");
  });

  it("B4. «bu qarz emas», oila roziligi, darvoza ochiq → sheriklik faol", async () => {
    await step(app, "Boshlash");
    await app.waitText("Tayyorgarlik darvozasi ochiq");
    await app.click("Tushundim, bu qarz emas");
    await app.click("Bekzod rozi");
    await app.click("Mohira rozi");
    await app.click("Sheriklikni boshlash");
    await app.waitText("Sheriklik faol");
    await noAxe(app, "sheriklik boshlash");
    await app.shot("bekzod-b4-active");
  });

  it("C1. kassa daftari: buyurtma 5 mln, material 2,2 mln", async () => {
    await app.click("Kassa daftari");
    const form = await app.region("Daftarga yozish", "form");
    await app.choose("Kirim", form);
    await app.selectText("Turi", "buyurtma", form);
    await app.type("Summa", "5 000 000", form);
    await app.type("Sana", inMonth(2), form);
    await app.type("Izoh", "Toʻy liboslari buyurtmasi", form);
    await app.click("Yozish", form);
    await app.waitText("Toʻy liboslari buyurtmasi");
    await app.choose("Xarajat", form);
    await app.selectText("Turi", "material", form);
    await app.type("Summa", "2 200 000", form);
    await app.type("Sana", inMonth(3), form);
    await app.type("Izoh", "Mato va iplar", form);
    await app.click("Yozish", form);
    await app.waitText("Mato va iplar");
    await noAxe(app, "kassa daftari");
  });

  it("C2. davr taqsimoti: oilaga 1,4 mln", async () => {
    await app.type("Davr oxiri", inMonth(4));
    await app.click("Taqsimotni koʻrish");
    await app.waitText("Oila byudjetiga daromad boʻlib tushadi: 1 400 000");
    await noAxe(app, "taqsimot");
    await app.shot("bekzod-c2-distribution");
    await app.click("Davrni yopish");
    await app.waitText("yopilgan");
  });

  it("C3. vazifa hodisasi: «bot ishdan chiqdi»", async () => {
    await app.click("Koʻrik va nizo");
    await app.click("Bajara olmayapman");
    const form = await app.region("Bajara olmayapman", "form");
    await app.type("Sana", inMonth(4), form);
    await app.type("Sabab", "Telegram-bot ishdan chiqdi", form);
    await app.type("Taklif qilingan yechim", "Buyurtmalarni telefon orqali qabul qilamiz", form);
    await app.click("Xabar berish", form);
    await app.waitText("Xabar jurnalga yozildi");
    await app.waitText("Kelishuvga koʻra endi: 1 kun ichida xabar beradi");
    await noAxe(app, "ko'rik va nizo");
    await app.shot("bekzod-c3-incident");
  });

  it("C4. oylik ochiq hisob ko'rigi va bayonnoma PDF", async () => {
    await app.click("Koʻrikni boshlash");
    const session = await app.region("Ochiq hisob koʻrigi", "div");
    await app.click("Koʻrsatish", session);
    await app.waitText("Zanjir tekshiruvi: barcha yozuvlar butun.");
    for (const name of ["Bekzod Karimov", "Sherzod Rahimov"]) {
      const group = await app.x(`//*[@role="radiogroup" and @aria-label=${xq(name)}]`);
      await app.choose("Koʻrdim, roziman", group);
    }
    await noAxe(app, "ko'rik sessiyasi");
    await app.shot("bekzod-c4-review");
    await app.click("Bayonnomani yozish", session);
    await session.waitForExist({ reverse: true });
    const article = await app.region("1-koʻrik", "article");
    assert.match(await article.getText(), /Butun/);
    await app.click("Bayonnoma PDF", article);
    await app.b.waitUntil(() => app.saved().some((f) => f.endsWith(".pdf")), { timeoutMsg: "bayonnoma PDF yozilmadi" });
  });

  it("D1. zaxira nusxa (to'liq eksport)", async () => {
    await app.nav("Sinxronlash");
    await app.type("Fayl paroli", "Bekzod-2026!");
    await app.type("Parolni takrorlang", "Bekzod-2026!");
    await app.click("Faylni saqlash");
    await app.waitText("Fayl saqlandi");
    assert.ok(app.saved().some((f) => f.endsWith(".baraka")));
    await noAxe(app, "sinxronlash");
    await app.nav("Bosh sahifa");
    // Zaxira olindi — eslatma yo'q; daromad ritmi eslatmasi bor.
    await (await app.testId("nudge-INCOME_TODAY")).waitForDisplayed();
    assert.equal(await (await app.testId("nudge-BACKUP")).isExisting(), false);
    await noAxe(app, "bosh sahifa (oxiri)");
    await app.shot("bekzod-d1-home");
  });
});

async function party(app, id) {
  return app.x(`//div[contains(@class,"rounded")][.//span[normalize-space()=${xq(`${id}: toʻliq ism-sharif`)}]]`);
}

async function step(app, name) {
  const btn = await app.x(`//nav[@aria-label="Shartnoma qadamlari"]//button[contains(normalize-space(), ${xq(name)})]`);
  await btn.click();
}

function nextYear(ddmmyyyy) {
  const [d, m, y] = ddmmyyyy.split(".");
  return `${d}.${m}.${Number(y) + 1}`;
}
