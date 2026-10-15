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
