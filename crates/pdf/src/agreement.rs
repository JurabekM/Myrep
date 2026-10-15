//! Kelishuv hujjati (SPEC 2F): 9 savol bo'limlari, tomonlar, imzolar. Matnlar — satr literallari,
//! typst markup'i foydalanuvchi matnidan kirmaydi.

use crate::{FONT_FAMILY, lit, pairs_table, section};

/// Kelishuv hujjati — PDF uchun tayyor matnlar (hisob yo'q, faqat ko'rsatish).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgreementDocument {
    /// Sarlavha.
    pub title: String,
    /// Turi (ko'rsatish nomi) va versiya satri, masalan «Sheriklik · 2-versiya».
    pub subtitle: String,
    /// Holat va sanalar satri.
    pub status_line: String,
    /// 1. Tomonlar: (ism, rol).
    pub parties: Vec<(String, String)>,
    /// 2. Hissalar: (tomon, tavsif).
    pub contributions: Vec<(String, String)>,
    /// 3. Vazifalar: (vazifa — mas'ul, «bajarilmasa» bandi).
    pub duties: Vec<(String, String)>,
    /// 4. Foyda qoidasi.
    pub profit: String,
    /// 5. Zarar qoidasi.
    pub loss: String,
    /// 6. Hisob yuritish.
    pub custody: String,
    /// 7. Ajralib chiqish.
    pub exit: String,
    /// 8. Hakam.
    pub arbiter: String,
    /// 9. Muddat va yangilash.
    pub term: String,
    /// Imzolar: (ism va rol, holat — «imzolangan DD.MM.YYYY» yoki «imzo yo'q»).
    pub signatures: Vec<(String, String)>,
    /// Disklеymer.
    pub disclaimer: String,
}

/// Kelishuv hujjatining typst shabloni.
pub fn template(document: &AgreementDocument) -> String {
    let mut out = String::new();
    out.push_str("#set page(paper: \"a4\", margin: 2cm)\n");
    out.push_str(&format!(
        "#set text(font: \"{FONT_FAMILY}\", size: 11pt, lang: \"uz\")\n"
    ));
    out.push_str(&format!(
        "#align(center)[#text(size: 18pt, weight: \"bold\")[#({})]]\n",
        lit(&document.title)
    ));
    out.push_str(&format!(
        "#align(center)[#text(fill: luma(90))[#({})]]\n",
        lit(&document.subtitle)
    ));
    out.push_str(&format!(
        "#align(center)[#text(fill: luma(90))[#({})]]\n",
        lit(&document.status_line)
    ));
    out.push_str("#v(1.2em)\n");
    out.push_str(&section("1. Kim bilan kim?"));
    out.push_str(&pairs_table(&document.parties));
    out.push_str(&section("2. Kim nima qo'shyapti?"));
    out.push_str(&pairs_table(&document.contributions));
    out.push_str(&section("3. Kim nima qiladi?"));
    out.push_str(&pairs_table(&document.duties));
    for (title, body) in [
        ("4. Foyda qanday bo'linadi?", &document.profit),
        ("5. Zarar ko'rilsa nima bo'ladi?", &document.loss),
        ("6. Pul qayerda, hisobni kim yuritadi?", &document.custody),
        ("7. Qanday ajralib chiqiladi?", &document.exit),
        ("8. Kelisha olmasangiz, kim hakam?", &document.arbiter),
        ("9. Qachon yangilanadi?", &document.term),
    ] {
        out.push_str(&section(title));
        out.push_str(&format!("#par[#({})]\n", lit(body)));
    }
    out.push_str("#v(1em)\n");
    out.push_str(&section("Imzolar"));
    out.push_str(&pairs_table(&document.signatures));
    out.push_str("#v(2em)\n");
    out.push_str(&format!(
        "#text(size: 9pt, fill: luma(110))[#({})]\n",
        lit(&document.disclaimer)
    ));
    out
}
