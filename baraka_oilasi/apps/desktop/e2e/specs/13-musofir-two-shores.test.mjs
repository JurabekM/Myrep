// «Ikki qirg'oq» (M2, musofir/SPEC 5, ADR-0004), ikki haqiqiy ilova bilan.
// Musofir (Rustam aka, xonadon egasi): sozlash → shartlar 50/30/20, Gulnora qabul qiladi → uyga 1 200 000 von
// (uyda 10 900 000 so'm) → «Uydagi oila qurilmasi» ulash fayli. Oila qurilmasi: Musofir makoni ko'rinmaydi,
// «Ikki qirg'oq»da yo'ldagi pul → qabul (Gulnora) → uy xarajati 5 450 000 dan 2 000 000 sarflandi →
// kelishuvni Gulnora tasdiqlaydi → fayl musofirga. Musofir: uyda maqsadlar qoldig'i, Gulnora tasdiqlagan.
import assert from "node:assert/strict";
import { copyFileSync } from "node:fs";
import { join } from "node:path";
import { after, afterEach, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard } from "../lib/flows.mjs";

const PASSWORD = "Ikki-qirgoq-2026!";
const HOME_PIN = "135790";

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

async function waitIn(el, fragment, what) {
  await el.waitUntil(async () => (await el.getText()).includes(fragment), { timeout: 15000, timeoutMsg: `${what}: ${fragment} yo'q` });
}

async function top(app) {
  await app.b.execute(() => document.getElementById("main")?.scrollTo(0, 0));
}

function carry(from, to, kind) {
  const file = from
    .saved()
    .filter((f) => f.endsWith(".baraka") && f.includes(kind))
    .sort()
    .pop();
  assert.ok(file, `${kind} fayli yo'q`);
  copyFileSync(join(from.files, file), join(to.files, file));
  return file;
}

describe("Musofir: ikki qirg'oq", () => {
  let mf;
  let home;
  after(async () => {
    await mf?.stop().catch(() => {});
    await home?.stop().catch(() => {});
  });
  afterEach(async (t) => {
    await mf?.shot(`tq-mf-${t.name.slice(0, 2)}`).catch(() => {});
    await home?.shot(`tq-home-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("T1. musofir: sozlash, shartlar 50/30/20 va uyga yuborish", async () => {
    mf = await startApp();
    await onboard(mf, { household: "Rustam akaning oilasi", name: "Rustam", members: [{ name: "Gulnora" }], spaces: ["Musofir"], rhythm: "Oylik maosh" });
    await mf.click("Musofir", await mf.region("Makonlar"));
    const setup = await mf.region("Musofir makonini sozlash", "form");
    await mf.selectText("Ish valyutasi", "Koreya voni (KRW)", setup);
    await mf.click("Saqlash", setup);
    await (await mf.testId("mf-fund")).waitForDisplayed();

    const card = await mf.region("Ikki qirgʻoq: oila bilan kelishuv", "section");
    await mf.click("Shartlarni belgilash", card);
    const form = await mf.region("Ikki qirgʻoq shartlari", "form");
    await mf.type("Uy xarajati, foiz", "50", form);
    await mf.type("Qarz toʻlovi, foiz", "30", form);
    await mf.type("Qurilish va taʼmir, foiz", "20", form);
    await mf.selectText("Uyda kim qabul qiladi", "Gulnora", form);
    await noAxe(mf, "mf-terms");
    await mf.shot("desktop-91-mf-terms");
    await mf.click("Saqlash", form);
    await waitIn(await mf.testId("mf-terms-shares"), "Uy xarajati 50 %", "shartlar");
    await waitIn(await mf.testId("mf-terms-agreement"), "hali tasdiqlamagan", "kelishuv");

    await mf.click("Uyga yuborish", await mf.region("Yozuv qoʻshish"));
    const dialog = await mf.x("//div[@role='dialog']");
    await mf.type("Summa (KRW)", "1 200 000", dialog);
    await mf.type("Komissiya (KRW)", "5 000", dialog);
    await mf.type("Uyda olingan summa (UZS)", "10 900 000", dialog);
    assert.equal(await (await mf.field("Uy xarajati, foiz", dialog)).getValue(), "50");
    await mf.click("Saqlash", dialog);
    await dialog.waitForExist({ reverse: true });

    await mf.nav("Sinxronlash");
    const pairing = await mf.region("Yangi qurilmani ulash");
    await mf.choose("Uydagi oila qurilmasi", pairing);
    await mf.click("Ulash faylini yaratish", pairing);
    await waitIn(await mf.testId("pairing-role"), "musofirning shaxsiy hisobi", "ulash");
  });

  it("T2. oila qurilmasi: Musofir ko'rinmaydi, pul qabul qilinadi va sarflanadi", async () => {
    const code = await mf.text("pairing-code");
    home = await startApp();
    carry(mf, home, "pairing");
    await home.choose("Mavjud xonadonga qoʻshilish");
    await home.click("Fayl tanlash");
    await home.type("Ulash kodi yoki zaxira nusxa paroli", code);
    await home.type("Bu qurilma nomi", "Uydagi kompyuter");
    await home.type("6 xonali PIN", HOME_PIN);
    await home.type("PINʼni takrorlang", HOME_PIN);
    await home.click("Qoʻshilish");
    await home.text("recovery-code");
    await home.click("Yozib oldim");
    await (await home.b.$("nav")).waitForDisplayed();

    await waitIn(await home.testId("role-badge"), "Uydagi oila qurilmasi", "rol");
    const spaces = await (await home.region("Makonlar")).getText();
    assert.doesNotMatch(spaces, /Musofir/);

    await home.nav("Ikki qirgʻoq");
    const r = await home.testId("mf-remittance");
    await waitIn(r, "1 200 000 KRW", "yuborish");
    assert.match(await r.getText(), /Yoʻlda/);
    const confirm = await home.region("Qabul qilish", "form");
    assert.equal(await (await home.field("Olingan summa (soʻmda)", confirm)).getValue(), "10900000");
    await home.selectText("Kim oldi", "Gulnora", confirm);
    await noAxe(home, "home-incoming");
    await top(home);
    await home.shot("desktop-92-home-incoming");
    await home.click("Qabul qildim", confirm);
    await waitIn(await home.testId("mf-purpose-HOUSEHOLD"), "5 450 000", "uy xarajati");

    const spend = await home.region("Maqsad boʻyicha xarajat", "form");
    await home.selectText("Maqsad", "Uy xarajati", spend);
    await home.type("Summa", "2 000 000", spend);
    await home.type("Izoh", "Bozor", spend);
    await home.click("Xarajatni yozish", spend);
    await waitIn(await home.testId("mf-purpose-HOUSEHOLD"), "3 450 000", "qoldiq");
    await waitIn(await home.testId("mf-shores-balance"), "8 900 000", "jami qoldiq");
    await noAxe(home, "home-shores");
    await top(home);
    await home.shot("desktop-93-home-two-shores");

    await home.nav("Kelishuvlar");
    await home.click("Oilaviy kelishuvlar");
    await (await home.testId("family-remittance-note")).waitForDisplayed();
    await home.click("Gulnora tasdiqlaydi");
    await home.type("Gulnora: PIN bilan tasdiqlang", HOME_PIN);
    await home.click("Tasdiqlash");
    await home.waitText("✓");

    await home.nav("Sinxronlash");
    const exp = await home.region("Eksport", "form");
    await home.choose("Qurilma uchun", exp);
    await home.type("Fayl paroli", PASSWORD, exp);
    await home.type("Parolni takrorlang", PASSWORD, exp);
    await home.click("Faylni saqlash", exp);
    await home.waitText("Fayl saqlandi");
  });

  it("T3. musofir: uydagi qabul va qoldiq, Gulnora tasdiqlagan", async () => {
    carry(home, mf, "incremental");
    const imp = await mf.region("Import");
    await mf.click("Fayl tanlash", imp);
    await mf.type("Fayl paroli", PASSWORD, imp);
    await mf.click("Koʻrib chiqish", imp);
    await mf.click("Qabul qilish", imp);
    await waitIn(imp, "yangi", "import");

    await mf.click("Musofir", await mf.region("Makonlar"));
    await mf.nav("Bosh sahifa");
    await waitIn(await mf.testId("mf-purpose-HOUSEHOLD"), "3 450 000", "musofirda qoldiq");
    const agreement = await mf.testId("mf-terms-agreement");
    await waitIn(agreement, "Gulnora: ✓", "Gulnora tasdig'i");
    await noAxe(mf, "mf-shores");
    await mf.b.execute(() => document.querySelector('[aria-label="Uyda: maqsadlar boʻyicha"]')?.scrollIntoView());
    await mf.shot("desktop-94-mf-shores-summary");
  });
});
