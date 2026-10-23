// Yo'l qarzi, «Qaytdim» va sovutish davri (M3, musofir/SPEC 6). Bobur aka: onboarding'da «qarzim bor» →
// Uy makonida tog'asidan yo'l qarzi 15 000 000 → Musofir: KRW, shartlar 50/30/20 → uyga 1 200 000 von
// (uyda 10 900 000) → «Ikki qirg'oq»: qabul, «Qarz to'lovi» maqsadidan tog'aga 3 270 000 → Musofir bosh
// sahifasi: yo'l qarzi belgilanadi, 6 oyda yopish uchun oyiga 1 955 000 → «Qaytdim» (9 kun oldin,
// 120 mln olib keldi) → tog'a 15 mln qarz so'raydi: sariq, kutish sanasi → «Kutaman» jurnalga.
import assert from "node:assert/strict";
import { after, afterEach, before, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard } from "../lib/flows.mjs";

const pad = (n) => String(n).padStart(2, "0");
const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/** Bugundan `shift` kun keyin, `DD.MM.YYYY` (qarz jadvali maydoni). */
function day(shift) {
  const d = new Date();
  d.setDate(d.getDate() + shift);
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

function isoDaysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return iso(d);
}

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

async function waitIn(el, fragment, what) {
  await el.waitUntil(async () => (await el.getText()).includes(fragment), { timeout: 15000, timeoutMsg: `${what}: ${fragment} yo'q` });
}

async function scrollTo(app, label) {
  await app.b.execute((l) => document.querySelector(`[aria-label="${l}"]`)?.scrollIntoView(), label);
}

describe("Musofir: yo'l qarzi va sovutish davri", () => {
  let app;
  before(async () => {
    app = await startApp();
  });
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`mfr-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("R1. Uy makonida yo'l qarzi: tog'adan 15 000 000", async () => {
    await onboard(app, { household: "Bobur akaning oilasi", name: "Bobur", members: [{ name: "Mohira" }], spaces: ["Musofir"], rhythm: "Oylik maosh", debts: true });
    await app.click("Qarz qoʻshish");
    const form = await app.region("Qarz qoʻshish", "form");
    await app.type("Kreditor (ism yoki bank)", "Togʻam", form);
    await app.type("Hozirgi qoldiq", "15 000 000", form);
    await app.type("Sababi", "Koreyaga yoʻl va viza", form);
    await app.type("Sana 1", day(40), form);
    await app.type("Summa 1", "15 000 000", form);
    await app.click("Saqlash", form);
    await app.region("Togʻam", "article");
  });

  it("R2. Musofir: sozlash, shartlar va uyga yuborish", async () => {
    await app.click("Musofir", await app.region("Makonlar"));
    const setup = await app.region("Musofir makonini sozlash", "form");
    await app.selectText("Ish valyutasi", "Koreya voni (KRW)", setup);
    await app.click("Saqlash", setup);
    await (await app.testId("mf-fund")).waitForDisplayed();
    // Uyda qarz bor, lekin hali belgilanmagan.
    const travel = await app.region("Yoʻl qarzi", "section");
    await waitIn(travel, "Yoʻlga olingan qarzni belgilang", "yo'l qarzi");

    await app.click("Shartlarni belgilash", await app.region("Ikki qirgʻoq: oila bilan kelishuv", "section"));
    const terms = await app.region("Ikki qirgʻoq shartlari", "form");
    await app.type("Uy xarajati, foiz", "50", terms);
    await app.type("Qarz toʻlovi, foiz", "30", terms);
    await app.type("Qurilish va taʼmir, foiz", "20", terms);
    await app.click("Saqlash", terms);
    await waitIn(await app.testId("mf-terms-shares"), "Qarz toʻlovi 30 %", "shartlar");

    await app.click("Uyga yuborish", await app.region("Yozuv qoʻshish"));
    const dialog = await app.x("//div[@role='dialog']");
    await app.type("Summa (KRW)", "1 200 000", dialog);
    await app.type("Uyda olingan summa (UZS)", "10 900 000", dialog);
    await app.click("Saqlash", dialog);
    await dialog.waitForExist({ reverse: true });
  });

  it("R3. Ikki qirg'oq: qabul va «Qarz to'lovi» maqsadidan tog'aga to'lov", async () => {
    await app.click("Uy", await app.region("Makonlar"));
    await app.nav("Ikki qirgʻoq");
    await app.click("Qabul qildim", await app.region("Qabul qilish", "form"));
    await waitIn(await app.testId("mf-purpose-DEBT"), "3 270 000", "qarz maqsadi");
    const spend = await app.region("Maqsad boʻyicha xarajat", "form");
    await app.selectText("Maqsad", "Qarz toʻlovi", spend);
    // Uy qarzlari maqsad tanlangach yuklanadi; yagona faol qarz — tanlangan.
    await waitIn(await app.field("Qaysi qarz", spend), "Togʻam · 15 000 000 soʻm", "qarz tanlovi");
    await app.type("Summa", "3 270 000", spend);
    await app.click("Qarzni toʻlash", spend);
    await waitIn(await app.testId("mf-spend"), "kimga: Togʻam", "to'lov");
    const debt = await app.testId("mf-purpose-DEBT");
    assert.match(await debt.getText(), /3 270 000 soʻm\s*3 270 000 soʻm\s*0 soʻm$/);
    await noAxe(app, "home-debt-payment");
    await scrollTo(app, "Maqsad boʻyicha xarajat");
    await app.shot("desktop-95-home-debt-payment");
  });

  it("R4. Musofir: yo'l qarzi belgilanadi — 6 oyda yopish rejasi", async () => {
    await app.click("Musofir", await app.region("Makonlar"));
    await app.nav("Bosh sahifa");
    const travel = await app.region("Yoʻl qarzi", "section");
    await app.click("Yoʻl qarzini belgilash", travel);
    const form = await app.region("Yoʻl qarzi sozlamasi", "form");
    assert.equal(await (await app.field("Necha oyda yopmoqchisiz", form)).getValue(), "6");
    await app.click("Saqlash", form);
    await waitIn(await app.testId("mf-travel-remaining"), "11 730 000", "qolgan");
    assert.match(await app.text("mf-travel-status"), /oyiga 1 955 000 soʻm kerak/);
    await noAxe(app, "mf-travel-debt");
    await scrollTo(app, "Yoʻl qarzi");
    await app.shot("desktop-96-mf-travel-debt");
  });

  it("R5. «Qaytdim» va katta qaror: tog'a 15 mln qarz so'raydi — sariq, kutaman", async () => {
    const card = await app.region("Qaytish va sovutish davri", "section");
    await app.click("Qaytdim", card);
    const form = await app.region("Qaytish", "form");
    await app.setDate("Qaytgan sana", isoDaysAgo(9), form);
    await app.type("Olib kelingan summa (UZS)", "120 000 000", form);
    await app.click("Saqlash", form);
    await waitIn(await app.testId("mf-cooling"), "yana 81 kun", "sovutish davri");

    await app.click("Katta qarorni tekshirish", card);
    const dialog = await app.x("//div[@role='dialog']");
    await app.type("Nima haqida", "Togʻamga qarz (doʻkon uchun)", dialog);
    await app.type("Summa (UZS)", "15 000 000", dialog);
    for (const [q, reply] of [
      ["qaytganingizdan keyin", "Ha"],
      ["Avval pul", "Yoʻq"],
      ["Chet elga", "Yoʻq"],
      ["Qaytarish muddati", "Yoʻq"],
      ["Oila bilan", "Ha"],
    ]) {
      const group = await dialog.$(`.//div[@role='radiogroup'][.//p[contains(., "${q}")]]`);
      await group.waitForDisplayed();
      await app.choose(reply, group);
    }
    await app.click("Tekshirish", dialog);
    const result = await app.testId("mf-decision-result");
    await waitIn(result, "Sariq: kuting va aniqlang", "natija");
    assert.match(await result.getText(), /olib kelinganning 12,5 %i/);
    assert.match(await result.getText(), /Kutish sanasi:/);
    await noAxe(app, "mf-decision");
    await result.scrollIntoView();
    await app.shot("desktop-97-mf-decision-check");
    await app.click("Kutaman", result);
    await dialog.waitForExist({ reverse: true });
    const row = await app.testId("mf-decision");
    await waitIn(row, "Kutaman", "jurnal");
    assert.match(await row.getText(), /Sariq/);
    await noAxe(app, "mf-cooling");
    await scrollTo(app, "Qaytish va sovutish davri");
    await app.shot("desktop-98-mf-cooling");
  });
});
