// Kasb-kor «Haqiqiy foydani bil» (K2, kasbkor/SPEC 3.1–3.3), haqiqiy ilovada: Nilufar atelyesi —
// tushum 18 mln, chiqim 8,5 mln → ko'rinadigan foyda 9,5 mln; o'z mehnati 5 mln, qizining 80 soati
// (15 000), 2 ta tikuv mashinasi 12 mln / 60 oy → haqiqiy foyda 3 100 000. Jasur buyurtmasi —
// tannarxdan past narx ogohlantirishi. Uskuna sotilsa — balans bir martalik xarajat. Har ekran axe bilan.
import assert from "node:assert/strict";
import { after, afterEach, before, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard } from "../lib/flows.mjs";

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

async function waitValue(app, id, fragment) {
  await app.b.waitUntil(async () => (await app.text(id)).includes(fragment), { timeout: 15000, timeoutMsg: `${id}: ${fragment} yo'q` });
}

async function entry(app, action, { amount, wallet, category }) {
  // «Tushum» tugmasida `Ctrl+N` belgisi ham bor — klaviatura bilan ochamiz.
  if (action === "Tushum") await app.b.keys(["Control", "n"]);
  else await app.click(action, await app.region("Yozuv qoʻshish"));
  const dialog = await app.x("//div[@role='dialog']");
  await app.type("Summa", amount, dialog);
  if (category) await app.selectText("Kategoriya", category, dialog);
  if (wallet) await app.click(wallet, dialog);
  await app.click("Saqlash", dialog);
  await dialog.waitForExist({ reverse: true });
}

describe("Kasb-kor: haqiqiy foyda", () => {
  let app;
  before(async () => {
    app = await startApp();
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`kkp-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("P1. Nilufar: tushum va chiqimlar → ko'rinadigan foyda", async () => {
    await onboard(app, { household: "Nilufarlar oilasi", name: "Nilufar", spaces: ["Kasb-kor"], rhythm: "Buyurtma boʻyicha" });
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await app.waitText("Haqiqiy foyda (shu oy)");
    await entry(app, "Tushum", { amount: "18 000 000", wallet: "Karta" });
    await entry(app, "Chiqim", { amount: "6 000 000", wallet: "Karta", category: "Material va xomashyo" });
    await entry(app, "Chiqim", { amount: "2 000 000", wallet: "Karta", category: "Ijara (ustaxona, doʻkon)" });
    await entry(app, "Chiqim", { amount: "500 000", wallet: "Karta", category: "Boshqa" });
    await waitValue(app, "kk-cash-flow", "9 500 000");
    await waitValue(app, "kk-true-profit", "9 500 000");
    await app.waitText("Oʻz mehnatingiz bahosi kiritilmagan");
  });

  it("P2. o'z mehnati bahosi 5 mln", async () => {
    await app.click("Bahoni kiritish");
    await app.type("Oʻz mehnatingiz bahosi (oyiga)", "5 000 000");
    await app.click("Saqlash", await app.region("Foyda qanday hosil boʻldi", "section"));
    await waitValue(app, "kk-true-profit", "4 500 000");
  });

  it("P3. oilaviy mehnat: qizining 80 soati", async () => {
    await app.nav("Oilaviy mehnat");
    await app.waitText("Mehnat yozish");
    await noAxe(app, "kk-labor");
    const form = await app.region("Mehnat yozish", "form");
    await app.type("Kim", "Madina (qizim)", form);
    await app.type("Soat", "80", form);
    await app.type("Soat bahosi", "15 000", form);
    await app.click("Yozish", form);
    await waitValue(app, "kk-family-labor", "1 200 000");
    await app.waitText("Madina (qizim)");
  });

  it("P4. uskuna: 2 ta tikuv mashinasi 12 mln, 60 oy", async () => {
    await app.nav("Uskunalar");
    const form = await app.region("Uskuna qoʻshish", "form");
    await app.type("Nomi", "Tikuv mashinalari (2 ta)", form);
    await app.type("Narxi", "12 000 000", form);
    await app.type("Foydali muddat (oy)", "60", form);
    await app.click("Karta", form);
    await app.click("Qoʻshish", form);
    await waitValue(app, "kk-eq-dep-Tikuv mashinalari (2 ta)", "200 000");
    await app.waitText("Yana 59 oy");
    await noAxe(app, "kk-equipment");
    await app.shot("desktop-64-kk-equipment");
  });

  it("P5. bosh sahifa: haqiqiy foyda 3 100 000; uskuna pul oqimiga kirmaydi", async () => {
    await app.nav("Bosh sahifa");
    await waitValue(app, "kk-true-profit", "3 100 000");
    assert.ok((await app.text("kk-cash-flow")).includes("9 500 000"), "uskuna xaridi pul oqimiga kirmaydi");
    await waitValue(app, "kk-wallet-CARD", "-2 500 000");
    await app.waitText("Uskuna xaridi");
    await noAxe(app, "kk-home-profit");
    await app.shot("desktop-65-kk-true-profit");
  });

  it("P6. Jasur buyurtmasi: narx tannarxdan past", async () => {
    await app.nav("Buyurtma narxi");
    await app.type("Material", "450 000");
    await app.type("Mehnat (soat)", "6");
    await app.type("Soat bahosi", "40 000");
    await app.type("Yoʻl", "50 000");
    await app.type("Asbob eskirishi ulushi", "20 000");
    await app.type("Zaxira (%)", "5");
    await app.type("Mijozga aytiladigan narx", "700 000");
    await app.type("Avans", "300 000");
    await app.click("Hisoblash");
    await waitValue(app, "kk-quote-cost", "798 000");
    const verdict = await app.text("kk-quote-verdict");
    assert.ok(verdict.includes("142 000") && verdict.includes("23 666,67"), verdict);
    assert.ok((await app.text("kk-quote-advance")).includes("150 000"));
    await noAxe(app, "kk-quote");
    await app.shot("desktop-66-kk-quote");
  });

  it("P7. uskuna shu oy 4 mln ga sotildi → 8 mln bir martalik xarajat", async () => {
    await app.nav("Uskunalar");
    await app.click("Sotildi / yaroqsiz");
    const form = await app.region("Tikuv mashinalari (2 ta): sotildi yoki yaroqsiz", "form");
    await app.type("Sotilgan narx", "4 000 000", form);
    await app.click("Naqd kassa", form);
    await app.click("Tasdiqlash", form);
    await app.waitText("chiqib ketdi");
    await app.nav("Bosh sahifa");
    await waitValue(app, "kk-true-profit", "-4 700 000");
    await app.waitText("Uskuna chiqib ketishi");
    await waitValue(app, "kk-wallet-CASH", "4 000 000");
  });
});
