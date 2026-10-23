// Bir nechta spec'da takrorlanadigan oqimlar.
export const PIN = "246810";

/** 5 qadamli onboarding. `spaces` — Uy'dan tashqari daftarlar (masalan, «Kasb-kor»). Tiklash kodini qaytaradi. */
export async function onboard(app, { household = "Bekzodlar oilasi", name = "Bekzod", members = [], spaces = [], rhythm = "Har kuni naqd", debts = false, pin = PIN } = {}) {
  await app.click("Davom etish");
  await app.type("Oila nomi", household);
  await app.type("Ismingiz", name);
  for (const s of spaces) await app.choose(s);
  for (const [i, m] of members.entries()) {
    await app.click("+ Aʼzo qoʻshish");
    await app.type(`${i + 2}-aʼzo ismi`, m.name);
    if (m.child) await app.select(`${i + 2}-aʼzo: katta yoki bola`, "CHILD");
  }
  await app.click("Davom etish");
  await app.choose(rhythm);
  await app.click("Davom etish");
  await app.choose(debts ? "Ha, bor" : "Yoʻq");
  await app.click("Davom etish");
  await app.type("6 xonali PIN", pin);
  await app.type("PINʼni takrorlang", pin);
  await app.click("Boshlash");
  const code = await app.text("recovery-code");
  await app.click("Yozib oldim");
  await (await app.b.$("nav")).waitForDisplayed();
  return code;
}

export async function unlock(app, pin = PIN) {
  const el = await app.b.$('input[type="password"]');
  await el.waitForDisplayed();
  await el.setValue(pin);
  await app.b.keys("Enter");
  await (await app.b.$("nav")).waitForDisplayed();
}
