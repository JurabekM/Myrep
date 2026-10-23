// Kasb-kor «Hisob kuni» (K3, kasbkor/SPEC 4.5), haqiqiy ilovada. A — joriy oyda Feruza atelyesi:
// tushum 18 mln, chiqimlar 9,7 mln (shu jumladan qiziga to'langan 1,2 mln), maosh 5 mln «egasi oldi».
// B — ilova keyingi oyning 5-kuniga siljitilgan yadro soati bilan qayta ochiladi: bosh sahifada
// eslatma → soliq zaxirasi 4 % tushumdan → qolgan 2 580 000 → 774 000 / 1 290 000 / 516 000 →
// oy yopiladi, bayonnoma PDF. Har ekran axe bilan.
import assert from "node:assert/strict";
import { after, afterEach, before, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard, unlock } from "../lib/flows.mjs";

/** Bugundan keyingi oyning 5-kunigacha kunlar (yadro soati siljishi). */
function daysToNextMonth() {
  const now = new Date();
  const target = new Date(now.getFullYear(), now.getMonth() + 1, 5, 12);
  return Math.round((target - now) / 86400000);
}

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

async function waitValue(app, id, fragment) {
  await app.b.waitUntil(async () => (await app.text(id)).includes(fragment), { timeout: 15000, timeoutMsg: `${id}: ${fragment} yo'q` });
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

describe("Kasb-kor: Hisob kuni", () => {
  let app;
  let profile;
  before(async () => {
    app = await startApp();
    profile = app.dir;
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`kkc-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("C1. joriy oy: tushum, chiqimlar, maosh va «egasi oldi»", async () => {
    await onboard(app, { household: "Feruzalar oilasi", name: "Feruza", spaces: ["Kasb-kor"], rhythm: "Buyurtma boʻyicha" });
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await app.waitText("Haqiqiy foyda (shu oy)");
    await entry(app, "Tushum", { amount: "18 000 000", wallet: "Karta" });
    await entry(app, "Chiqim", { amount: "6 000 000", wallet: "Karta", category: "Material va xomashyo" });
    await entry(app, "Chiqim", { amount: "2 000 000", wallet: "Karta", category: "Ijara (ustaxona, doʻkon)" });
    await entry(app, "Chiqim", { amount: "500 000", wallet: "Karta", category: "Boshqa" });
    await entry(app, "Chiqim", { amount: "1 200 000", wallet: "Karta", category: "Ishchilar haqi" });
    await app.click("Maosh belgilash");
    await app.type("Oylik maosh", "5 000 000");
    await app.click("Saqlash", await app.region("Egasining maoshi", "section"));
    await entry(app, "Egasi oldi", { amount: "5 000 000", wallet: "Karta" });
    await waitValue(app, "kk-cash-flow", "8 300 000");
    assert.equal(await (await app.testId("kk-close-due")).isExisting(), false, "joriy oyda eslatma yo'q");
  });

  it("C2. keyingi oy: bosh sahifada «Hisob kuni» eslatmasi", async () => {
    await app.stop();
    app = await startApp({ profile, shiftDays: daysToNextMonth() });
    await unlock(app);
    await app.click("Kasb-kor", await app.region("Makonlar"));
    const due = await app.testId("kk-close-due");
    await due.waitForDisplayed();
    await noAxe(app, "kk-home-close-due");
    await app.click("Hisob kuni", due);
    await app.waitText("1. Oy yakunlari");
  });

  it("C3. soliq zaxirasi 4 % tushumdan → qolgan 2 580 000 va taqsimot", async () => {
    await app.click("Oʻzgartirish", await app.region("Qoidalar", "section"));
    const form = await app.region("Qoidalarni oʻzgartirish", "form");
    await app.choose("Tushumdan foiz", form);
    await app.type("Foiz (%)", "4", form);
    await app.click("Saqlash", form);
    await form.waitForExist({ reverse: true });
    await waitValue(app, "kk-close-tax", "720 000");
    await waitValue(app, "kk-close-remaining", "2 580 000");
    assert.ok((await app.text("kk-close-reserve")).includes("774 000"));
    assert.ok((await app.text("kk-close-working")).includes("1 290 000"));
    assert.ok((await app.text("kk-close-expansion")).includes("516 000"));
    await noAxe(app, "kk-close-draft");
    await app.shot("desktop-67-kk-close-draft");
  });

  it("C4. oy yopiladi: bayonnoma, tekshirish kodi va PDF", async () => {
    await app.click("Oyni yopish");
    await app.waitText("Oʻtgan oy yopilgan");
    await app.b.waitUntil(async () => !(await (await app.testId("kk-close-remaining")).isExisting()), { timeout: 15000, timeoutMsg: "qoralama qoldi" });
    const history = await app.region("Bayonnomalar", "section");
    assert.match(await history.getText(), /[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}/);
    const pdf = await history.$(".//button[starts-with(@aria-label, 'PDF saqlash')]");
    await pdf.click();
    await app.b.waitUntil(() => app.saved().some((f) => f.endsWith(".pdf")), { timeout: 15000, timeoutMsg: "PDF saqlanmadi" });
    await noAxe(app, "kk-close-done");
    await app.shot("desktop-68-kk-close-done");
  });

  it("C5. bosh sahifada eslatma yo'q", async () => {
    await app.nav("Bosh sahifa");
    await app.waitText("Haqiqiy foyda (shu oy)");
    await app.b.waitUntil(async () => !(await (await app.testId("kk-close-due")).isExisting()), { timeout: 15000, timeoutMsg: "eslatma qoldi" });
  });
});
