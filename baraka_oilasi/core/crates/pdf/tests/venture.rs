#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! Sheriklik davri hisoboti (U12): lokallar, determinizm, in'eksiyaga chidamlilik, PNG snapshot.

use baraka_pdf::{PdfEngine, PdfLocale, ReportBuyout, ReportEntry, ReportParty, VentureReport};
use chrono::NaiveDate;
use sha2::{Digest, Sha256};

fn today() -> NaiveDate {
    NaiveDate::from_ymd_opt(2026, 12, 1).unwrap()
}

fn entry(date: &str, kind: &str, cat: Option<&str>, note: &str, amount: &str) -> ReportEntry {
    ReportEntry {
        date: date.into(),
        kind: kind.into(),
        category: cat.map(Into::into),
        note: note.into(),
        amount: amount.into(),
        attachments: u32::from(kind == "EXPENSE"),
    }
}

fn report(locale: PdfLocale) -> VentureReport {
    VentureReport {
        ident: "vp-0192a000".into(),
        locale,
        title: "Tikuvchilik ustaxonasi".into(),
        kind: "MUDARABA".into(),
        period_no: 1,
        start: "01.11.2026".into(),
        end: "30.11.2026".into(),
        version: "v2".into(),
        loss_policy: "CAPITAL_FIRST".into(),
        totals: [
            ("vtotal.income", "15 000 000 soʻm"),
            ("vtotal.expense", "7 000 000 soʻm"),
            ("vtotal.result", "8 000 000 soʻm"),
            ("vtotal.distributable", "8 000 000 soʻm"),
        ]
        .iter()
        .map(|(k, v)| ((*k).to_string(), (*v).to_string()))
        .collect(),
        entries: vec![
            entry(
                "05.11.2026",
                "INCOME",
                Some("ORDER"),
                "Toʻy koʻylaklari",
                "+12 000 000 soʻm",
            ),
            entry(
                "09.11.2026",
                "EXPENSE",
                Some("MATERIAL"),
                "Mato va ip",
                "−5 000 000 soʻm",
            ),
            entry(
                "30.11.2026",
                "EXPENSE",
                Some("WAGE"),
                "Zamira",
                "−2 000 000 soʻm",
            ),
            entry(
                "30.11.2026",
                "CORRECTION",
                None,
                "Sana xato yozilgan",
                "+3 000 000 soʻm",
            ),
        ],
        parties: vec![
            ReportParty {
                name: "Sobir Qodirov".into(),
                role: "CAPITAL_PROVIDER".into(),
                share: "3 200 000 soʻm".into(),
                recovered: "0 soʻm".into(),
                liability: "0 soʻm".into(),
                payout: "6 200 000 soʻm".into(),
                capital_after: "27 000 000 soʻm".into(),
            },
            ReportParty {
                name: "Nilufar Karimova".into(),
                role: "WORKER".into(),
                share: "4 800 000 soʻm".into(),
                recovered: "0 soʻm".into(),
                liability: "0 soʻm".into(),
                payout: "1 800 000 soʻm".into(),
                capital_after: "3 000 000 soʻm".into(),
            },
        ],
        buyout: Some(ReportBuyout {
            seller: "Sobir Qodirov".into(),
            buyer: "Nilufar Karimova".into(),
            paid: "1, 2".into(),
            unpaid: "—".into(),
            amount: "3 000 000 soʻm".into(),
            progress: "2 / 20".into(),
        }),
        negligence: None,
        chain_head: "ba06ad59d6c270a58182a304bd376535d814dd210520f8359a4969f870b26903".into(),
        chain_short_code: "BA06-AD59-D6C2-70A5".into(),
    }
}

#[test]
fn report_renders_in_all_locales() {
    let engine = PdfEngine::new();
    let dir =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../target/pdf-snapshots");
    std::fs::create_dir_all(&dir).unwrap();
    for (locale, name) in [
        (PdfLocale::Uz, "uz"),
        (PdfLocale::UzCyrl, "uz-Cyrl"),
        (PdfLocale::Ru, "ru"),
    ] {
        let r = report(locale).render(&engine, today()).unwrap();
        assert!(r.warnings.is_empty(), "{name}: {:?}", r.warnings);
        assert!(r.pdf.starts_with(b"%PDF-"));
        for (i, page) in r.document.pages().iter().enumerate() {
            let pixmap = typst_render::render(page, &typst_render::RenderOptions::default());
            std::fs::write(
                dir.join(format!("venture_report-{name}-{}.png", i + 1)),
                pixmap.encode_png().unwrap(),
            )
            .unwrap();
        }
    }
    let a = report(PdfLocale::Uz).render(&engine, today()).unwrap().pdf;
    let b = report(PdfLocale::Uz)
        .render(&PdfEngine::new(), today())
        .unwrap()
        .pdf;
    assert_eq!(Sha256::digest(&a), Sha256::digest(&b));
}

#[test]
fn report_user_text_is_not_code() {
    let mut r = report(PdfLocale::Uz);
    r.title = "#panic(\"x\") #read(\"/etc/hostname\")".into();
    r.entries[0].note = "$x^2$ *qalin* <lbl> @ref ] #import \"/etc/passwd\"".into();
    r.parties[0].name = "\")] #panic(\"y".into();
    r.negligence = Some("#image(\"qr.svg\")".into());
    let out = r.render(&PdfEngine::new(), today()).unwrap();
    assert!(out.warnings.is_empty(), "{:?}", out.warnings);
}
