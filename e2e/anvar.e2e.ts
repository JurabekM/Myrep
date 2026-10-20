// Yakuniy E2E — Anvar ssenariysi (DESKTOP_PROMPT D15). WebdriverIO + tauri-driver (Windows, WebView2).
// Ishga tushirish tartibi: e2e/README.md. Bu fayl loyiha lint/typecheck doirasiga kirmaydi (alohida papka).
// Selektorlar — faqat ko'rinadigan matn va rollar (accessible name): data-testid yo'q, UI testlari bilan bir xil.

/* eslint-disable */
// @ts-nocheck

const PIN = "246813"; // faqat toza test profili uchun (haqiqiy PIN emas)

async function click(name: string) {
  const button = await $(`aria/${name}`);
  await button.waitForClickable({ timeout: 10_000 });
  await button.click();
}

async function type(label: string, value: string) {
  const field = await $(`aria/${label}`);
  await field.waitForDisplayed({ timeout: 10_000 });
  await field.setValue(value);
}

async function see(text: string) {
  const element = await $(`*=${text}`);
  await element.waitForDisplayed({ timeout: 10_000 });
}

describe("Anvar ssenariysi", () => {
  it("1. PIN o'rnatish va onboarding", async () => {
    await type("PIN (6 ta raqam)", PIN);
    await type("PIN ni qayta kiriting", PIN);
    await click("Saqlash va boshlash");
    await see("Xush kelibsiz");
    await click("O'tkazib yuborish");
  });

  it("2. Daromad va Kelajagim ulushi", async () => {
    await click("Daromad");
    await click("Yangi daromad");
    await type("Summa", "3 000 000");
    await click("Saqlash");
    // Daromaddan keyin «Kelajagim»ga ulush taklifi chiqadi (2026-10-20 qo'lda o'tilgan ssenariy bo'yicha).
    await click("Ajratish");
    await see("3 000 000 soʻm");
    await click("Kelajagim");
    await see("Kelajagim");
  });

  it("3. Xarajatlar, audit, havas chegarasi", async () => {
    await click("Xarajatlar");
    await see("Oy xulosasi");
    await click("Byudjet");
    await see("Obuna");
  });

  it("4. Qarz: to'xta va o'yla, 70/20/10, payoff", async () => {
    await click("Qarzlar");
    await type("Qoldiq summa", "3 900 000");
    await click("Hisoblash");
    await see("Qarzsiz kun");
    await click("Saqlash");
  });

  it("5. Sheriklik: musharaka 9/9, imzolar, hodisa, ko'rik, taqsimot", async () => {
    await click("Sheriklik");
    await type("Sheriklik nomi", "Non sexi");
    await click("Sheriklik yaratish");
    await see("Kim bilan kim?");
    // 9 savol va imzolar — AgreementWizard; canvas imzo WebDriver `actions` bilan chiziladi.
    // Davr yopilgach: Dilshod 40 % → 1 400 000 soʻm.
  });

  it("6. .baraka eksport", async () => {
    await click("Sozlamalar");
    await type("Eksport paroli (kamida 8 belgi)", "juda-sirli-parol");
    await click("Eksport qilish");
    await see(".baraka");
  });
});
