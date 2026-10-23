// Zaxira pul, ish boshlash summasi va qaror natijasi (M4, musofir/SPEC 6.4, 6.6). Bobur aka: Musofir (KRW,
// maqsad 120 mln so'm) → o'tgan 2 oy: maosh va 800 000 von xarajat → zaxira pul boshlang'ich 500 000 →
// shu oy maosh: ulush 520 000 = 300 000 zaxira pulga + 220 000 jamg'armaga → zaxira pul to'la → kasalxona
// uchun 200 000 olindi (ulush kamaymaydi) → «Hunardan ishga»da «Tikuv sexi» (30 mln) → ish boshlash summasi:
// yashash uchun 90 mln → qarz so'rovi rad etildi va natijasi «qilmadim».
import assert from "node:assert/strict";
import { after, afterEach, before, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard } from "../lib/flows.mjs";

const pad = (n) => String(n).padStart(2, "0");
const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/** `k` oy oldingi oyning 20-kuni (ISO). */
function monthsAgo(k) {
  const d = new Date();
  return iso(new Date(d.getFullYear(), d.getMonth() - k, 20));
}

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

async function waitValue(app, id, fragment) {
  await app.b.waitUntil(async () => (await app.text(id)).includes(fragment), { timeout: 15000, timeoutMsg: `${id}: ${fragment} yo'q` });
}

async function scrollTo(app, label) {
  await app.b.execute((l) => document.querySelector(`[aria-label="${l}"]`)?.scrollIntoView(), label);
}

async function entry(app, action, within, { amount, date, note }) {
  if (action) await app.click(action, within ?? (await app.region("Yozuv qoʻshish")));
  const dialog = await app.x("//div[@role='dialog']");
  if (amount) await app.type("Summa (KRW)", amount, dialog);
  if (date) await app.setDate("Sana (boʻsh — bugun)", date, dialog);
  if (note) await app.type(action === "Zaxira puldan" ? "Sabab" : "Izoh", note, dialog);
  await app.click("Saqlash", dialog);
  await dialog.waitForExist({ reverse: true });
}

describe("Musofir: zaxira pul va ish boshlash summasi", () => {
  let app;
  before(async () => {
    app = await startApp();
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`mfq-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("Q1. sozlash va o'tgan 2 oy: maosh va xarajat — zaxira pul maqsadi", async () => {
    await onboard(app, { household: "Bobur akaning oilasi", name: "Bobur", spaces: ["Musofir"], rhythm: "Oylik maosh" });
    await app.click("Musofir", await app.region("Makonlar"));
    const form = await app.region("Musofir makonini sozlash", "form");
    await app.selectText("Ish valyutasi", "Koreya voni (KRW)", form);
    await app.type("Qaytish jamgʻarmasi maqsadi (soʻmda)", "120 000 000", form);
    await app.click("Saqlash", form);
    await (await app.testId("mf-fund")).waitForDisplayed();
    await waitValue(app, "mf-reserve-status", "Bir oy xarajatlarni yozing");
    for (const k of [2, 1]) {
      await app.b.keys(["Control", "n"]);
      await entry(app, null, null, { amount: "2 600 000", date: monthsAgo(k) });
      await app.click("Keyinroq");
      await entry(app, "Xarajat", null, { amount: "800 000", date: monthsAgo(k) });
    }
    // Ikki oy o'rtachasi 800 000 — 1 oylik maqsad; zaxira pul bo'sh.
    await waitValue(app, "mf-reserve-status", "Zaxira pul boʻsh");
    assert.match(await app.text("mf-reserve-status"), /800 000 KRW kerak/);
  });

  it("Q2. ulush avval zaxira pulga, qolgani jamg'armaga", async () => {
    await entry(app, "Zaxira pul (boshlangʻich)", await app.region("Zaxira pul yozuvlari"), { amount: "500 000" });
    await waitValue(app, "mf-reserve-status", "Yana 300 000 KRW");
    await app.b.keys(["Control", "n"]);
    await entry(app, null, null, { amount: "2 600 000" });
    await waitValue(app, "mf-offer", "300 000 KRW — zaxira pulga, 220 000 KRW — qaytish jamgʻarmasiga");
    await noAxe(app, "mf-offer-split");
    await app.shot("desktop-99-mf-offer-split");
    await app.click("Zaxira pulga qoʻyish");
    let dialog = await app.x("//div[@role='dialog']");
    assert.equal(await (await app.field("Summa (KRW)", dialog)).getValue(), "300000");
    await app.click("Saqlash", dialog);
    await dialog.waitForExist({ reverse: true });
    await app.click("Jamgʻarmaga qoʻyish");
    dialog = await app.x("//div[@role='dialog']");
    assert.equal(await (await app.field("Summa (KRW)", dialog)).getValue(), "220000");
    await app.click("Saqlash", dialog);
    await dialog.waitForExist({ reverse: true });
    await waitValue(app, "mf-reserve", "800 000 KRW");
    await waitValue(app, "mf-reserve-status", "Zaxira pul toʻla");
    await waitValue(app, "mf-share", "520 000");
  });

  it("Q3. kasalxona: zaxira puldan 200 000 — ulush kamaymaydi", async () => {
    await entry(app, "Zaxira puldan", await app.region("Zaxira pul yozuvlari"), { amount: "200 000", note: "Kasalxona" });
    await waitValue(app, "mf-reserve-status", "Yana 200 000 KRW");
    await waitValue(app, "mf-share", "520 000");
    assert.equal(await (await app.testId("mf-share-gap")).isExisting(), false);
    await noAxe(app, "mf-reserve");
    await scrollTo(app, "Zaxira pul");
    await app.shot("desktop-100-mf-reserve");
  });

  it("Q4. «Hunardan ishga»: Tikuv sexi 30 mln → ish boshlash summasi", async () => {
    await app.click("«Hunardan ishga»ni ochish", await app.region("Qaytgandan keyin ish", "section"));
    await app.click("Yangi gʻoya");
    const form = await app.region("Gʻoya hisobi", "form");
    await app.type("Gʻoya nomi", "Tikuv sexi", form);
    await app.type("1-narsa", "Tikuv mashinalari", form);
    await app.type("1-narsa narxi", "30 000 000", form);
    for (const label of ["Oylik kirim", "Oylik xarajat"]) {
      const inputs = await form.$$(`.//label[.//span[normalize-space()='${label}']]//input`);
      for (const [i, el] of inputs.entries()) {
        await el.setValue(label === "Oylik kirim" ? ["5 000 000", "7 000 000", "9 000 000"][i] : "4 000 000");
      }
    }
    await app.click("Hisoblash va saqlash", form);
    await form.waitForExist({ reverse: true });

    await app.click("Musofir", await app.region("Makonlar"));
    await app.nav("Bosh sahifa");
    const card = await app.region("Qaytgandan keyin ish", "section");
    await app.click("Ish boshlash summasini belgilash", card);
    const sf = await app.region("Ish boshlash summasi", "form");
    // G'oyalar Uy makonidan yuklanadi.
    const idea = await app.field("«Hunardan ishga» gʻoyasi", sf);
    await idea.waitUntil(async () => (await idea.getText()).includes("Tikuv sexi"), { timeout: 15000, timeoutMsg: "g'oya yo'q" });
    // Summa matnida bo'linmas bo'shliqlar bor — tartib raqami bilan (0 — «g'oyasiz»).
    await idea.selectByIndex(1);
    assert.equal(await (await app.field("Ish boshlash summasi (UZS)", sf)).getValue(), "30000000");
    await app.click("Saqlash", sf);
    await waitValue(app, "mf-startup", "Yashash uchun: 90 000 000 soʻm (ish boshlash — maqsadning 25 %i)");
    assert.match(await app.text("mf-startup"), /Tikuv sexi/);
    await noAxe(app, "mf-startup");
  });

  it("Q5. qarz so'rovi: rad etaman → natija «qilmadim»", async () => {
    const card = await app.region("Qaytish va sovutish davri", "section");
    await app.click("Katta qarorni tekshirish", card);
    const dialog = await app.x("//div[@role='dialog']");
    await app.type("Nima haqida", "Qoʻshniga qarz", dialog);
    await app.type("Summa (UZS)", "5 000 000", dialog);
    for (const q of ["qaytganingizdan keyin", "Avval pul", "Chet elga", "Qaytarish muddati", "Oila bilan"]) {
      const group = await dialog.$(`.//div[@role='radiogroup'][.//p[contains(., "${q}")]]`);
      await group.waitForDisplayed();
      await app.choose("Yoʻq", group);
    }
    await app.click("Tekshirish", dialog);
    const result = await app.testId("mf-decision-result");
    await result.waitForDisplayed();
    await app.click("Rad etaman", result);
    await dialog.waitForExist({ reverse: true });
    await app.click("Qilmadim", await app.region("Natija qanday boʻldi?"));
    await waitValue(app, "mf-decision-outcome", "Natija: qilmadim");
    await noAxe(app, "mf-outcome");
    await scrollTo(app, "Qaytgandan keyin ish");
    await app.shot("desktop-101-mf-startup-outcome");
  });
});
