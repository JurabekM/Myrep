// Kasb-kor: sotuvchi qurilmasi (K8, ADR-0003, kasbkor/SPEC 12), ikki haqiqiy ilova bilan.
// Egasi: Shakar (10 kg, sotuv narxi 15 000) → «Sotuvchi» rolida ulash fayli.
// Sotuvchi: qo'shiladi — menyuda faqat sotuv, nasiya to'lovi, smena; foyda va chiqim yo'q. 2 kg shakar
// (30 000, naqd) va 50 000 karta; smena: 100 000 + 30 000 = 130 000, egasiga 100 000. Fayl → egasi:
// shakar 8 kg, «Sotuvchi smenalari»da qator, qurilma «Sotuvchi».
import assert from "node:assert/strict";
import { copyFileSync } from "node:fs";
import { join } from "node:path";
import { after, afterEach, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard } from "../lib/flows.mjs";

const PASSWORD = "Dokon-2026!";

async function noAxe(app, screen) {
  const v = await app.axe();
  assert.deepEqual(v, [], `${screen}: axe`);
}

async function waitIn(el, fragment, what) {
  await el.waitUntil(async () => (await el.getText()).includes(fragment), { timeout: 15000, timeoutMsg: `${what}: ${fragment} yo'q` });
}

/** Eng yangi `.baraka` faylni bir ilovadan ikkinchisiga «olib o'tish». */
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

describe("Kasb-kor: sotuvchi qurilmasi", () => {
  let owner;
  let seller;
  after(async () => {
    await owner?.stop().catch(() => {});
    await seller?.stop().catch(() => {});
  });
  afterEach(async (t) => {
    await owner?.shot(`kkr-owner-${t.name.slice(0, 2)}`).catch(() => {});
    await seller?.shot(`kkr-seller-${t.name.slice(0, 2)}`).catch(() => {});
  });

  it("R1. egasi: tovar, chiqim va sotuvchi uchun ulash fayli", async () => {
    owner = await startApp();
    await onboard(owner, { household: "Bahodirlar oilasi", name: "Bahodir", spaces: ["Kasb-kor"], rhythm: "Har kuni naqd" });
    await owner.click("Kasb-kor", await owner.region("Makonlar"));
    await owner.waitText("Haqiqiy foyda (shu oy)");
    await owner.nav("Tovarlar");
    await owner.click("Yangi tovar");
    const item = await owner.region("Yangi tovar", "form");
    await owner.type("Nomi", "Shakar", item);
    await owner.type("Sotuv narxi (1 kg)", "15 000", item);
    await owner.click("Tovarni qoʻshish", item);
    const card = await owner.testId("kk-item-Shakar");
    await card.waitForDisplayed();
    await owner.click("Xarid", card);
    const buy = await owner.region("Shakar: Xarid", "form");
    await owner.type("Miqdor (kg)", "10", buy);
    await owner.type("Jami narx", "120 000", buy);
    await owner.click("Ilovagacha bor edi", buy);
    await owner.click("Saqlash", buy);
    await buy.waitForExist({ reverse: true });

    await owner.nav("Sinxronlash");
    const pairing = await owner.region("Yangi qurilmani ulash");
    await owner.choose("Sotuvchi", pairing);
    await owner.click("Ulash faylini yaratish", pairing);
    await (await owner.testId("pairing-code")).waitForDisplayed();
    assert.match(await owner.text("pairing-role"), /foyda, chiqim, maosh/);
    await noAxe(owner, "pairing-seller");
    await owner.shot("desktop-84-kk-pairing-seller");
  });

  it("R2. sotuvchi: qo'shiladi — foyda yo'q, sotuv yoziladi", async () => {
    const code = await owner.text("pairing-code");
    seller = await startApp();
    carry(owner, seller, "pairing");
    await seller.choose("Mavjud xonadonga qoʻshilish");
    await seller.click("Fayl tanlash");
    await seller.type("Ulash kodi yoki zaxira nusxa paroli", code);
    await seller.type("Bu qurilma nomi", "Do'kon telefoni");
    await seller.type("6 xonali PIN", "445566");
    await seller.type("PINʼni takrorlang", "445566");
    await seller.click("Qoʻshilish");
    await seller.text("recovery-code");
    await seller.click("Yozib oldim");
    await (await seller.b.$("nav")).waitForDisplayed();

    await waitIn(await seller.testId("role-badge"), "Sotuvchi qurilmasi · Kasb-kor", "rol");
    const nav = await (await seller.b.$("nav")).getText();
    assert.match(nav, /Sotuv/);
    assert.doesNotMatch(nav, /Hisob kuni|Tovarlar|Xodimlar/);
    assert.ok(!(await (await seller.b.$("main")).getText()).includes("Haqiqiy foyda"));

    const form = await seller.region("Yangi sotuv", "form");
    // Yagona katalog bandi (0 — «Katalogsiz»).
    await (await seller.field("Tovar", form)).selectByIndex(1);
    await seller.type("Miqdor (kg)", "2", form);
    await seller.click("Sotuvni yozish", form);
    await waitIn(await seller.testId("kk-seller-totals"), "30 000", "naqd");
    await (await seller.field("Tovar", form)).selectByIndex(0);
    await seller.type("Summa", "50 000", form);
    await seller.choose("Karta", form);
    await seller.click("Sotuvni yozish", form);
    await waitIn(await seller.testId("kk-seller-totals"), "Karta: 50 000", "karta");
    await noAxe(seller, "seller-sale");
    await seller.shot("desktop-85-kk-seller-sale");
  });

  it("R3. sotuvchi: smena yopiladi, fayl egasiga", async () => {
    await seller.nav("Smena");
    const form = await seller.region("Smenani yopish", "form");
    await seller.type("Kassadagi boshlangʻich naqd", "100 000", form);
    await waitIn(await seller.testId("kk-shift-expected"), "130 000", "kutilgan");
    await seller.type("Sanalgan summa", "130 000", form);
    await seller.type("Egasiga topshirildi", "100 000", form);
    await waitIn(await seller.testId("kk-shift-difference"), "Farq yoʻq", "farq");
    await noAxe(seller, "seller-shift");
    await seller.shot("desktop-86-kk-seller-shift");
    await seller.click("Smenani yopish", form);
    await seller.waitText("Bugungi smena yopilgan");
    await (await seller.testId("kk-shift-row")).waitForDisplayed();

    await seller.nav("Sinxronlash");
    const exp = await seller.region("Eksport", "form");
    await seller.choose("Qurilma uchun", exp);
    await seller.type("Fayl paroli", PASSWORD, exp);
    await seller.type("Parolni takrorlang", PASSWORD, exp);
    await seller.click("Faylni saqlash", exp);
    await seller.waitText("Fayl saqlandi");
  });

  it("R4. egasi: sotuvchi fayli — sotuv, smena va qoldiq", async () => {
    carry(seller, owner, "incremental");
    const imp = await owner.region("Import");
    await owner.click("Fayl tanlash", imp);
    await owner.type("Fayl paroli", PASSWORD, imp);
    await owner.click("Koʻrib chiqish", imp);
    await owner.click("Qabul qilish", imp);
    await waitIn(imp, "yangi", "import");
    await waitIn(await owner.testId("device-role-Do'kon telefoni"), "Sotuvchi", "rol");

    await owner.nav("Kassa");
    await waitIn(await owner.testId("kk-shift-row"), "Do'kon telefoni", "smena");
    await noAxe(owner, "owner-shifts");
    await owner.shot("desktop-87-kk-owner-seller-shifts");
    await owner.nav("Tovarlar");
    await waitIn(await owner.testId("kk-item-Shakar"), "8 kg", "qoldiq");
  });
});
