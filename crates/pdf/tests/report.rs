//! Bayonnoma testlari: PDF yaratiladi, o'zbekcha belgilar shriftda bor, natija snapshot bilan mos.
#![allow(clippy::expect_used, clippy::unwrap_used)]

use std::path::PathBuf;

use pdf::{CouncilReport, FONT_FAMILY, font_data, render_council_report};
use typst::foundations::Bytes;
use typst::text::Font;

/// Testlar uchun namunaviy bayonnoma: o'zbekcha belgilar (ʻ, ʼ), ismlar va summalar bilan.
fn sample() -> CouncilReport {
    CouncilReport {
        title: "Oila kengashi bayonnomasi".to_owned(),
        period: "01.10.2026 — 31.10.2026".to_owned(),
        generated_on: "15.10.2026".to_owned(),
        summary: vec![
            ("Zarur".to_owned(), "1 200 000 soʻm".to_owned()),
            ("Kerak".to_owned(), "800 000 soʻm".to_owned()),
            ("Havas".to_owned(), "350 000 soʻm".to_owned()),
            (
                "Sadaqa (havas hisobiga kirmaydi)".to_owned(),
                "100 000 soʻm".to_owned(),
            ),
        ],
        categories: vec![
            ("Ijara".to_owned(), "Zarur".to_owned()),
            ("Gazak va ichimlik".to_owned(), "Havas".to_owned()),
            ("Bolalar".to_owned(), "Kerak".to_owned()),
        ],
        limit_status: "Chegara faol: 1 000 000 soʻm (kattalar roziligi bor)".to_owned(),
        adults: vec![
            ("O'zim".to_owned(), "rozi".to_owned()),
            ("Dilshod".to_owned(), "rozi".to_owned()),
        ],
        disclaimer: "Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    }
}

fn snapshot_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("snapshots")
        .join("council-report.pdf")
}

#[test]
fn bayonnoma_pdf_yaratiladi() {
    let bytes = render_council_report(&sample()).expect("bayonnoma");
    assert!(bytes.starts_with(b"%PDF-"), "PDF sarlavhasi yo'q");
    assert!(bytes.len() > 1_000, "PDF juda kichik");
}

#[test]
fn ozbekcha_belgilar_shriftda_bor() {
    // ʻ (U+02BB) va ʼ (U+02BC) — o'zbekcha apostrof belgilari; shrift ularni bera olishi shart.
    let font = font_data()
        .flat_map(|data| Font::iter(Bytes::new(data.to_vec())))
        .find(|font| font.info().family == FONT_FAMILY)
        .expect("Libertinus Serif shrifti ilova ichida");
    for ch in ['ʻ', 'ʼ'] {
        assert!(
            font.ttf().glyph_index(ch).is_some(),
            "shriftda {ch:?} (U+{:04X}) belgisi yo'q",
            ch as u32
        );
    }
}

#[test]
fn bayonnoma_snapshot_bilan_mos() {
    let bytes = render_council_report(&sample()).expect("bayonnoma");
    let path = snapshot_path();
    if std::env::var_os("UPDATE_SNAPSHOTS").is_some() {
        std::fs::create_dir_all(path.parent().expect("papka")).expect("papka yaratilsin");
        std::fs::write(&path, &bytes).expect("snapshot yozilsin");
        return;
    }
    let expected =
        std::fs::read(&path).expect("snapshot mavjud (UPDATE_SNAPSHOTS=1 bilan yarating)");
    assert!(
        bytes == expected,
        "bayonnoma snapshot'dan farq qiladi; o'zgarish kutilgan bo'lsa, UPDATE_SNAPSHOTS=1 bilan yangilang"
    );
}

/// Kelishuv hujjati namunasi: o'zbekcha belgilar, 9 bo'lim, imzolar.
fn agreement_sample() -> pdf::AgreementDocument {
    pdf::AgreementDocument {
        title: "Sheriklik kelishuvi — «Non sexi»".to_owned(),
        subtitle: "Sheriklik (musharaka) · 1-versiya".to_owned(),
        status_line: "Imzolangan · amal qiladi 01.10.2026 dan · tuzilgan 15.10.2026".to_owned(),
        parties: vec![
            ("Anvar Karimov".to_owned(), "sherik (men)".to_owned()),
            ("Dilshod Rahimov".to_owned(), "sherik".to_owned()),
        ],
        contributions: vec![
            (
                "Anvar Karimov".to_owned(),
                "pul: 3 000 000 soʻm — naqd".to_owned(),
            ),
            (
                "Dilshod Rahimov".to_owned(),
                "mehnat: yetkazib berish".to_owned(),
            ),
        ],
        duties: vec![(
            "Buyurtmalarni yetkazish — Dilshod Rahimov".to_owned(),
            "Bajarilmasa: 1 kun ichida xabar beradi va oʻrniga yechim topadi".to_owned(),
        )],
        profit: "Foyda ulush bo'yicha: Anvar Karimov 50 %, Dilshod Rahimov 50 %.".to_owned(),
        loss: "Zarar kapitalga mutanosib (musharaka).".to_owned(),
        custody:
            "Pul: umumiy karta. Hisobni yuritadi: Anvar Karimov. Ko'rib chiqish: har 30 kunda."
                .to_owned(),
        exit: "Ogohlantirish: 30 kun. Baholash: oxirgi koʻrik boʻyicha. To'lash: 3 oy ichida."
            .to_owned(),
        arbiter: "Sobir hoji (mahalla oqsoqoli).".to_owned(),
        term: "Muddat: 12 oy. Keyingi ko'rib chiqish: 01.10.2027.".to_owned(),
        signatures: vec![
            (
                "Anvar Karimov (tomon)".to_owned(),
                "imzolangan 15.10.2026".to_owned(),
            ),
            (
                "Dilshod Rahimov (tomon)".to_owned(),
                "imzolangan 15.10.2026".to_owned(),
            ),
            ("Sobir hoji (hakam)".to_owned(), "imzo yoʻq".to_owned()),
        ],
        disclaimer: "Shaxsiy hisob uchun yozuv. Yuridik maslahat emas.".to_owned(),
    }
}

#[test]
fn kelishuv_pdf_snapshot_bilan_mos() {
    let bytes = pdf::render_agreement(&agreement_sample()).expect("kelishuv");
    assert!(bytes.starts_with(b"%PDF-"));
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("snapshots")
        .join("agreement.pdf");
    if std::env::var_os("UPDATE_SNAPSHOTS").is_some() {
        std::fs::write(&path, &bytes).expect("snapshot yozilsin");
        return;
    }
    let expected =
        std::fs::read(&path).expect("snapshot mavjud (UPDATE_SNAPSHOTS=1 bilan yarating)");
    assert!(expected == bytes, "kelishuv PDF'i snapshot bilan mos emas");
}
