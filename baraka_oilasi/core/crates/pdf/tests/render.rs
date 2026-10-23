#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! PDF render testlari: lokallar, determinizm, in'eksiyaga chidamlilik, PNG snapshot (ko'rib chiqish uchun).

use baraka_pdf::{LoanReceipt, PdfEngine, PdfLocale, ScheduleLine};
use chrono::NaiveDate;
use sha2::{Digest, Sha256};

fn today() -> NaiveDate {
    NaiveDate::from_ymd_opt(2026, 10, 15).unwrap()
}

fn receipt(locale: PdfLocale) -> LoanReceipt {
    LoanReceipt {
        ident: "agr-0192a000".into(),
        locale,
        lender: "Gʻayrat Oʻgʻilov".into(),
        borrower: "Karim Rahmonov".into(),
        amount: "2 000 000 soʻm".into(),
        issued_on: "15.10.2026".into(),
        due_on: "15.01.2027".into(),
        place: "Toshkent, Chorsu mahallasi".into(),
        schedule: vec![
            ScheduleLine {
                date: "15.11.2026".into(),
                amount: "700 000 soʻm".into(),
            },
            ScheduleLine {
                date: "15.12.2026".into(),
                amount: "700 000 soʻm".into(),
            },
            ScheduleLine {
                date: "15.01.2027".into(),
                amount: "600 000 soʻm".into(),
            },
        ],
        witnesses: vec!["Hasan Yusupov".into(), "Ҳасан Қодиров".into()],
        note: Some("Taʼmirlash uchun. Ўзбекча кирилл: ў қ ғ ҳ".into()),
        chain_head: Some("f8b2ef8c8e72218faa742a2a997ed401e71c6a4ab251080ca78ef5a5ee3bd89a".into()),
        chain_short_code: Some("F8B2-EF8C-8E72-218F".into()),
    }
}

fn snapshot_dir() -> std::path::PathBuf {
    let dir =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../target/pdf-snapshots");
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

#[test]
fn renders_all_locales_without_warnings() {
    let engine = PdfEngine::new();
    for (locale, name) in [
        (PdfLocale::Uz, "uz"),
        (PdfLocale::UzCyrl, "uz-Cyrl"),
        (PdfLocale::Ru, "ru"),
    ] {
        let r = receipt(locale).render(&engine, today()).unwrap();
        assert!(r.warnings.is_empty(), "{name}: {:?}", r.warnings);
        assert!(r.pdf.starts_with(b"%PDF-"));
        assert_eq!(r.document.pages().len(), 1, "{name}");
        let pixmap = typst_render::render(
            &r.document.pages()[0],
            &typst_render::RenderOptions::default(),
        );
        std::fs::write(
            snapshot_dir().join(format!("loan_receipt-{name}.png")),
            pixmap.encode_png().unwrap(),
        )
        .unwrap();
        std::fs::write(
            snapshot_dir().join(format!("loan_receipt-{name}.pdf")),
            &r.pdf,
        )
        .unwrap();
    }
}

#[test]
fn output_is_deterministic() {
    let engine = PdfEngine::new();
    let a = receipt(PdfLocale::Uz).render(&engine, today()).unwrap().pdf;
    let b = receipt(PdfLocale::Uz)
        .render(&PdfEngine::new(), today())
        .unwrap()
        .pdf;
    assert_eq!(Sha256::digest(&a), Sha256::digest(&b));
}

#[test]
fn user_text_is_never_executed_as_typst() {
    let engine = PdfEngine::new();
    let mut r = receipt(PdfLocale::Uz);
    r.note = Some("#panic(\"x\") ] #import \"/etc/passwd\" $x^2$ *qalin* @ref <lbl>".into());
    r.lender = "#read(\"/etc/hostname\")".into();
    let out = r.render(&engine, today()).unwrap();
    assert!(out.warnings.is_empty(), "{:?}", out.warnings);
}

#[test]
fn chain_block_is_optional() {
    let engine = PdfEngine::new();
    let mut r = receipt(PdfLocale::Ru);
    r.chain_head = None;
    r.chain_short_code = None;
    r.schedule.clear();
    r.note = None;
    r.witnesses.clear();
    assert!(r.render(&engine, today()).is_ok());
}
