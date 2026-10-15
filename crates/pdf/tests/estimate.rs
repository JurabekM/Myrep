//! Smeta testlari: PDF yaratiladi va snapshot bilan mos.
#![allow(clippy::expect_used, clippy::unwrap_used)]

use std::path::PathBuf;

use pdf::{CeremonyEstimate, render_estimate};

fn sample() -> CeremonyEstimate {
    CeremonyEstimate {
        title: "O'g'limizning to'yi".to_owned(),
        subtitle: "To'y · 12.03.2027 · Ixcham: 1 kun, 100 kishi".to_owned(),
        generated_on: "15.10.2026".to_owned(),
        lines: vec![
            [
                "Osh".to_owned(),
                "100 × 45 000 soʻm".to_owned(),
                "Jamg'arma".to_owned(),
                "4 500 000 soʻm".to_owned(),
            ],
            [
                "Xonanda".to_owned(),
                "1 × 6 000 000 soʻm".to_owned(),
                "Oila hissasi".to_owned(),
                "6 000 000 soʻm".to_owned(),
            ],
            [
                "Sarpo".to_owned(),
                "1 × 8 000 000 soʻm".to_owned(),
                "Qarz".to_owned(),
                "8 000 000 soʻm".to_owned(),
            ],
        ],
        summary: vec![
            ("Umumiy".to_owned(), "18 500 000 soʻm".to_owned()),
            ("Jamg'arma".to_owned(), "4 500 000 soʻm".to_owned()),
            ("Oila hissasi".to_owned(), "6 000 000 soʻm".to_owned()),
            ("Kutilayotgan to'yona".to_owned(), "0 soʻm".to_owned()),
            ("Qarz".to_owned(), "8 000 000 soʻm".to_owned()),
        ],
        note: "Qarz qatori bor: oilaviy muhokama o'tkazilgan. Holat: tasdiqlangan.".to_owned(),
        disclaimer: "Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    }
}

fn snapshot_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("snapshots")
        .join("estimate.pdf")
}

#[test]
fn smeta_pdf_yaratiladi() {
    let bytes = render_estimate(&sample()).expect("smeta");
    assert!(bytes.starts_with(b"%PDF-"), "PDF sarlavhasi yo'q");
    assert!(bytes.len() > 1_000, "PDF juda kichik");
}

#[test]
fn smeta_snapshot_bilan_mos() {
    let bytes = render_estimate(&sample()).expect("smeta");
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
        "smeta PDF snapshot'dan farq qiladi (UPDATE_SNAPSHOTS=1 bilan yangilang)"
    );
}
