// Kasb-kor tovar qoldig'i (K5, kasbkor/SPEC 4), haqiqiy ilovada. Bahodir aka, shakar: 50 kg × 11 000
// (ilovagacha bor edi) + 100 kg × 12 500 (kartadan) → 80 kg 1 120 000 ga sotildi: o'rtacha tannarx
// 960 000, qolgan 70 kg — 840 000. Joriy xarid narxi 13 500 → 945 000, farq 105 000; 13 000 ga sotish —
// ogohlantirish. Sanoqda 69,5 kg → 6 000 yo'qotish. 91 kundan keyin — muzlagan tovar.
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

async function sugarCard(app) {
  const card = await app.testId("kk-item-Shakar");
  await card.waitForDisplayed();
  return card;
}

async function move(app, action, { qty, amount, wallet, reason }) {
  const card = await sugarCard(app);
  await app.click(action, card);
  const form = await app.region(`Shakar: ${action}`, "form");
  await app.type(action === "Sanash" ? "Sanalgan miqdor (kg)" : "Miqdor (kg)", qty, form);
  if (amount) await app.type(action === "Xarid" ? "Jami narx" : "Tushum", amount, form);
  if (wallet) await app.click(wallet, form);
  if (reason) await app.type("Sabab", reason, form);
  await app.click("Saqlash", form);
  await form.waitForExist({ reverse: true });
}

describe("Kasb-kor: tovarlar", () => {
  let app;
  let profile;
  before(async () => {
    app = await startApp();
    profile = app.dir;
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`kks-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("S1. shakar: xarid, xarid, sotuv — o'rtacha tannarx 12 000/kg", async () => {
    await onboard(app, { household: "Bahodirlar oilasi", name: "Bahodir", spaces: ["Kasb-kor"], rhythm: "Har kuni naqd" });
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await app.waitText("Haqiqiy foyda (shu oy)");
    await app.nav("Tovarlar");
    await app.click("Yangi tovar");
    const form = await app.region("Yangi tovar", "form");
    await app.type("Nomi", "Shakar", form);
    await app.type("Sotuv narxi (1 kg)", "14 000", form);
    await app.click("Tovarni qoʻshish", form);
    await move(app, "Xarid", { qty: "50", amount: "550 000", wallet: "Ilovagacha bor edi" });
    await move(app, "Xarid", { qty: "100", amount: "1 250 000", wallet: "Karta" });
    await move(app, "Sotuv", { qty: "80", amount: "1 120 000", wallet: "Naqd kassa" });
    const card = await sugarCard(app);
    await waitIn(await card.$('[data-testid="kk-item-qty"]'), "70 kg", "qoldiq");
    assert.match(await card.getText(), /840 000/);
    assert.match(await card.getText(), /12 000/);
    await noAxe(app, "kk-stock");
    await app.shot("desktop-72-kk-stock");
  });

  it("S2. joriy narx 13 500: farq 105 000; 13 000 ga sotish — ogohlantirish", async () => {
    const card = await sugarCard(app);
    await app.click("Tahrirlash", card);
    const form = await app.region("Shakar: tahrirlash", "form");
    await app.type("Sotuv narxi (1 kg)", "13 000", form);
    await app.type("Joriy xarid narxi (1 kg)", "13 500", form);
    await app.click("Saqlash", form);
    await form.waitForExist({ reverse: true });
    await waitIn(await app.testId("kk-stock-gap"), "105 000", "farq");
    await waitIn(await sugarCard(app), "Shu narxda sotsangiz, bu tovarni qayta ololmaysiz", "ogohlantirish");
    await noAxe(app, "kk-stock-warning");
    await app.shot("desktop-73-kk-stock-warning");
  });

  it("S3. sanoq 69,5 kg: 6 000 yo'qotish foyda tarkibida", async () => {
    await move(app, "Sanash", { qty: "69,5", reason: "Toʻkilgan" });
    await waitIn(await (await sugarCard(app)).$('[data-testid="kk-item-qty"]'), "69,5 kg", "sanoq");
    await app.nav("Bosh sahifa");
    await waitIn(await app.testId("kk-stock-value"), "834 000", "tovar qoldig'i");
    const profit = await app.region("Foyda qanday hosil boʻldi", "section");
    const text = await profit.getText();
    assert.match(text, /Sotilgan tovar tannarxi[\s\S]*?960 000/);
    assert.match(text, /Tovar yoʻqotishlari[\s\S]*6 000/);
    assert.ok((await app.text("kk-wallet-CARD")).includes("-1 250 000"), "xarid kartadan");
    await noAxe(app, "kk-home-stock");
    await app.shot("desktop-74-kk-home-stock");
  });

  it("S4. 91 kundan keyin: muzlagan tovar bosh sahifada (qayta tiklash narxida)", async () => {
    await app.stop();
    app = await startApp({ profile, shiftDays: 91 });
    await unlock(app);
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await waitIn(await app.testId("kk-stock-frozen"), "938 250", "muzlagan");
    await app.nav("Tovarlar");
    await waitIn(await sugarCard(app), "Muzlagan: oxirgi sotuv", "muzlagan belgisi");
    await noAxe(app, "kk-stock-frozen");
    await app.shot("desktop-75-kk-stock-frozen");
  });
});
