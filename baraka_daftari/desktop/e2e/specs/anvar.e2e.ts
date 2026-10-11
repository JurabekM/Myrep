/**
 * «Anvar» ssenariysi (DESKTOP_PROMPT D15), haqiqiy oynada: PIN → daromad (Ctrl+N) → asosiy sahifalar →
 * sheriklik → eksport sahifasi. Pul hisobi bu yerda tekshirilmaydi (Rust integratsiya testi
 * `crates/services/tests/anvar.rs` va golden vektorlar tekshiradi); bu spetsifikatsiya UI ulanishini,
 * klaviatura yo'lini va OS dialoglarisiz oqimni sinaydi.
 *
 * HOLAT: yozilgan, lekin shu sessiyada ISHGA TUSHIRILMAGAN (Linux konteynerda Windows/WebView2 yo'q).
 * Selektorlar i18n matnlariga (uz) tayanadi; birinchi Windows ishga tushirishda sozlash kerak bo'lishi mumkin.
 */
const PIN = '123456';

async function nav(label: string) {
  await $(`nav button=${label}`).click();
}

describe('Anvar: boshidan oxirigacha', () => {
  it('PIN o‘rnatadi va daftar ochiladi', async () => {
    await $('aria/Yangi PIN (6 raqam)').setValue(PIN);
    await $("aria/PIN'ni takrorlang").setValue(PIN);
    await $("button=PIN o'rnatish").click();
    await $('nav').waitForDisplayed();
  });

  it('onboarding 5 qadam va yakunlanadi', async () => {
    await $('[data-testid="onb-progress"]').waitForDisplayed();
    for (let i = 0; i < 4; i++) await $('button=Keyingi').click();
    await $('button=Boshlash').click();
    await $('[data-testid="onb-progress"]').waitForDisplayed({ reverse: true });
  });

  it('Ctrl+N bilan daromad yozadi: ilova ulush taklif qiladi', async () => {
    await browser.keys(['Control', 'n']);
    await $("aria/Summa (so'm)").setValue('200000');
    await $('[role="dialog"]').waitForDisplayed();
    await $('button=Saqlash').click();
  });

  it('asosiy bo‘limlar ochiladi (daromad → qarzlar → sheriklik → almashish)', async () => {
    for (const label of ['Daromad', 'Qarzlar', 'Sheriklik', 'Hunardan ishga', 'Almashish']) {
      await nav(label);
      await $('h1').waitForDisplayed();
      await expect($('h1')).toHaveText(expect.stringContaining(label.split(' ')[0] ?? label));
    }
  });

  it('har bir ta’limiy sahifada disklеymer bor', async () => {
    await expect($('footer')).toHaveText(expect.stringContaining('Fatvo yoki moliyaviy maslahat emas'));
  });

  it('Ctrl+L daftarni qulflaydi, PIN bilan ochiladi', async () => {
    await browser.keys(['Control', 'l']);
    await $('aria/PIN (6 raqam)').setValue(PIN);
    await $('button=Ochish').click();
    await $('nav').waitForDisplayed();
  });
});
