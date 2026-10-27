// Kasb-kor «O'zimga sarmoya» (K9, kasbkor/SPEC 8A), haqiqiy ilovada. A — joriy oyda Feruza atelyesi
// (3.1 misoli): tushum 18 mln, chiqimlar 8,5 mln (shundan 500 000 — «Sarmoya (o'qish)» belgili),
// o'z mehnati 5 mln, qizining 80 soati × 15 000, tikuv mashinalari 12 mln / 60 oy → haqiqiy foyda
// 3 100 000. B — ilova keyingi oyga siljitilib qayta ochiladi: «Hisob kuni»da «Sarmoya (o'qish)»
// alohida qator, oy yopiladi → egasi topgani 8 100 000 (maosh qo'shilmaydi), 10 soat × 26 kun →
// 31 153,85 → «O'zim qilaymi yoki o'rgatib topshiraymi?»: yordamchi 15 000, 20 soat, o'rgatish
// 500 000 + 10 soat → 3 oyda qoplanadi; 40 000 — «hozircha o'zingiz qilganingiz arzon» → «Ilm
// zakoti» → kurs tekshiruvi COURSE turida. Har ekran axe bilan.
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

async function waitIn(app, el, fragment) {
  await app.b.waitUntil(async () => (await el.getText()).includes(fragment), { timeout: 15000, timeoutMsg: `yo'q: ${fragment}` });
}

async function entry(app, action, { amount, wallet, category, invest = false }) {
  if (action === "Tushum") await app.b.keys(["Control", "n"]);
  else await app.click(action, await app.region("Yozuv qoʻshish"));
  const dialog = await app.x("//div[@role='dialog']");
  await app.type("Summa", amount, dialog);
  if (category) await app.selectText("Kategoriya", category, dialog);
  if (invest) await app.choose("Sarmoya (oʻqish)", dialog);
  if (wallet) await app.click(wallet, dialog);
  await app.click("Saqlash", dialog);
  await dialog.waitForExist({ reverse: true });
}

describe("Kasb-kor: Oʻzimga sarmoya", () => {
  let app;
  let profile;
  before(async () => {
    app = await startApp();
    profile = app.dir;
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`kkls-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("S1. joriy oy: tushum, chiqimlar («Sarmoya (o'qish)» bilan), o'z mehnati, oilaviy mehnat, uskuna", async () => {
    await onboard(app, { household: "Feruzalar oilasi", name: "Feruza", spaces: ["Kasb-kor"], rhythm: "Buyurtma boʻyicha" });
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await app.waitText("Haqiqiy foyda (shu oy)");
    await entry(app, "Tushum", { amount: "18 000 000", wallet: "Karta" });
    await entry(app, "Chiqim", { amount: "6 000 000", wallet: "Karta", category: "Material va xomashyo" });
    await entry(app, "Chiqim", { amount: "2 000 000", wallet: "Karta", category: "Ijara (ustaxona, doʻkon)" });
    await entry(app, "Chiqim", { amount: "500 000", wallet: "Karta", category: "Boshqa", invest: true });
    await waitValue(app, "kk-cash-flow", "9 500 000");
    await app.click("Bahoni kiritish");
    await app.type("Oʻz mehnatingiz bahosi (oyiga)", "5 000 000");
    await app.click("Saqlash", await app.region("Foyda qanday hosil boʻldi", "section"));
    await app.nav("Oilaviy mehnat");
    const labor = await app.region("Mehnat yozish", "form");
    await app.type("Kim", "Qizi", labor);
    await app.type("Soat", "80", labor);
    await app.type("Soat bahosi", "15 000", labor);
    await app.click("Yozish", labor);
    await waitValue(app, "kk-family-labor", "1 200 000");
    await app.nav("Uskunalar");
    const eq = await app.region("Uskuna qoʻshish", "form");
    await app.type("Nomi", "Tikuv mashinalari (2 ta)", eq);
    await app.type("Narxi", "12 000 000", eq);
    await app.type("Foydali muddat (oy)", "60", eq);
    await app.click("Karta", eq);
    await app.click("Qoʻshish", eq);
    await waitValue(app, "kk-eq-dep-Tikuv mashinalari (2 ta)", "200 000");
    await app.nav("Bosh sahifa");
    await waitValue(app, "kk-true-profit", "3 100 000");
  });

  it("S2. keyingi oy: «Hisob kuni»da «Sarmoya (o'qish)» qatori, oy yopiladi", async () => {
    await app.stop();
    app = await startApp({ profile, shiftDays: daysToNextMonth() });
    await unlock(app);
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await app.nav("Hisob kuni");
    await app.waitText("1. Oy yakunlari");
    await waitValue(app, "kk-close-self-investment", "500 000");
    await noAxe(app, "kk-close-self-investment");
    await app.click("Oyni yopish");
    await app.waitText("Oʻtgan oy yopilgan");
    const history = await app.region("Bayonnomalar", "section");
    await waitIn(app, history, "500 000");
  });

  it("S3. egasining bir soati: yopilgan oydan 8 100 000, 10 soat × 26 kun → 31 153,85", async () => {
    await app.nav("Oʻzimga sarmoya");
    const card = await app.testId("kkl-hour");
    await card.waitForDisplayed();
    await waitIn(app, card, "topgani 8 100 000 soʻm");
    assert.match(await card.getText(), /maosh qoʻshilmaydi/);
    await app.type("Kuniga soat", "10", card);
    await app.type("Kuniga daqiqa", "0", card);
    await app.type("Oyda ish kunlari", "26", card);
    await app.click("Hisoblash va saqlash", card);
    await waitValue(app, "kkl-hour-value", "31 153,85 soʻm");
    const fresh = await app.testId("kkl-hour");
    assert.match(await fresh.getText(), /yopilgan oylar oʻrtachasi \(1 oy\)/);
    assert.ok((await app.text("kkl-self-investment")).includes("0 soʻm"), "yangi oyda hali sarmoya yo'q");
    await noAxe(app, "kk-learning-hour");
    await app.b.execute(() => document.querySelector('[data-testid="kkl-hour"]')?.scrollIntoView({ block: "start" }));
    await app.shot("desktop-107-kk-learning-hour");
  });

  it("S4. o'zim qilaymi yoki o'rgatib topshiraymi: 3 oyda qoplanadi; qimmat yordamchi — o'zingiz arzon", async () => {
    const form = await app.region("Oʻzim qilaymi yoki oʻrgatib topshiraymi?", "form");
    await app.type("Ish turi", "Mato qabul qilish", form);
    await app.type("Yordamchi yoki xodimning 1 soati narxi", "15 000", form);
    await app.type("Bu ishga oyiga, soat", "20", form);
    await app.type("Oʻrgatishga ketadigan vaqtingiz, soat", "10", form);
    await app.type("Bir martalik oʻrgatish xarajati (ixtiyoriy)", "500 000", form);
    await app.click("Hisoblash", form);
    await waitValue(app, "kkl-payback", "3 oy");
    assert.ok((await app.text("kkl-benefit")).includes("323 077"));
    assert.ok((await app.text("kkl-full-cost")).includes("811 538,50"));
    await noAxe(app, "kk-delegate");
    await app.b.execute(() => document.querySelector('[data-testid="kkl-delegate-result"]')?.scrollIntoView({ block: "center" }));
    await app.shot("desktop-108-kk-delegate");

    await app.type("Yordamchi yoki xodimning 1 soati narxi", "40 000", form);
    await app.click("Hisoblash", form);
    await waitValue(app, "kkl-verdict", "Hozircha oʻzingiz qilganingiz arzon");
    assert.equal(await (await app.testId("kkl-payback")).isExisting(), false);
    await app.type("Yordamchi yoki xodimning 1 soati narxi", "15 000", form);
    await app.click("Qarorni saqlash", form);
    await (await app.region("Qaror: Mato qabul qilish")).waitForDisplayed();
  });

  it("S5. «Ilm zakoti» va kurs tekshiruvi", async () => {
    await app.click("Oʻrgatganimni yozish");
    const d = await app.region("Ilm zakoti: oʻrgatish yozuvi");
    await app.type("Nimani oʻrgatdi", "Narx yorligʻi yozish", d);
    await app.type("Ism (ixtiyoriy)", "Qizi", d);
    await app.click("Saqlash", d);
    await d.waitForExist({ reverse: true });
    await waitValue(app, "kkl-teach-count", "1 marta");
    await app.waitText("kimga: Qizi");
    await noAxe(app, "kk-learning-teach");
    await app.b.execute(() => document.querySelector('[data-testid="kkl-teach-count"]')?.scrollIntoView({ block: "center" }));
    await app.shot("desktop-109-kk-learning-teach");
    await app.click("Kursni tekshirish");
    await app.waitText("Qisqa muddatda boylik yoki katta daromad vaʼda qilinyaptimi?");
  });
});
