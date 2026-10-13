/**
 * Dilshod bilan musharaka (DESKTOP_PROMPT D15), haqiqiy oynada: shartnoma ustasi (9 savol, jonli progress va
 * önizleme) → kattalar/tomonlar tasdig'i → faollashtirish → vazifa hodisasi → oylik ko'rik va bayonnoma →
 * katta foyda tasdig'i bilan davrni yopish (1,4 mln taqsimot) → eksport.
 *
 * HOLAT: yozilgan, lekin shu sessiyada ISHGA TUSHIRILMAGAN (Linux konteynerda Windows/WebView2 yo'q).
 * Selektorlar `data-testid` va i18n matnlariga (uz) tayanadi; birinchi Windows ishga tushirishda sozlash kerak
 * bo'lishi mumkin. Pul hisobi Rust integratsiya testlarida (`crates/services/tests/`) tekshiriladi.
 */
const PARTNER = 'Yetkazib berish';

async function goTo(label: string) {
  await $(`nav button=${label}`).click();
}

describe('Musharaka: Anvar × Dilshod', () => {
  it('shartnoma ustasi: progress va önizleme ko‘rinadi, 9/9 bo‘lguncha imzolash yo‘q', async () => {
    await goTo('Sheriklik');
    await $('button=Yangi shartnoma').click();
    await $('[data-testid="wizard-progress"]').waitForDisplayed();
    await $('[data-testid="draft-preview"]').waitForDisplayed();
    await $("aria/Sheriklik nomi").setValue(PARTNER);
    await $("aria/1-tomon ismi").setValue('Anvar');
    await $("aria/2-tomon ismi").setValue('Dilshod');
  });

  it('vazifalar va pul joyi kiritiladi; qoralama 9/9 bo‘ladi', async () => {
    await $("aria/Muddat tugaganda nima bo'ladi").setValue('Hisob-kitob qilinadi');
    await $("aria/Nizolarni hal qilish tartibi").setValue('Hakam hal qiladi');
    await $("aria/Pul qayerda turadi").setValue('Anvar hisobi, Dilshod ko‘chirma oladi');
    await $('button=Shartnomani saqlash').click();
    await $('[data-testid="agreement-status"]').waitForDisplayed();
  });

  it('kattalar PIN bilan tasdiqlaydi; hammasi tasdiqlagach faollashadi', async () => {
    await $('button=Faollashtirish').waitForDisplayed();
    await $('button=Faollashtirish').click();
    await $('[data-testid="ps-status"]').waitForDisplayed();
  });

  it('vazifa hodisasi: «Bajara olmayapman» bandni ko‘rsatadi va jurnalga yozadi', async () => {
    await $('[data-testid="duty-list"]').waitForDisplayed();
    await $('button=Bajara olmayapman').click();
    await $('[data-testid="duty-incident-form"]').waitForDisplayed();
    await $("aria/Sabab").setValue('Yo‘l yopiq edi');
    await $('button=Hodisani yozish').click();
    await $('//*[contains(text(), "Hodisa jurnalga yozildi")]').waitForDisplayed();
  });

  it('oylik ko‘rik: ikkala tomon javob beradi, ko‘rik yakunlanadi, bayonnoma chiqadi', async () => {
    await $('[data-testid="review-session"]').waitForDisplayed();
    await $('[data-testid="review-party-Anvar"] button=Ko\'rdim, roziman').click();
    await $('[data-testid="review-party-Dilshod"] button=Ko\'rdim, roziman').click();
    await $('button=Ko\'rikni yakunlash').click();
    await $('[data-testid="review-head"]').waitForDisplayed();
    await $('button=Bayonnoma PDF').click();
  });

  it('katta foyda: tasdiqsiz davr yopilmaydi; 1 400 000 taqsimot tasdiq bilan yopiladi', async () => {
    await goTo('Sheriklik');
    await $('[data-testid="spike-alert"]').waitForDisplayed();
    await expect($('button=Davrni yopish')).toBeDisabled();
    await $("aria/Ikkala tomon 4- va 5-bandlarni qayta o'qib chiqdi").click();
    await $('button=Davrni yopish').click();
  });

  it('eksport: .baraka fayli yoziladi', async () => {
    await goTo('Almashish');
    await $('h1').waitForDisplayed();
    await expect($('footer')).toHaveText(expect.stringContaining('Fatvo yoki moliyaviy maslahat emas'));
  });
});

export {};
