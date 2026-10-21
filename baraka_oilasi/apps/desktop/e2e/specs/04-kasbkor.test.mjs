// Kasb-kor «ikki cho'ntak» (K1, kasbkor/SPEC 2): tikuvchi Nodira — boshlang'ich qoldiq → maosh
// belgilash → tushum (Ctrl+N) → chiqim → «egasi oldi» (pul oqimi kamaymaydi) → maoshni Uy'ga
// o'tkazish (bitta atomar yozuv) → Uy'dagi ulush taklifi → Uy'da daromad. Har bir ekran axe bilan.
import assert from "node:assert/strict";
import { after, afterEach, before, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard } from "../lib/flows.mjs";

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

/** Bosh sahifadagi qiymat kutilgan matnni o'z ichiga olguncha kutadi. */
async function waitValue(app, id, fragment) {
  await app.b.waitUntil(async () => (await app.text(id)).includes(fragment), { timeout: 15000, timeoutMsg: `${id}: ${fragment} yo'q` });
}

async function entry(app, action, { amount, wallet, category, note }) {
  await app.click(action, await app.region("Yozuv qoʻshish"));
  const dialog = await app.x("//div[@role='dialog']");
  await app.type("Summa", amount, dialog);
  if (category) await app.selectText("Kategoriya", category, dialog);
  if (wallet) await app.click(wallet, dialog);
  if (note) await app.type(action === "Tushum" ? "Buyurtma yoki mijoz" : "Izoh", note, dialog);
  await app.click("Saqlash", dialog);
  await dialog.waitForExist({ reverse: true });
}

describe("Kasb-kor: ikki cho'ntak", () => {
  let app;
  before(async () => {
    app = await startApp();
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`kk-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("K1. onboarding: Uy + Kasb-kor; Kasb-kor bosh sahifasi va qisqa navigatsiya", async () => {
    await onboard(app, { household: "Nodiralar oilasi", name: "Nodira", spaces: ["Kasb-kor"], rhythm: "Buyurtma boʻyicha" });
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await app.waitText("Egasiga toʻlangan (shu oy)");
    const nav = await (await app.b.$("nav")).getText();
    assert.ok(nav.includes("Bosh sahifa") && nav.includes("Sinxronlash") && nav.includes("Sozlamalar"), nav);
    assert.ok(!nav.includes("Kelajagim") && !nav.includes("Xarajatlar"), "Kasb-kor'da Uy bo'limlari yo'q");
    await noAxe(app, "kk-home");
    await app.shot("desktop-61-kk-empty");
  });

  it("K2. boshlang'ich qoldiq va egasining maoshi", async () => {
    await entry(app, "Boshlangʻich qoldiq", { amount: "500 000", wallet: "Naqd kassa" });
    await waitValue(app, "kk-wallet-CASH", "500 000");
    await app.click("Maosh belgilash");
    await app.type("Oylik maosh", "4 000 000");
    await app.click("Saqlash", await app.region("Egasining maoshi", "section"));
    await app.waitText("Oyiga 4 000 000");
    await waitValue(app, "kk-salary-remaining", "4 000 000");
  });

  it("K3. tushum (Ctrl+N) va chiqim → pul oqimi", async () => {
    await app.b.keys(["Control", "n"]);
    const dialog = await app.x("//div[@role='dialog']");
    await noAxe(app, "kk-sale-dialog");
    await app.type("Summa", "6 000 000", dialog);
    await app.click("Karta", dialog);
    await app.type("Buyurtma yoki mijoz", "Kelin libosi", dialog);
    await app.click("Saqlash", dialog);
    await dialog.waitForExist({ reverse: true });
    await waitValue(app, "kk-cash-flow", "6 000 000");

    await entry(app, "Chiqim", { amount: "1 500 000", wallet: "Karta", category: "Material va xomashyo" });
    await waitValue(app, "kk-cash-flow", "4 500 000");
    await waitValue(app, "kk-wallet-CARD", "4 500 000");
  });

  it("K4. «egasi oldi» foydani kamaytirmaydi, maosh qoldig'ini kamaytiradi", async () => {
    await entry(app, "Egasi oldi", { amount: "300 000", wallet: "Naqd kassa", note: "bozorlik" });
    await waitValue(app, "kk-owner-paid", "300 000");
    assert.ok((await app.text("kk-cash-flow")).includes("4 500 000"));
    await waitValue(app, "kk-salary-remaining", "3 700 000");
    await waitValue(app, "kk-wallet-CASH", "200 000");
    await noAxe(app, "kk-home-filled");
    await app.shot("desktop-62-kk-home");
  });

  it("K5. maoshni Uy'ga o'tkazish → ulush taklifi → Ajratish", async () => {
    await app.click("Maoshni Uy'ga oʻtkazish");
    const dialog = await app.x("//div[@role='dialog']");
    assert.equal(await (await app.field("Summa", dialog)).getValue(), "3700000", "standart — shu oy maosh qoldig'i");
    await app.click("Oʻtkazish", dialog);
    await app.waitText("Uy makoniga 3 700 000");
    await noAxe(app, "kk-salary-offer");
    await app.shot("desktop-63-kk-salary-offer");
    await app.click("Ajratish", dialog);
    await dialog.waitForExist({ reverse: true });
    await waitValue(app, "kk-owner-paid", "4 000 000");
    await waitValue(app, "kk-salary-remaining", "qoldi: 0");
    await waitValue(app, "kk-wallet-CARD", "800 000");
    assert.ok((await app.text("kk-cash-flow")).includes("4 500 000"), "maosh pul oqimiga kirmaydi");
    await app.waitText("Egasi maoshi → Uy");
  });

  it("K6. Uy makonida: maosh daromad, ulush «Kelajagim»da", async () => {
    await app.click("Uy", await app.region("Makonlar"));
    await waitValue(app, "kpi-paid-to-self", "185 000");
    await app.nav("Oylik audit");
    await app.waitText("3 700 000");
    await noAxe(app, "uy-audit");
  });
});
