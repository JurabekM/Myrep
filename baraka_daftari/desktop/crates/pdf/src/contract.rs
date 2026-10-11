//! Sheriklik shartnomasi PDF'i (D12, SPEC 2E.2). Ma'lumotlar tayyor formatlangan matn; foydalanuvchi
//! matnlari typst string literal sifatida qo'yiladi (markup injection yo'q).
//!
//! ⚠️ Shablon yurist va ulamo tasdig'idan o'tmagan; PDF'da bu ochiq yozilgan.

use crate::{minutes::lit, render_pdf, PdfError};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContractParty {
    pub name: String,
    pub role: String,
    /// «Kapital: 10 000 000 so'm».
    pub capital: String,
    /// «Foyda ulushi: 50%».
    pub share: String,
    /// Kapital qatorlari: «Overlock — 4 000 000 so'm».
    pub items: Vec<String>,
    /// Ilovada tasdiqlangan sana yoki `None`.
    pub signed_at: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContractDoc {
    pub title: String,
    pub version: u32,
    pub kind: String,
    pub status: String,
    pub parties: Vec<ContractParty>,
    /// Foyda va zarar qoidalari (matn qatorlari).
    pub rules: Vec<String>,
    pub term: String,
    pub reporting: String,
    pub end_clause: String,
    pub dispute_clause: String,
    /// (ism, tasdiqlangan sana).
    pub witnesses: Vec<(String, Option<String>)>,
    /// Buyout haqida qisqa matn (bo'lsa).
    pub buyout: Option<String>,
    pub legal_note: String,
    pub disclaimer: String,
}

fn text(s: &str) -> String {
    format!("[#{}]", lit(s))
}

fn sign_block(name: &str, signed: Option<&str>) -> String {
    let status = signed.map_or_else(
        || "ilovada hali tasdiqlanmagan".to_owned(),
        |d| format!("ilovada tasdiqlangan: {d}"),
    );
    format!(
        "[#v(1cm)#line(length: 100%, stroke: 0.4pt)#text(size: 8pt)[#{} \u{2014} #{}]]",
        lit(name),
        lit(&status)
    )
}

#[must_use]
pub fn contract_markup(d: &ContractDoc) -> String {
    let mut s = String::from(
        "#set page(paper: \"a4\", margin: (x: 2cm, y: 2cm))\n\
         #set text(font: \"DejaVu Sans\", size: 10pt, lang: \"uz\")\n\
         #set par(justify: false, leading: 0.6em)\n",
    );
    s.push_str(&format!(
        "#align(center)[#text(size: 16pt, weight: \"bold\")[#{}]]\n#align(center)[#{}]\n#v(0.6em)\n",
        lit(&d.title),
        lit(&format!("{} \u{b7} {} \u{b7} {}-versiya", d.kind, d.status, d.version))
    ));
    s.push_str(&format!(
        "== #{}\n",
        lit("1. Tomonlar va kiritilgan kapital")
    ));
    for p in &d.parties {
        s.push_str(&format!(
            "#text(weight: \"bold\")[#{}] #{}\n",
            lit(&p.name),
            lit(&format!("\u{2014} {}", p.role))
        ));
        let mut lines = vec![p.capital.clone(), p.share.clone()];
        lines.extend(p.items.iter().map(|i| format!("\u{2022} {i}")));
        s.push_str(&format!(
            "#list(marker: [], {})\n",
            lines.iter().map(|l| text(l)).collect::<Vec<_>>().join(", ")
        ));
    }
    s.push_str(&format!("== #{}\n", lit("2. Foyda va zarar qoidalari")));
    for r in &d.rules {
        s.push_str(&format!("#{}\n#v(0.2em)\n", lit(r)));
    }
    s.push_str(&format!(
        "== #{}\n#{}\n",
        lit("3. Muddat va hisobot"),
        lit(&format!("{}. {}", d.term, d.reporting))
    ));
    s.push_str(&format!(
        "== #{}\n#{}\n",
        lit("4. Muddat tugaganda"),
        lit(&d.end_clause)
    ));
    s.push_str(&format!(
        "== #{}\n#{}\n",
        lit("5. Nizolarni hal qilish"),
        lit(&d.dispute_clause)
    ));
    if let Some(b) = &d.buyout {
        s.push_str(&format!(
            "== #{}\n#{}\n",
            lit("6. Bosqichma-bosqich sotib olish"),
            lit(b)
        ));
    }
    s.push_str(&format!("== #{}\n", lit("Tomonlar imzosi")));
    let cells: Vec<String> = d
        .parties
        .iter()
        .map(|p| sign_block(&p.name, p.signed_at.as_deref()))
        .collect();
    s.push_str(&format!(
        "#grid(columns: (1fr, 1fr), gutter: 1em, row-gutter: 0.8em,\n  {}\n)\n",
        cells.join(",\n  ")
    ));
    s.push_str(&format!("== #{}\n", lit("Guvohlar")));
    let w: Vec<String> = (0..d.witnesses.len().max(2))
        .map(|i| match d.witnesses.get(i) {
            Some((n, at)) => sign_block(n, at.as_deref()),
            None => sign_block(&format!("Guvoh {}", i + 1), None),
        })
        .collect();
    s.push_str(&format!(
        "#grid(columns: (1fr, 1fr), gutter: 1em, row-gutter: 0.8em,\n  {}\n)\n",
        w.join(",\n  ")
    ));
    s.push_str(&format!(
        "#v(1fr)\n#text(size: 8pt, fill: luma(90))[#{} #{}]\n",
        lit(&d.legal_note),
        lit(&d.disclaimer)
    ));
    s
}

/// Shartnomani PDF qiladi.
///
/// # Errors
/// Shablon yoki eksport xatosi.
pub fn partnership_contract(d: &ContractDoc) -> Result<Vec<u8>, PdfError> {
    render_pdf(&contract_markup(d))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> ContractDoc {
        ContractDoc {
            title: "Tikuvchilik ustaxonasi".into(),
            version: 2,
            kind: "Mudaraba".into(),
            status: "Qoralama".into(),
            parties: vec![
                ContractParty {
                    name: "Karim aka".into(),
                    role: "Kapital egasi".into(),
                    capital: "Kapital: 8 000 000 so'm".into(),
                    share: "Foyda ulushi: 40%".into(),
                    items: vec!["Overlock \u{2014} 4 000 000 so'm".into()],
                    signed_at: Some("2026-10-11".into()),
                },
                ContractParty {
                    name: "Zamira".into(),
                    role: "Ishchi (mehnat)".into(),
                    capital: "Kapital: 0 so'm".into(),
                    share: "Foyda ulushi: 60%".into(),
                    items: vec![],
                    signed_at: None,
                },
            ],
            rules: vec![
                "Foyda — sof foydaning kelishilgan foizi; kafolatlangan summa yo'q.".into(),
                "Moliyaviy zarar kapital egasi zimmasida, ishchi mehnatidan ayriladi.".into(),
            ],
            term: "Muddat: 12 oy".into(),
            reporting: "Hisobot: har oy".into(),
            end_clause: "Uskunalar kapital egasiga qaytariladi yoki buyout davom etadi".into(),
            dispute_clause: "Avval mahalla oqsoqoli huzurida kelishiladi".into(),
            witnesses: vec![("Dilshod".into(), Some("2026-10-11".into()))],
            buyout: Some("Ishchi uskunani 6 davrda sotib oladi.".into()),
            legal_note: "Shablon yurist va ulamo tasdig'idan o'tmagan; yuridik kuchi va islomiy muvofiqligi haqida va'da berilmaydi.".into(),
            disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".into(),
        }
    }

    #[test]
    fn contract_text_snapshot_keeps_uzbek_letters() {
        let mut d = sample();
        d.parties[1].name = "Zamira O\u{2bb}ktamova".into();
        let pdf = partnership_contract(&d).unwrap();
        let raw = pdf_extract::extract_text_from_mem(&pdf).unwrap();
        let t = raw.split_whitespace().collect::<Vec<_>>().join(" ");
        assert!(t.contains("O\u{2bb}ktamova"), "{t}");
        insta::assert_snapshot!("partnership_contract_text", t);
    }

    #[test]
    fn injection_and_minimal_inputs_are_safe() {
        let mut d = sample();
        d.parties[0].name = "#panic(\"x\") $ * _ \"); #read(\"/etc/passwd\")".into();
        d.rules.push("`raw` <label> @ref".into());
        assert!(partnership_contract(&d).is_ok());
        d.witnesses.clear();
        d.buyout = None;
        d.parties[0].items.clear();
        assert!(partnership_contract(&d).is_ok());
    }
}
