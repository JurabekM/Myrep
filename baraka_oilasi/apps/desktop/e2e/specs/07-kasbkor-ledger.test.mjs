// Kasb-kor kassa va nasiya (K4, kasbkor/SPEC 5), haqiqiy ilovada. Bahodir aka: ochilish 500 000, naqd
// sotuv 3 200 000, karta sotuv 900 000, non 400 000, «egasi oldi» 300 000, kartaga 1 500 000 → kutilgan
// 1 500 000, sanalgan 1 450 000 → −50 000. Malika: ko'ylak naqd 600 000, nasiya 660 000 = 3 × 220 000;
// birinchi to'lov o'z vaqtida, ikkinchisi 20 kun kechikadi — summa o'zgarmaydi, haftalik ko'rikda eslatma.
import assert from "node:assert/strict";
import { after, afterEach, before, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard, unlock } from "../lib/flows.mjs";

/** Bugundan 2 oy va 20 kun keyingacha kunlar (ikkinchi to'lov 20 kun kechikadi). */
function daysToSecondDuePlus20() {
  const now = new Date();
  const due = new Date(now.getFullYear(), now.getMonth() + 2, now.getDate(), 12);
  due.setDate(due.getDate() + 20);
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 12);
  return Math.round((due - today) / 86400000);
}

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

async function waitValue(app, id, fragment) {
  await app.b.waitUntil(async () => (await app.text(id)).includes(fragment), { timeout: 15000, timeoutMsg: `${id}: ${fragment} yo'q` });
}

async function entry(app, action, { amount, wallet, category, from, to }) {
  if (action === "Tushum") await app.b.keys(["Control", "n"]);
  else await app.click(action, await app.region("Yozuv qoʻshish"));
  const dialog = await app.x("//div[@role='dialog']");
  await app.type("Summa", amount, dialog);
  if (category) await app.selectText("Kategoriya", category, dialog);
  if (wallet) await app.click(wallet, dialog);
  if (from) await app.click(from, await dialog.$(".//fieldset[legend[normalize-space()='Qaysi hamyondan']]"));
  if (to) await app.click(to, await dialog.$(".//fieldset[legend[normalize-space()='Qaysi hamyonga']]"));
  await app.click("Saqlash", dialog);
  await dialog.waitForExist({ reverse: true });
}

describe("Kasb-kor: kassa va nasiya", () => {
  let app;
  let profile;
  before(async () => {
    app = await startApp();
    profile = app.dir;
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`kkl-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("L1. Bahodir: kunlik harakatlar", async () => {
    await onboard(app, { household: "Bahodirlar oilasi", name: "Bahodir", spaces: ["Kasb-kor"], rhythm: "Har kuni naqd" });
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await app.waitText("Haqiqiy foyda (shu oy)");
    await entry(app, "Boshlangʻich qoldiq", { amount: "500 000", wallet: "Naqd kassa" });
    await entry(app, "Tushum", { amount: "3 200 000", wallet: "Naqd kassa" });
    await entry(app, "Tushum", { amount: "900 000", wallet: "Karta" });
    await entry(app, "Chiqim", { amount: "400 000", wallet: "Naqd kassa", category: "Boshqa" });
    await entry(app, "Egasi oldi", { amount: "300 000", wallet: "Naqd kassa" });
    await entry(app, "Hamyonlar orasida", { amount: "1 500 000", from: "Naqd kassa", to: "Karta" });
    await waitValue(app, "kk-wallet-CASH", "1 500 000");
  });

  it("L2. kassani yopish: kutilgan 1 500 000, sanalgan 1 450 000 → −50 000", async () => {
    await app.nav("Kassa");
    await waitValue(app, "kk-cash-expected", "1 500 000");
    await noAxe(app, "kk-cash");
    await app.type("Sanalgan summa", "1 450 000");
    await app.click("Tekshirish");
    await waitValue(app, "kk-cash-difference", "-50 000");
    await app.choose("Nomaʼlum");
    await noAxe(app, "kk-cash-difference");
    await app.shot("desktop-69-kk-cash-close");
    await app.click("Kunni yopish");
    await app.waitText("Bugungi kassa yopilgan");
    await app.region("Yopilgan kunlar", "section");
    await app.nav("Bosh sahifa");
    await waitValue(app, "kk-wallet-CASH", "1 450 000");
  });

  it("L3. nasiya: yangi mijoz (rozilik bilan), ko'ylak 660 000 = 3 × 220 000, birinchi to'lov", async () => {
    await app.nav("Nasiya daftari");
    await app.click("Yangi nasiya");
    const cust = await app.region("Yangi mijoz", "form");
    await app.type("Ism", "Malika", cust);
    await app.type("Telefon (ixtiyoriy)", "+998 90 123 45 67", cust);
    await app.choose("Mijoz telefon raqami", cust);
    await app.click("Mijozni saqlash", cust);
    const form = await app.region("Nasiya shartlari", "form");
    await app.type("Tovar yoki xizmat", "Koʻylak", form);
    await app.type("Naqd narxi (maʼlumot uchun)", "600 000", form);
    await app.type("Nasiya narxi (qotiriladi)", "660 000", form);
    await app.click("Saqlash", form);
    const card = await app.testId("kk-credit-sale-Malika");
    await card.waitForDisplayed();
    await app.click("Toʻlov", card);
    const pay = await app.region("Toʻlov", "form");
    assert.equal(await (await app.field("Summa", pay)).getValue(), "220000");
    await app.click("Karta", pay);
    await app.click("Saqlash", pay);
    await pay.waitForExist({ reverse: true });
    await waitValue(app, "kk-credit-total", "440 000");
    await noAxe(app, "kk-credit");
    await app.shot("desktop-70-kk-credit");
  });

  it("L4. ikki oy-u 20 kundan keyin: kechikkan, summa o'zgarmagan, haftalik ko'rik", async () => {
    await app.stop();
    app = await startApp({ profile, shiftDays: daysToSecondDuePlus20() });
    await unlock(app);
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await waitValue(app, "kk-receivables", "440 000");
    await app.nav("Nasiya daftari");
    await waitValue(app, "kk-credit-d1_30", "440 000");
    const card = await app.testId("kk-credit-sale-Malika");
    assert.match(await card.getText(), /20 kun kechikkan/);
    assert.ok((await app.text("kk-credit-outstanding")).includes("440 000"), "ustama yo'q");
    const review = await app.region("Haftalik koʻrik (juma)", "section");
    assert.match(await (await app.field("Eslatma matni", review)).getValue(), /Assalomu alaykum, Malika!/);
    await app.choose("Bu hafta gaplashaman", review);
    await noAxe(app, "kk-credit-review");
    await app.shot("desktop-71-kk-credit-review");
  });
});
