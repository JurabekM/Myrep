// Kasb-kor kengayish darvozasi, zakot hisobi, tarozi va sanoq (K7, kasbkor/SPEC 6, 8), haqiqiy ilovada.
// Tushum 120 000 000, chiqim 2 000 000: darvoza yopiq (zaxira, «Hisob kuni», reja yo'q). Zakot: oltin
// 1 100 000 × 85 = nisob 93,5 mln; baza 118 mln; hawl tasdiqlangach 2 950 000 (hisob, fatvo emas).
// Tarozi tekshirildi, shakar sanaldi (9,5 kg). 35 kundan keyin — tarozi eslatmasi.
import assert from "node:assert/strict";
import { after, afterEach, before, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard, unlock } from "../lib/flows.mjs";

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

async function waitIn(el, fragment, what) {
  await el.waitUntil(async () => (await el.getText()).includes(fragment), { timeout: 15000, timeoutMsg: `${what}: ${fragment} yo'q` });
}

async function entry(app, action, { amount, wallet, category }) {
  if (action === "Tushum") await app.b.keys(["Control", "n"]);
  else await app.click(action, await app.region("Yozuv qoʻshish"));
  const dialog = await app.x("//div[@role='dialog']");
  await app.type("Summa", amount, dialog);
  if (category) await app.selectText("Kategoriya", category, dialog);
  if (wallet) await app.click(wallet, dialog);
  await app.click("Saqlash", dialog);
  await dialog.waitForExist({ reverse: true });
}

describe("Kasb-kor: darvoza, zakot, tarozi", () => {
  let app;
  let profile;
  before(async () => {
    app = await startApp();
    profile = app.dir;
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`kkg-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("G1. darvoza yopiq: sabablar va keyingi qadamlar", async () => {
    await onboard(app, { household: "Bahodirlar oilasi", name: "Bahodir", spaces: ["Kasb-kor"], rhythm: "Har kuni naqd" });
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await app.waitText("Haqiqiy foyda (shu oy)");
    await entry(app, "Tushum", { amount: "120 000 000", wallet: "Karta" });
    await entry(app, "Chiqim", { amount: "2 000 000", wallet: "Karta", category: "Boshqa" });
    await app.nav("Kengayish darvozasi");
    await waitIn(await app.testId("kk-gate-status"), "Darvoza yopiq", "darvoza");
    assert.match(await app.text("kk-gate-PLAN"), /Keyingi qadam/);
    assert.match(await app.text("kk-gate-PROFIT"), /«Hisob kuni» oʻtkazilmagan/);
    await noAxe(app, "kk-gate");
    await app.shot("desktop-80-kk-gate");
  });

  it("G2. zakot: oltin narxi, hawl tasdig'i → 2 950 000; hisob saqlanadi", async () => {
    await app.nav("Zakot hisobi");
    await app.waitText("Hisob, fatvo emas");
    const form = await app.region("Sozlamalar", "form");
    await app.type("Oltin narxi (1 gramm)", "1 100 000", form);
    await app.click("Saqlash", form);
    await waitIn(await app.region("Hisob", "section"), "93 500 000", "nisob");
    await waitIn(await app.testId("kk-zakat-base"), "118 000 000", "baza");
    await app.choose("Biznes kamida bir qamariy yildan beri bor");
    await waitIn(await app.testId("kk-zakat-amount"), "2 950 000", "zakot");
    await noAxe(app, "kk-zakat");
    await app.shot("desktop-81-kk-zakat");
    await app.click("Hisobni saqlash");
    await waitIn(await app.region("Saqlangan hisoblar", "section"), "2 950 000", "tarix");
  });

  it("G3. tarozi tekshirildi; yillik sanoq: shakar 9,5 kg", async () => {
    await app.nav("Tovarlar");
    await app.click("Yangi tovar");
    const item = await app.region("Yangi tovar", "form");
    await app.type("Nomi", "Shakar", item);
    await app.click("Tovarni qoʻshish", item);
    const card = await app.testId("kk-item-Shakar");
    await card.waitForDisplayed();
    await app.click("Xarid", card);
    const buy = await app.region("Shakar: Xarid", "form");
    await app.type("Miqdor (kg)", "10", buy);
    await app.type("Jami narx", "120 000", buy);
    await app.click("Ilovagacha bor edi", buy);
    await app.click("Saqlash", buy);
    await buy.waitForExist({ reverse: true });

    await app.nav("Tarozi va sanoq");
    await app.choose("Har oy eslatish");
    await (await app.testId("kk-scale-due")).waitForDisplayed();
    // Forma Enter bilan yuboriladi: «Tekshirildi» bosilganda fokus oynani surib, mouseup tugmadan chetga tushadi.
    await app.type("Izoh (sozlangan yoki nosoz boʻlsa — majburiy)", "Toshlar bilan solishtirildi", await app.region("Tekshiruv natijasi", "form"));
    await app.b.keys(["Enter"]);
    await (await app.testId("kk-scale-due")).waitForExist({ reverse: true });
    const inv = await app.region("Sanalgan miqdorlar", "form");
    await app.type("Shakar: sanalgan (kg)", "9,5", inv);
    await app.type("Izoh (farqlar uchun)", "Yillik sanoq", inv);
    await app.b.keys(["Enter"]);
    await waitIn(await app.testId("kk-count-row"), "1 tasida farq", "sanoq");
    await noAxe(app, "kk-measure");
    await app.shot("desktop-82-kk-measure");
  });

  it("G4. 35 kundan keyin: bosh sahifada tarozi eslatmasi", async () => {
    await app.stop();
    app = await startApp({ profile, shiftDays: 35 });
    await unlock(app);
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await waitIn(await app.testId("kk-scale-reminder"), "Tarozini tekshirish vaqti keldi", "eslatma");
    await noAxe(app, "kk-home-reminders");
    await app.shot("desktop-83-kk-home-reminders");
  });
});
