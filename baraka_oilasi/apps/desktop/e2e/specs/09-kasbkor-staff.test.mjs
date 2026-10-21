// Kasb-kor xodim va ta'minotchi kelishuvlari (K6, kasbkor/SPEC 7), haqiqiy ilovada. Sardor: haq 3 000 000,
// kelishuv imzolanadi, 1 000 000 avans foizsiz 2 oyda ushlanadi. Ulgurji baza: shakar 12 500 dan qotirilgan,
// 30 kunlik muddat; 100 kg yetkazildi (qoldiqqa kirdi), 500 000 to'landi. 35 kundan keyin: qarz kechikdi
// (jarimasiz), xodimga o'tgan oy haqi to'lanadi, varaqcha PDF.
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

async function card(app, id) {
  const el = await app.testId(id);
  await el.waitForDisplayed();
  return el;
}

describe("Kasb-kor: xodimlar va ta'minotchilar", () => {
  let app;
  let profile;
  before(async () => {
    app = await startApp();
    profile = app.dir;
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`kkst-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("T1. Sardor: kelishuv, imzo, avans (foizsiz, 2 oyda)", async () => {
    await onboard(app, { household: "Bahodirlar oilasi", name: "Bahodir", spaces: ["Kasb-kor"], rhythm: "Har kuni naqd" });
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await app.waitText("Haqiqiy foyda (shu oy)");
    await app.nav("Xodimlar");
    await app.waitText("yurist koʻrigidan oʻtmagan");
    await app.click("Yangi xodim");
    const form = await app.region("Yangi xodim", "form");
    await app.type("Ism", "Sardor", form);
    await app.type("Lavozim", "Sotuvchi", form);
    await app.type("Vazifalar", "Savdo va kassa", form);
    await app.type("Oylik haq", "3 000 000", form);
    await app.type("Avans qoldigʻi chegarasi (ixtiyoriy)", "1 500 000", form);
    await app.click("Xodimni qoʻshish", form);
    await form.waitForExist({ reverse: true });
    const c = await card(app, "kk-employee-Sardor");
    await app.click("Imzolash", c);
    const sign = await app.region("Sardor: imzolash", "form");
    await app.click("Imzolandi deb yozish", sign);
    await sign.waitForExist({ reverse: true });
    await waitIn(await c.$('[data-testid="kk-employee-status"]'), "1-versiya", "imzo");
    await app.click("Avans", c);
    const adv = await app.region("Sardor: avans", "form");
    await app.type("Summa", "1 000 000", adv);
    await app.selectText("Necha oyda ushlanadi", "2 oyda", adv);
    await app.click("Avansni yozish", adv);
    await adv.waitForExist({ reverse: true });
    // Shu oy haqidan birinchi ulush (500 000) ushlandi.
    await waitIn(await app.testId("kk-staff-advances"), "500 000", "ushlanmagan avans");
    await noAxe(app, "kk-staff");
    await app.shot("desktop-76-kk-staff");
    await app.click("Sardor — kelishuv PDF", c);
    await app.b.waitUntil(() => app.saved().includes("kelishuv.pdf"), { timeout: 15000, timeoutMsg: "kelishuv PDF saqlanmadi" });
  });

  it("T2. Ulgurji baza: shakar 12 500 dan, 100 kg nasiyaga, 500 000 to'landi", async () => {
    await app.nav("Tovarlar");
    await app.click("Yangi tovar");
    const item = await app.region("Yangi tovar", "form");
    await app.type("Nomi", "Shakar", item);
    await app.click("Tovarni qoʻshish", item);
    await card(app, "kk-item-Shakar");
    await app.nav("Taʼminotchilar");
    await app.click("Yangi taʼminotchi");
    const form = await app.region("Yangi taʼminotchi", "form");
    await app.type("Nomi", "Ulgurji baza", form);
    await app.selectText("Tovar qoldigʻidagi tovar", "Shakar", form);
    await app.type("Qotirilgan narx (1 kg)", "12 500", form);
    await app.click("Taʼminotchini qoʻshish", form);
    await form.waitForExist({ reverse: true });
    const c = await card(app, "kk-supplier-Ulgurji baza");
    await app.click("Imzolash", c);
    const sign = await app.region("Ulgurji baza: imzolash", "form");
    await app.click("Imzolandi deb yozish", sign);
    await sign.waitForExist({ reverse: true });
    await app.click("Yetkazish", c);
    const del = await app.region("Ulgurji baza: yetkazish", "form");
    await app.type("Miqdor (kg)", "100", del);
    await app.click("Saqlash", del);
    await del.waitForExist({ reverse: true });
    await waitIn(await app.testId("kk-supply-outstanding"), "1 250 000", "qarz");
    await app.click("Toʻlov", c);
    const pay = await app.region("Ulgurji baza: toʻlov", "form");
    await app.type("Summa", "500 000", pay);
    await app.click("Saqlash", pay);
    await pay.waitForExist({ reverse: true });
    await waitIn(await app.testId("kk-supply-outstanding"), "750 000", "qarz");
    await noAxe(app, "kk-suppliers");
    await app.shot("desktop-77-kk-suppliers");
    await app.nav("Tovarlar");
    await waitIn(await (await card(app, "kk-item-Shakar")).$('[data-testid="kk-item-qty"]'), "100 kg", "qoldiq");
    await app.nav("Bosh sahifa");
    await waitIn(await app.testId("kk-payables"), "750 000", "bosh sahifa qarzi");
    await noAxe(app, "kk-home-obligations");
    await app.shot("desktop-78-kk-home-obligations");
  });

  it("T3. 35 kundan keyin: qarz kechikdi (jarimasiz), haq to'lanadi, varaqcha", async () => {
    await app.stop();
    app = await startApp({ profile, shiftDays: 35 });
    await unlock(app);
    await app.click("Kasb-kor", await app.region("Makonlar"));
    await app.nav("Taʼminotchilar");
    await waitIn(await app.testId("kk-supply-overdue"), "750 000", "kechikkan");
    const s = await card(app, "kk-supplier-Ulgurji baza");
    assert.match(await s.getText(), /Jarima yoʻq/);
    assert.ok((await app.text("kk-supply-outstanding")).includes("750 000"), "jarima qo'shilmagan");
    await app.nav("Xodimlar");
    const c = await card(app, "kk-employee-Sardor");
    const due = await (await c.$('[data-testid="kk-employee-due"]')).getText();
    assert.notEqual(due.replace(/\s/g, ""), "0soʻm", "o'tgan oy haqi to'lanadigan bo'lishi kerak");
    await app.click("Haq toʻlash", c);
    const pay = await app.region("Sardor: haq toʻlash", "form");
    await app.click("Saqlash", pay);
    await pay.waitForExist({ reverse: true });
    await waitIn(await c.$('[data-testid="kk-employee-due"]'), "0 soʻm", "to'langan");
    await (await c.$(".//summary[contains(., 'Oylik hisob')]")).click();
    const slip = await c.$(".//button[normalize-space()='Varaqcha']");
    await slip.waitForClickable();
    await slip.click();
    await app.b.waitUntil(() => app.saved().includes("varaqcha.pdf"), { timeout: 15000, timeoutMsg: "varaqcha PDF saqlanmadi" });
    await noAxe(app, "kk-staff-paid");
    await app.shot("desktop-79-kk-staff-paid");
  });
});
