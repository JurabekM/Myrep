// Onboarding (≤ 5 qadam), tiklash kodi, qulf va til/shrift sozlamalarining saqlanishi.
import assert from "node:assert/strict";
import { after, before, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";

describe("Onboarding va sozlamalar", () => {
  let app;
  let profile;
  before(async () => {
    app = await startApp();
    profile = app.dir;
  });
  after(async () => app?.stop());

  it("5 qadam: til → oila → daromad → qarz → PIN; har qadam axe'dan o'tadi", async () => {
    assert.equal(await app.text("setup-progress"), "Qadam 1 / 5");
    assert.deepEqual(await app.axe(), []);
    await app.shot("onboarding-1-language");
    await app.click("Davom etish");

    await app.type("Oila nomi", "Anvarlar oilasi");
    await app.type("Ismingiz", "Anvar");
    await app.click("+ Aʼzo qoʻshish");
    await app.type("2-aʼzo ismi", "Gulnora");
    await app.click("+ Aʼzo qoʻshish");
    await app.type("3-aʼzo ismi", "Jasur");
    await app.select("3-aʼzo: katta yoki bola", "CHILD");
    assert.deepEqual(await app.axe(), []);
    await app.shot("onboarding-2-family");
    await app.click("Davom etish");

    await app.choose("Har kuni naqd");
    assert.deepEqual(await app.axe(), []);
    await app.shot("onboarding-3-income");
    await app.click("Davom etish");

    await app.choose("Ha, bor");
    await app.shot("onboarding-4-debts");
    await app.click("Davom etish");

    assert.equal(await app.text("setup-progress"), "Qadam 5 / 5");
    await app.type("6 xonali PIN", "246810");
    await app.type("PINʼni takrorlang", "246810");
    await app.click("Boshlash");
    const code = await app.text("recovery-code");
    assert.match(code, /^[A-Z2-7]{4}(-[A-Z2-7]{4}){5}$/);
    assert.deepEqual(await app.axe(), []);
    await app.shot("onboarding-5-recovery");
    await app.click("Yozib oldim");

    // «Qarzim bor» → birinchi ekran — qarzlar inventari.
    await app.waitText("Qarzlar");
    assert.equal(await (await app.b.$('nav button[aria-current="page"]')).getText(), "Qarzlar");
  });

  it("bosh sahifa eslatmalari: bugungi tushum va qarzlarni yozish", async () => {
    await app.nav("Bosh sahifa");
    await (await app.testId("nudge-INCOME_TODAY")).waitForDisplayed();
    await (await app.testId("nudge-DEBT_INVENTORY")).waitForDisplayed();
    assert.deepEqual(await app.axe(), []);
    await app.shot("home-nudges");
  });

  it("sozlamalar: rus tili va 130% shrift qayta ochilganda saqlanadi", async () => {
    await app.nav("Sozlamalar");
    await app.choose("Русский");
    await app.waitText("Настройки");
    await app.choose("130%");
    assert.deepEqual(await app.axe(), []);
    await app.shot("settings-ru-130");
    await app.stop();

    app = await startApp({ profile });
    // Qulf ekrani ham rus tilida (baza hali ochilmagan) va shrift 130%.
    await app.waitText("PIN");
    assert.match(await app.bodyText(), /Тетрадь|PIN/);
    assert.equal(await app.b.execute(() => document.documentElement.style.fontSize), "130%");
    assert.equal(await app.b.execute(() => document.documentElement.lang), "ru");
    const pin = await app.b.$('input[type="password"]');
    await pin.setValue("246810");
    await app.b.keys("Enter");
    await app.waitText("Главная");
    assert.deepEqual(await app.axe(), []);
    await app.shot("home-ru-after-restart");
  });
});
