//! Ochiq hisob ko'rigi bayonnomasi (SPEC 2F.5, D13A) va hakam uchun ish papkasi (SPEC 2F.8).
//! Matnlar — satr literallari; sarlavhalar — kod ichidagi doimiylar (markup foydalanuvchidan kirmaydi).

use crate::{FONT_FAMILY, lit, pairs_table, section};

/// Ko'rik bayonnomasi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReviewMinutes {
    /// Sarlavha (kelishuv nomi).
    pub title: String,
    /// Davr matni.
    pub period: String,
    /// Yaratilgan sana.
    pub generated_on: String,
    /// Davr yozuvlari: sana, tur, tomon, summa.
    pub entries: Vec<[String; 4]>,
    /// Yakun: (nomi, summa).
    pub summary: Vec<(String, String)>,
    /// Ochiq hodisalar: (vazifa, sabab).
    pub incidents: Vec<(String, String)>,
    /// Tomonlar belgisi: (ism, «ko'rdim, roziman» / «e'tirozim bor: …»).
    pub marks: Vec<(String, String)>,
    /// Zanjir holati matni (`chain_head` bilan).
    pub chain_line: String,
    /// Disklеymer.
    pub disclaimer: String,
}

fn head(title: &str, sub1: &str, sub2: &str) -> String {
    format!(
        "#set page(paper: \"a4\", margin: 2cm, numbering: \"1 / 1\")\n#set text(font: \"{FONT_FAMILY}\", size: 11pt, lang: \"uz\")\n\
         #align(center)[#text(size: 18pt, weight: \"bold\")[#({})]]\n\
         #align(center)[#text(fill: luma(90))[#({})]]\n\
         #align(center)[#text(fill: luma(90))[#({})]]\n#v(1.2em)\n",
        lit(title),
        lit(sub1),
        lit(sub2)
    )
}

fn four_col(header: [&str; 4], rows: &[[String; 4]]) -> String {
    let mut out = String::from(
        "#table(columns: (1fr, 1.4fr, 1.4fr, 1.2fr), stroke: (x: none, y: 0.4pt + luma(200)), inset: (x: 4pt, y: 5pt),\n",
    );
    out.push_str(&format!(
        "  [*{}*], [*{}*], [*{}*], [*{}*],\n",
        header[0], header[1], header[2], header[3]
    ));
    for [a, b, c, d] in rows {
        out.push_str(&format!(
            "  [#({})], [#({})], [#({})], [#({})],\n",
            lit(a),
            lit(b),
            lit(c),
            lit(d)
        ));
    }
    out.push_str(")\n");
    out
}

/// Bayonnoma shabloni.
pub fn minutes_template(minutes: &ReviewMinutes) -> String {
    let mut out = head(
        &minutes.title,
        &format!("Ochiq hisob ko'rigi bayonnomasi · {}", minutes.period),
        &format!("Tuzilgan sana: {}", minutes.generated_on),
    );
    out.push_str(&section("Davr yozuvlari"));
    out.push_str(&four_col(
        ["Sana", "Tur", "Tomon", "Summa"],
        &minutes.entries,
    ));
    out.push_str("#v(0.8em)\n");
    out.push_str(&section("Davr yakuni"));
    out.push_str(&pairs_table(&minutes.summary));
    out.push_str("#v(0.8em)\n");
    out.push_str(&section("Ochiq vazifa hodisalari"));
    if minutes.incidents.is_empty() {
        out.push_str("#par[Ochiq hodisa yo'q.]\n");
    } else {
        out.push_str(&pairs_table(&minutes.incidents));
    }
    out.push_str("#v(0.8em)\n");
    out.push_str(&section("Tomonlar belgisi"));
    out.push_str(&pairs_table(&minutes.marks));
    out.push_str("#v(0.8em)\n");
    out.push_str(&format!(
        "#text(size: 9pt, fill: luma(90))[#({})]\n",
        lit(&minutes.chain_line)
    ));
    out.push_str("#v(2em)\n");
    out.push_str(&format!(
        "#text(size: 9pt, fill: luma(110))[#({})]\n",
        lit(&minutes.disclaimer)
    ));
    out
}

/// Hakam uchun ish papkasi — bitta PDF, mundarija va sahifa raqamlari bilan.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ArbiterFolder {
    /// Sarlavha.
    pub title: String,
    /// Yaratilgan sana.
    pub generated_on: String,
    /// Amaldagi versiya satri.
    pub version_line: String,
    /// Shartnoma bo'limlari: (band, matn).
    pub contract: Vec<(String, String)>,
    /// Versiyalar tarixi: (versiya, izoh).
    pub versions: Vec<(String, String)>,
    /// Hisob yozuvlari: sana, tur, tomon, summa.
    pub entries: Vec<[String; 4]>,
    /// Zanjir tekshiruvi natijasi.
    pub chain_line: String,
    /// Ko'rik bayonnomalari: (davr, xulosa).
    pub reviews: Vec<(String, String)>,
    /// Vazifa hodisalari: (vazifa va sana, sabab va holat).
    pub incidents: Vec<(String, String)>,
    /// Nizolar va talablar: (mavzu va ochgan tomon, talab va qaror).
    pub disputes: Vec<(String, String)>,
    /// Disklеymer.
    pub disclaimer: String,
}

fn chapter(title: &str) -> String {
    // Sarlavha matni — kod ichidagi doimiy (markup xavfsiz); mundarija shu sarlavhalardan tuziladi.
    format!("#pagebreak(weak: true)\n= {title}\n#v(0.4em)\n")
}

fn pairs_or_empty(rows: &[(String, String)], empty: &str) -> String {
    if rows.is_empty() {
        format!("#par[{empty}]\n")
    } else {
        pairs_table(rows)
    }
}

/// Ish papkasi shabloni: mundarija (`outline`), sahifa raqamlari, bo'limlar.
pub fn folder_template(folder: &ArbiterFolder) -> String {
    let mut out = head(
        &folder.title,
        "Hakam uchun ish papkasi",
        &format!(
            "Tuzilgan sana: {} · {}",
            folder.generated_on, folder.version_line
        ),
    );
    out.push_str("#set heading(numbering: \"1.\")\n");
    out.push_str("#outline(title: \"Mundarija\", indent: auto)\n");
    out.push_str(&chapter("Shartnomaning amaldagi versiyasi"));
    out.push_str(&pairs_table(&folder.contract));
    out.push_str(&chapter("Versiyalar tarixi"));
    out.push_str(&pairs_or_empty(&folder.versions, "Faqat birinchi versiya."));
    out.push_str(&chapter("Hisob yozuvlari va zanjir tekshiruvi"));
    if folder.entries.is_empty() {
        out.push_str("#par[Hisob yozuvi yo'q.]\n");
    } else {
        out.push_str(&four_col(
            ["Sana", "Tur", "Tomon", "Summa"],
            &folder.entries,
        ));
    }
    out.push_str(&format!("#par[#({})]\n", lit(&folder.chain_line)));
    out.push_str(&chapter("Ko'rik bayonnomalari"));
    out.push_str(&pairs_or_empty(&folder.reviews, "Ko'rik o'tkazilmagan."));
    out.push_str(&chapter("Vazifa hodisalari"));
    out.push_str(&pairs_or_empty(&folder.incidents, "Hodisa yo'q."));
    out.push_str(&chapter("Nizolar va tomonlar talablari"));
    out.push_str(&pairs_or_empty(&folder.disputes, "Nizo yo'q."));
    out.push_str("#v(2em)\n");
    out.push_str(&format!(
        "#text(size: 9pt, fill: luma(110))[#({})]\n",
        lit(&folder.disclaimer)
    ));
    out
}
