// Zaxira nusxa → yangi profil (boshqa kompyuter) → «Mavjud xonadonga qo'shilish» → 1:1.
import assert from "node:assert/strict";
import { copyFileSync } from "node:fs";
import { join } from "node:path";
import { after, describe, it } from "node:test";

import { startApp } from "../lib/app.mjs";
import { onboard } from "../lib/flows.mjs";

const PASSWORD = "Zaxira-2027!";

describe("Zaxira nusxadan tiklash", () => {
  const apps = [];
  after(async () => {
    for (const a of apps) await a.stop().catch(() => {});
  });

  it("eksport → yangi profil → qo'shilish: ma'lumotlar 1:1", async () => {
    const a = await startApp();
    apps.push(a);
    await onboard(a, { household: "Ravshan akaning oilasi", name: "Karim", members: [{ name: "Malika" }] });
    await a.b.keys(["Control", "n"]);
    await a.type("Summa", "1 250 000");
    await a.type("Manba", "Bozor");
    await a.click("Saqlash");
    await a.click("Ajratish");
    await a.waitText("1 250 000");
    const before = { paid: await a.text("kpi-paid-to-self") };

    await a.nav("Sinxronlash");
    await a.type("Fayl paroli", PASSWORD);
    await a.type("Parolni takrorlang", PASSWORD);
    await a.click("Faylni saqlash");
    await a.waitText("Fayl saqlandi");
    const file = a.saved().find((f) => f.endsWith(".baraka"));
    assert.ok(file, "zaxira fayli yozilmadi");
    assert.deepEqual(await a.axe(), []);
    await a.shot("restore-1-export");

    const b = await startApp();
    apps.push(b);
    copyFileSync(join(a.files, file), join(b.files, file));
    await b.choose("Mavjud xonadonga qoʻshilish");
    await b.click("Fayl tanlash");
    await b.waitText(file);
    await b.type("Ulash kodi yoki zaxira nusxa paroli", PASSWORD);
    await b.type("Bu qurilma nomi", "Yangi kompyuter");
    await b.type("6 xonali PIN", "112233");
    await b.type("PINʼni takrorlang", "112233");
    await b.click("Qoʻshilish");
    await b.text("recovery-code");
    await b.click("Yozib oldim");
    await (await b.b.$("nav")).waitForDisplayed();
    assert.equal(await b.text("kpi-paid-to-self"), before.paid);
    await b.nav("Sinxronlash");
    await b.waitText("Yangi kompyuter");
    await b.waitText("Desktop");
    await b.shot("restore-2-joined");
  });
});
