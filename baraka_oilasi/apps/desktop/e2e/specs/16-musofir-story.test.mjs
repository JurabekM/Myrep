// Qaytish xavfsizligi (M5, musofir/SPEC 6.8). Uyda oyiga 8 mln so'm
// xarajat → 35 kundan keyin Rustam Koreyadan qaytdi: 18 000 $ (1 $ = 12 650 so'm ≈ 227,7 mln) — qal'a devori
// 48 mln, erkin pul 179,7 mln → «Oltin foyda»ga 10 000 $ (126,5 mln): «oyiga 35 % kafolat», «joy kam», tekshirtirmaydi,
// pulni qaytarib olish qiyin, oila bilan maslahatlashmadi → qizil: besh belgidan to'rttasi, «5,2 barobar» → rad
// etdi. Uy makonida «Taklifni tekshirish» ham shu besh belgini so'raydi.
import assert from "node:assert/strict";
import { after, afterEach, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard, unlock } from "../lib/flows.mjs";

const SHIFT = 35;
const pad = (n) => String(n).padStart(2, "0");

/** Yadro soati bo'yicha (SHIFT kun keyin) `back` kun oldingi sana, ISO. */
function coreDaysAgo(back) {
  const d = new Date();
  d.setDate(d.getDate() + SHIFT - back);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

async function waitValue(app, id, fragment) {
  await app.b.waitUntil(async () => (await app.text(id)).includes(fragment), { timeout: 15000, timeoutMsg: `${id}: ${fragment} yo'q` });
}

async function answer(app, dialog, question, reply) {
  const group = await dialog.$(`.//div[@role='radiogroup'][.//p[contains(., "${question}")]]`);
  await group.waitForDisplayed();
  await app.choose(reply, group);
}

describe("Musofir: qaytish xavfsizligi", () => {
  let app;
  let profile;
  after(async () => app?.stop());
  afterEach(async (t) => {
    await app?.shot(`mfs-last-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("S1. uyda oyiga 8 mln so'm xarajat", async () => {
    app = await startApp();
    profile = app.dir;
    await onboard(app, { household: "Rustamning oilasi", name: "Rustam", spaces: ["Musofir"], rhythm: "Oylik maosh" });
    await app.nav("Xarajatlar");
    await app.type("Summa", "8 000 000");
    await app.selectText("Kategoriya", "Oziq-ovqat");
    await app.click("Saqlash");
    await app.waitText("8 000 000");
  });

  it("S2. 35 kundan keyin: 18 000 $ bilan qaytdi — qal'a devori va erkin pul", async () => {
    await app.stop();
    app = await startApp({ profile, shiftDays: SHIFT });
    await unlock(app);
    await app.click("Musofir", await app.region("Makonlar"));
    const setup = await app.region("Musofir makonini sozlash", "form");
    await app.selectText("Ish valyutasi", "Koreya voni (KRW)", setup);
    await app.click("Saqlash", setup);
    await (await app.testId("mf-fund")).waitForDisplayed();

    const card = await app.region("Qaytish va sovutish davri", "section");
    await app.click("Qaytdim", card);
    const form = await app.region("Qaytish", "form");
    await app.setDate("Qaytgan sana", coreDaysAgo(3), form);
    await app.selectText("Valyuta", "USD", form);
    await app.type("Olib kelingan summa (USD)", "18 000", form);
    await app.type("1 USD necha UZS", "12 650", form);
    await app.click("Saqlash", form);
    await waitValue(app, "mf-cooling", "yana 87 kun");
    await waitValue(app, "mf-wall", "48 000 000 soʻm");
    assert.match(await app.text("mf-wall"), /Erkin pul.*179 700 000 soʻm/s);
    assert.match(await card.getText(), /227 700 000 soʻm/);
    await noAxe(app, "mf-wall");
    await app.b.execute(() => document.querySelector('[aria-label="Qaytish va sovutish davri"]')?.scrollIntoView());
    await app.shot("desktop-102-mf-fortress-wall");
  });

  it("S3. «Oltin foyda»: oyiga 35 % kafolat — besh belgidan to'rttasi, qizil", async () => {
    await app.click("Katta qarorni tekshirish", await app.region("Qaytish va sovutish davri", "section"));
    const dialog = await app.x("//div[@role='dialog']");
    await app.selectText("Qaror turi", "Sarmoya", dialog);
    await app.type("Summa (UZS)", "126 500 000", dialog);
    await app.type("Oyiga vaʼda qilingan foyda, % (boʻlsa)", "35", dialog);
    await app.type("Nima haqida", "«Oltin foyda» — sinfdoshning taklifi", dialog);
    for (const [q, r] of [
      ["kafolatlanyaptimi", "Ha"],
      ["Zarar boʻlsa", "Bilmayman"],
      ["real mol", "Bilmayman"],
      ["yangi odam", "Bilmayman"],
      ["Shoshiltirishyaptimi", "Ha"],
      ["Yozma shartnoma", "Ha"],
      ["davlat ruxsati", "Bilmayman"],
      ["oʻz koʻzingiz bilan", "Yoʻq"],
      ["qaytarib olish", "Yoʻq"],
      ["qaytganingizdan keyin", "Ha"],
      ["Avval pul", "Yoʻq"],
      ["Chet elga", "Yoʻq"],
      ["Oila bilan", "Yoʻq"],
    ]) {
      await answer(app, dialog, q, r);
    }
    await app.click("Tekshirish", dialog);
    const result = await app.testId("mf-decision-result");
    await result.waitForDisplayed();
    const text = await result.getText();
    assert.match(text, /Qizil: katta xavf/);
    assert.match(text, /Besh xavf belgisidan topildi: 4/);
    assert.match(text, /ikkitasi — bu taklifdan voz kechishga yetarli sabab/);
    assert.match(text, /55,56 %i/);
    assert.match(await app.text("mf-decision-promise"), /420 %, pulingiz 5,2 barobar/);
    await noAxe(app, "mf-scam-offer");
    await app.b.execute(() => document.querySelector('[data-testid="mf-decision-result"]')?.scrollIntoView({ block: "end" }));
    await app.shot("desktop-103-mf-scam-offer-red");
    await app.click("Rad etaman", result);
    await dialog.waitForExist({ reverse: true });
    await waitValue(app, "mf-decision", "Rad etaman");
  });

  it("S4. Uy: «Taklifni tekshirish» — besh belgi", async () => {
    await app.click("Uy", await app.region("Makonlar"));
    await app.click("Taklifni tekshirish");
    const dialog = await app.x("//div[@role='dialog']");
    for (const [q, r] of [
      ["kafolatlanyaptimi", "Yoʻq"],
      ["Zarar boʻlsa", "Ha"],
      ["real mol", "Ha"],
      ["yangi odam", "Yoʻq"],
      ["Shoshiltirishyaptimi", "Ha"],
      ["Yozma shartnoma", "Ha"],
      ["davlat ruxsati", "Ha"],
      ["oʻz koʻzingiz bilan", "Ha"],
      ["qaytarib olish", "Yoʻq"],
    ]) {
      await answer(app, dialog, q, r);
    }
    await app.click("Tekshirish", dialog);
    await app.waitText("Besh xavf belgisidan topildi: 2");
    assert.match(await dialog.getText(), /Qizil: pul bermang/);
    await noAxe(app, "uy-offer-signs");
  });
});
