/* OmborAI eskizlari uchun: til (uz-lat / ru) va tema (yorug' / tungi) almashtirish. */
(function () {
  const dict = {
    "uz": {
      "brand.nav.pos": "Kassa",
      "brand.nav.inventory": "Tovarlar",
      "brand.nav.dashboard": "Bosh sahifa",
      "shift.open": "Smena ochiq",
      "theme.label": "Mavzu",
      "theme.light": "Yorug'",
      "theme.dark": "Tungi",
      "lang.label": "Til",

      "pos.search": "Shtrix-kod yoki nom bo'yicha qidirish",
      "pos.cart": "Savat",
      "pos.empty": "Savat bo'sh. Tovarni skanerlang yoki tanlang.",
      "pos.subtotal": "Jami",
      "pos.discount": "Chegirma",
      "pos.total": "To'lov summasi",
      "pos.pay": "To'lash",
      "pos.pay.cash": "Naqd",
      "pos.pay.card": "Karta",
      "pos.pay.click": "Click",
      "pos.pay.payme": "Payme",
      "pos.customer": "Mijoz (qarzga sotuv uchun)",
      "pos.clear": "Tozalash",
      "pos.stock": "qoldiq",
      "pos.unit.pcs": "dona",

      "inv.title": "Tovarlar va qoldiq",
      "inv.search": "Tovar nomi yoki shtrix-kod",
      "inv.filter.low": "Faqat kam qolganlar",
      "inv.col.name": "Tovar",
      "inv.col.barcode": "Shtrix-kod",
      "inv.col.stock": "Qoldiq",
      "inv.col.min": "Minimal",
      "inv.col.price": "Sotuv narxi",
      "inv.col.status": "Holat",
      "inv.col.actions": "Amallar",
      "inv.status.ok": "Yetarli",
      "inv.status.low": "Kam qoldi",
      "inv.status.out": "Tugagan",
      "inv.btn.in": "Kirim",
      "inv.btn.adjust": "Tuzatish",
      "inv.btn.new": "Yangi tovar",

      "dash.title": "Bugungi holat",
      "dash.sales": "Bugungi savdo",
      "dash.profit": "Taxminiy foyda",
      "dash.debts": "Mijozlar qarzi",
      "dash.low": "Kam qolgan tovarlar",
      "dash.chart": "So'nggi 7 kun savdosi",
      "dash.recent": "So'nggi cheklar",
      "dash.vs": "kechagiga nisbatan",
      "dash.days": ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"],
      "unit.sum": "so'm",
      "unit.pcs": "dona"
    },
    "ru": {
      "brand.nav.pos": "Касса",
      "brand.nav.inventory": "Товары",
      "brand.nav.dashboard": "Главная",
      "shift.open": "Смена открыта",
      "theme.label": "Тема",
      "theme.light": "Светлая",
      "theme.dark": "Тёмная",
      "lang.label": "Язык",

      "pos.search": "Поиск по штрих-коду или названию",
      "pos.cart": "Корзина",
      "pos.empty": "Корзина пуста. Отсканируйте или выберите товар.",
      "pos.subtotal": "Итого",
      "pos.discount": "Скидка",
      "pos.total": "К оплате",
      "pos.pay": "Оплатить",
      "pos.pay.cash": "Наличные",
      "pos.pay.card": "Карта",
      "pos.pay.click": "Click",
      "pos.pay.payme": "Payme",
      "pos.customer": "Клиент (для продажи в долг)",
      "pos.clear": "Очистить",
      "pos.stock": "остаток",
      "pos.unit.pcs": "шт.",

      "inv.title": "Товары и остатки",
      "inv.search": "Название товара или штрих-код",
      "inv.filter.low": "Только заканчивающиеся",
      "inv.col.name": "Товар",
      "inv.col.barcode": "Штрих-код",
      "inv.col.stock": "Остаток",
      "inv.col.min": "Минимум",
      "inv.col.price": "Цена продажи",
      "inv.col.status": "Статус",
      "inv.col.actions": "Действия",
      "inv.status.ok": "В норме",
      "inv.status.low": "Мало",
      "inv.status.out": "Закончился",
      "inv.btn.in": "Приход",
      "inv.btn.adjust": "Корректировка",
      "inv.btn.new": "Новый товар",

      "dash.title": "Сегодня",
      "dash.sales": "Продажи сегодня",
      "dash.profit": "Примерная прибыль",
      "dash.debts": "Долги клиентов",
      "dash.low": "Заканчивающиеся товары",
      "dash.chart": "Продажи за 7 дней",
      "dash.recent": "Последние чеки",
      "dash.vs": "по сравнению со вчера",
      "dash.days": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
      "unit.sum": "сум",
      "unit.pcs": "шт."
    }
  };

  const LANG_KEY = "omborai.lang";
  const THEME_KEY = "omborai.theme";

  function safeGet(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function safeSet(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* saqlash mumkin bo'lmasa, e'tiborsiz */ }
  }

  let lang = safeGet(LANG_KEY) || "uz";
  let theme = safeGet(THEME_KEY) || "system";

  function t(key) {
    const table = dict[lang] || dict.uz;
    return table[key] !== undefined ? table[key] : key;
  }

  function applyLang() {
    document.documentElement.lang = lang === "uz" ? "uz-Latn" : "ru";
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.placeholder = t(el.dataset.i18nPlaceholder);
    });
    document.querySelectorAll("[data-lang-btn]").forEach((b) => {
      b.setAttribute("aria-pressed", String(b.dataset.langBtn === lang));
    });
    document.querySelectorAll("[data-theme-btn]").forEach((b) => {
      b.setAttribute("aria-pressed", String(b.dataset.themeBtn === theme));
    });
    document.dispatchEvent(new CustomEvent("omborai:lang", { detail: { lang } }));
  }

  function applyTheme() {
    if (theme === "system") {
      document.documentElement.removeAttribute("data-theme");
    } else {
      document.documentElement.setAttribute("data-theme", theme);
    }
    document.querySelectorAll("[data-theme-btn]").forEach((b) => {
      b.setAttribute("aria-pressed", String(b.dataset.themeBtn === theme));
    });
  }

  document.addEventListener("click", (e) => {
    const langBtn = e.target.closest("[data-lang-btn]");
    if (langBtn) {
      lang = langBtn.dataset.langBtn;
      safeSet(LANG_KEY, lang);
      applyLang();
      return;
    }
    const themeBtn = e.target.closest("[data-theme-btn]");
    if (themeBtn) {
      theme = themeBtn.dataset.themeBtn;
      safeSet(THEME_KEY, theme);
      applyTheme();
    }
  });

  window.OmborI18n = { t: t, get lang() { return lang; } };

  document.addEventListener("DOMContentLoaded", () => {
    applyTheme();
    applyLang();
  });
})();
