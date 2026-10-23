//! Marosim kengashi bayonnomasi testlari: PDF yaratiladi va snapshot bilan mos.
#![allow(clippy::expect_used, clippy::unwrap_used)]

use std::path::PathBuf;

use pdf::{DiscussionMinutes, render_discussion_minutes};

fn sample() -> DiscussionMinutes {
    DiscussionMinutes {
        title: "O'g'limizning to'yi".to_owned(),
        subtitle: "To'y · 12.03.2027".to_owned(),
        generated_on: "17.10.2026".to_owned(),
        headers: vec![
            "Ko'rsatkich".to_owned(),
            "Katta".to_owned(),
            "Ixcham".to_owned(),
        ],
        rows: vec![
            vec![
                "Hajmi".to_owned(),
                "3 kun, 200 kishi".to_owned(),
                "1 kun, 100 kishi".to_owned(),
            ],
            vec![
                "Umumiy narx".to_owned(),
                "17 000 000 soʻm".to_owned(),
                "4 500 000 soʻm".to_owned(),
            ],
            vec![
                "Qarz qismi".to_owned(),
                "8 000 000 soʻm".to_owned(),
                "0 soʻm".to_owned(),
            ],
            vec![
                "Qarzni to'lash muddati".to_owned(),
                "14 oy".to_owned(),
                "—".to_owned(),
            ],
            vec![
                "Shu pulga muqobil".to_owned(),
                "5 oylik zarur xarajat".to_owned(),
                "1 oylik zarur xarajat".to_owned(),
            ],
        ],
        decision: vec![
            ("Tanlangan stsenariy".to_owned(), "Ixcham".to_owned()),
            (
                "Qaror".to_owned(),
                "Hajmni 100 kishiga qisqartiramiz, sarpo oila hissasidan, qarz olinmaydi."
                    .to_owned(),
            ),
            ("Boshlangan".to_owned(), "17.10.2026".to_owned()),
            ("Yakunlangan".to_owned(), "17.10.2026".to_owned()),
        ],
        adults: vec![
            ("Akmal Karimov".to_owned(), "rozi".to_owned()),
            ("Zarina Karimova".to_owned(), "rozi".to_owned()),
        ],
        disclaimer: "Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    }
}

fn snapshot_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("snapshots")
        .join("discussion-minutes.pdf")
}

#[test]
fn bayonnoma_pdf_yaratiladi() {
    let bytes = render_discussion_minutes(&sample()).expect("bayonnoma");
    assert!(bytes.starts_with(b"%PDF-"), "PDF sarlavhasi yo'q");
    assert!(bytes.len() > 1_000, "PDF juda kichik");
}

#[test]
fn bayonnoma_snapshot_bilan_mos() {
    let bytes = render_discussion_minutes(&sample()).expect("bayonnoma");
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
        "bayonnoma PDF snapshot'dan farq qiladi (UPDATE_SNAPSHOTS=1 bilan yangilang)"
    );
}
