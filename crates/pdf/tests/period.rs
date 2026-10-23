//! Davr hisoboti testlari: PDF yaratiladi va snapshot bilan mos.
#![allow(clippy::expect_used, clippy::unwrap_used)]

use std::path::PathBuf;

use pdf::{PeriodReport, render_period_report};

fn sample() -> PeriodReport {
    PeriodReport {
        title: "Tikuv sexi".to_owned(),
        period: "01.11.2026 — 30.11.2026".to_owned(),
        generated_on: "01.12.2026".to_owned(),
        entries: vec![
            [
                "05.11.2026".to_owned(),
                "Kirim".to_owned(),
                "Akmal Karimov".to_owned(),
                "6 000 000 soʻm".to_owned(),
            ],
            [
                "12.11.2026".to_owned(),
                "Xarajat".to_owned(),
                "Akmal Karimov".to_owned(),
                "2 500 000 soʻm".to_owned(),
            ],
        ],
        summary: vec![
            ("Kirim".to_owned(), "6 000 000 soʻm".to_owned()),
            ("Xarajat".to_owned(), "2 500 000 soʻm".to_owned()),
            ("Sof foyda".to_owned(), "3 500 000 soʻm".to_owned()),
        ],
        distribution: vec![
            (
                "Akmal Karimov (60 %)".to_owned(),
                "2 100 000 soʻm · buyout ayirmasi 1 000 000 soʻm".to_owned(),
            ),
            (
                "Jasur Rahimov (40 %)".to_owned(),
                "1 400 000 soʻm".to_owned(),
            ),
        ],
        chain_head: "0".repeat(64),
        note: "Fors-major hodisasi yo'q. Taqsimot shartnomaning 4–5-bandlari bo'yicha.".to_owned(),
        disclaimer: "Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    }
}

fn snapshot_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("snapshots")
        .join("period-report.pdf")
}

#[test]
fn davr_hisoboti_pdf_yaratiladi() {
    let bytes = render_period_report(&sample()).expect("hisobot");
    assert!(bytes.starts_with(b"%PDF-"));
    assert!(bytes.len() > 1_000);
}

#[test]
fn davr_hisoboti_snapshot_bilan_mos() {
    let bytes = render_period_report(&sample()).expect("hisobot");
    let path = snapshot_path();
    if std::env::var_os("UPDATE_SNAPSHOTS").is_some() {
        std::fs::create_dir_all(path.parent().expect("papka")).expect("papka yaratilsin");
        std::fs::write(&path, &bytes).expect("snapshot yozilsin");
        return;
    }
    let expected =
        std::fs::read(&path).expect("snapshot mavjud (UPDATE_SNAPSHOTS=1 bilan yarating)");
    assert!(bytes == expected, "davr hisoboti snapshot'dan farq qiladi");
}
