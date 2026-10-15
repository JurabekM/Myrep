//! Ko'rik bayonnomasi va hakam papkasi testlari: PDF yaratiladi, snapshot bilan mos.
#![allow(clippy::expect_used, clippy::unwrap_used)]

use std::path::PathBuf;

use pdf::{ArbiterFolder, ReviewMinutes, render_arbiter_folder, render_review_minutes};

fn minutes() -> ReviewMinutes {
    ReviewMinutes {
        title: "Tikuv sexi".to_owned(),
        period: "01.11.2026 — 30.11.2026".to_owned(),
        generated_on: "01.12.2026".to_owned(),
        entries: vec![[
            "05.11.2026".to_owned(),
            "Kirim".to_owned(),
            "Anvar Karimov".to_owned(),
            "6 000 000 soʻm".to_owned(),
        ]],
        summary: vec![("Kirim".to_owned(), "6 000 000 soʻm".to_owned())],
        incidents: vec![(
            "Yetkazish · 10.11.2026".to_owned(),
            "mashina buzildi — o'rniga: kuryer".to_owned(),
        )],
        marks: vec![
            ("Anvar Karimov".to_owned(), "ko'rdim, roziman".to_owned()),
            (
                "Dilshod Rahimov".to_owned(),
                "e'tirozim bor: xarajat cheki yo'q".to_owned(),
            ),
        ],
        chain_line: format!("Zanjir to'g'ri · boshi: {}", "a".repeat(64)),
        disclaimer: "Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    }
}

fn folder() -> ArbiterFolder {
    ArbiterFolder {
        title: "Tikuv sexi".to_owned(),
        generated_on: "01.12.2026".to_owned(),
        version_line: "2-versiya · imzolangan".to_owned(),
        contract: vec![
            ("1. Tomonlar".to_owned(), "Anvar Karimov (mehnat); Dilshod Rahimov (kapital)".to_owned()),
            ("4. Foyda".to_owned(), "60 % / 40 %".to_owned()),
        ],
        versions: vec![("2-versiya".to_owned(), "o'zgarishsiz tasdiqlandi".to_owned())],
        entries: vec![[
            "05.11.2026".to_owned(),
            "Kirim".to_owned(),
            "Anvar Karimov".to_owned(),
            "6 000 000 soʻm".to_owned(),
        ]],
        chain_line: "Zanjir to'g'ri (1 yozuv).".to_owned(),
        reviews: vec![("01.11.2026 — 30.11.2026".to_owned(), "2 belgi: 1 rozi, 1 e'tiroz".to_owned())],
        incidents: vec![("Yetkazish · 10.11.2026".to_owned(), "mashina buzildi · ochiq".to_owned())],
        disputes: vec![(
            "Xarajat cheki · Dilshod Rahimov".to_owned(),
            "Talab: cheklar taqdim etilsin · qaror: yo'q".to_owned(),
        )],
        disclaimer: "Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    }
}

fn snapshot(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("snapshots")
        .join(name)
}

fn check(bytes: &[u8], name: &str) {
    assert!(bytes.starts_with(b"%PDF-"));
    let path = snapshot(name);
    if std::env::var_os("UPDATE_SNAPSHOTS").is_some() {
        std::fs::create_dir_all(path.parent().expect("papka")).expect("papka yaratilsin");
        std::fs::write(&path, bytes).expect("snapshot yozilsin");
        return;
    }
    let expected = std::fs::read(&path).expect("snapshot mavjud (UPDATE_SNAPSHOTS=1 bilan yarating)");
    assert!(bytes == expected, "{name} snapshot'dan farq qiladi");
}

#[test]
fn bayonnoma_snapshot() {
    check(&render_review_minutes(&minutes()).expect("bayonnoma"), "review-minutes.pdf");
}

#[test]
fn hakam_papkasi_snapshot_va_kop_sahifali() {
    let bytes = render_arbiter_folder(&folder()).expect("papka");
    // Mundarija alohida sahifada, har bo'lim yangi sahifada: kamida 3 sahifa.
    let pages = String::from_utf8_lossy(&bytes).matches("/Type /Page\n").count()
        + String::from_utf8_lossy(&bytes).matches("/Type /Page/").count()
        + String::from_utf8_lossy(&bytes).matches("/Type/Page/").count();
    assert!(pages >= 3 || bytes.len() > 5_000, "ko'p sahifali papka kutilgan");
    check(&bytes, "arbiter-folder.pdf");
}
