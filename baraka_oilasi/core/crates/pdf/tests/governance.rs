#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! U13: ko'rik bayonnomasi va «hakam uchun ish papkasi» — lokallar, barcha bo'limlar (sahifa
//! matnidan tekshiriladi), mundarija, determinizm, in'eksiyaga chidamlilik, PNG snapshot.

use baraka_pdf::{
    AckLine, ArbiterFolder, FolderClaim, FolderDecision, FolderPeriod, FolderReview, FolderVersion,
    IncidentLine, PdfEngine, PdfLocale, ReportEntry, ReviewProtocol,
};
use chrono::NaiveDate;
use sha2::{Digest, Sha256};
use typst::layout::{Frame, FrameItem};

fn today() -> NaiveDate {
    NaiveDate::from_ymd_opt(2027, 1, 2).unwrap()
}

fn texts(frame: &Frame, out: &mut String) {
    for (_, item) in frame.items() {
        match item {
            FrameItem::Group(g) => texts(&g.frame, out),
            FrameItem::Text(t) => out.push_str(t.text.as_str()),
            _ => {}
        }
    }
}

/// Barcha sahifalar matni, bo'shliqlarsiz (typst so'zlarni alohida bo'laklarga ajratishi mumkin).
fn page_text(doc: &typst_layout::PagedDocument) -> String {
    let mut s = String::new();
    for p in doc.pages() {
        texts(&p.frame, &mut s);
    }
    s.split_whitespace().collect()
}

fn squash(s: &str) -> String {
    s.split_whitespace().collect()
}

fn entry(date: &str, kind: &str, note: &str, amount: &str) -> ReportEntry {
    ReportEntry {
        date: date.into(),
        kind: kind.into(),
        category: (kind == "INCOME").then(|| "ORDER".to_string()),
        note: note.into(),
        amount: amount.into(),
        attachments: 0,
    }
}

fn incident() -> IncidentLine {
    IncidentLine {
        date: "10.12.2026".into(),
        duty: "Buyurtmalarni tikish va topshirish".into(),
        party: "Feruza Karimova".into(),
        reason: "Kasal bo'ldim, 3 kun ishlay olmayman".into(),
        solution: "Zamira o'rnimga tikadi".into(),
        status: "OPEN".into(),
    }
}

fn protocol(locale: PdfLocale) -> ReviewProtocol {
    ReviewProtocol {
        ident: "rv-0192a000".into(),
        locale,
        title: "Tikuvchilik ustaxonasi".into(),
        review_no: 1,
        range: "01.11.2026 — 31.12.2026".into(),
        held_on: "02.01.2027".into(),
        reason: "SCHEDULED".into(),
        version: "v2".into(),
        totals: vec![
            ("vtotal.income".into(), "24 000 000 soʻm".into()),
            ("vtotal.result".into(), "+13 500 000 soʻm".into()),
            ("vtotal.periods".into(), "3".into()),
        ],
        entries: vec![
            entry(
                "05.11.2026",
                "INCOME",
                "Toʻy koʻylaklari",
                "+12 000 000 soʻm",
            ),
            entry(
                "02.12.2026",
                "FORCE_MAJEURE",
                "Omborni suv bosdi",
                "−1 000 000 soʻm",
            ),
        ],
        incidents: vec![incident()],
        acks: vec![
            AckLine {
                party: "Otabek Qodirov".into(),
                verdict: "AGREE".into(),
                note: String::new(),
            },
            AckLine {
                party: "Feruza Karimova".into(),
                verdict: "OBJECT".into(),
                note: "Mato narxi chekdan ko'ra yuqori yozilgan".into(),
            },
        ],
        chain_ok: true,
        chain_head: "a765".repeat(16),
        chain_short_code: "A765-A765-A765-A765".into(),
    }
}

fn folder(locale: PdfLocale) -> ArbiterFolder {
    ArbiterFolder {
        ident: "dp-0192a000".into(),
        locale,
        title: "Tikuvchilik ustaxonasi".into(),
        kind: "MUDARABA".into(),
        arbiter: "Hamid Yusupov".into(),
        opened_on: "03.01.2027".into(),
        opened_by: "Otabek Qodirov".into(),
        subject: "Dekabr foydasi taqsimoti".into(),
        clauses: "4, 5".into(),
        claims: vec![
            FolderClaim {
                party: "Otabek Qodirov".into(),
                claim: "Fors-major zarari mehnat egasining beparvoligidan".into(),
            },
            FolderClaim {
                party: "Feruza Karimova".into(),
                claim: "Ombor kaliti kapital egasida edi".into(),
            },
        ],
        terms: vec![
            (
                "folder.term.parties".into(),
                "Otabek Qodirov 40%, Feruza Karimova 60%".into(),
            ),
            ("folder.term.capital".into(), "30 000 000 soʻm".into()),
        ],
        versions: vec![
            FolderVersion {
                no: "v1".into(),
                date: "15.10.2026".into(),
                hash_code: "250E-CBAA-CCD5-29DB".into(),
                signatures: "4 / 4".into(),
                note: String::new(),
                in_force: false,
            },
            FolderVersion {
                no: "v2".into(),
                date: "15.10.2026".into(),
                hash_code: "EF7C-F91B-D087-6D6D".into(),
                signatures: "4 / 4".into(),
                note: "RENEWED_UNCHANGED".into(),
                in_force: true,
            },
        ],
        periods: (1..=3)
            .map(|n| FolderPeriod {
                title: format!("{n} · 01.11.2026 — 30.11.2026"),
                totals: vec![("vtotal.result".into(), "+8 000 000 soʻm".into())],
                entries: vec![entry(
                    "05.11.2026",
                    "INCOME",
                    "Buyurtma",
                    "+12 000 000 soʻm",
                )],
            })
            .collect(),
        chain_ok: true,
        chain_entries: 21,
        chain_short_code: "A765-1DD8-4DAD-994D".into(),
        reviews: vec![FolderReview {
            no: "1".into(),
            range: "01.11.2026 — 31.12.2026".into(),
            held_on: "02.01.2027".into(),
            acks: vec![
                AckLine {
                    party: "Otabek Qodirov".into(),
                    verdict: "AGREE".into(),
                    note: String::new(),
                },
                AckLine {
                    party: "Feruza Karimova".into(),
                    verdict: "OBJECT".into(),
                    note: "Mato narxi".into(),
                },
            ],
            chain_code: "A765-A765-A765-A765".into(),
            integrity: "INTACT".into(),
        }],
        incidents: vec![incident()],
        decision: Some(FolderDecision {
            decided_on: "10.01.2027".into(),
            arbiter: "Hamid Yusupov".into(),
            decision: "Zarar kapitalga mutanosib qoladi; ombor kaliti endi ikkalasida.".into(),
            outcome: "AMEND".into(),
        }),
    }
}

#[test]
fn protocol_renders_in_all_locales() {
    let engine = PdfEngine::new();
    for locale in [PdfLocale::Uz, PdfLocale::UzCyrl, PdfLocale::Ru] {
        let r = protocol(locale).render(&engine, today()).unwrap();
        assert!(r.warnings.is_empty(), "{:?}", r.warnings);
        assert!(r.pdf.starts_with(b"%PDF-"));
    }
    let r = protocol(PdfLocale::Uz).render(&engine, today()).unwrap();
    let text = page_text(&r.document);
    for needle in [
        "Ochiq hisob koʻrigi bayonnomasi",
        "Koʻrdim, roziman",
        "Eʼtirozim bor",
        "A765-A765-A765-A765",
    ] {
        assert!(text.contains(&squash(needle)), "{needle}");
    }
}

#[test]
fn folder_has_all_sections_toc_and_snapshot() {
    let engine = PdfEngine::new();
    let dir =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../target/pdf-snapshots");
    std::fs::create_dir_all(&dir).unwrap();
    for (locale, name, sections) in [
        (
            PdfLocale::Uz,
            "uz",
            [
                "Mundarija",
                "1. Nizo va tomonlarning talablari",
                "2. Amaldagi shartnoma va versiyalar tarixi",
                "3. Hisob yozuvlari va zanjir tekshiruvi",
                "4. Koʻrik bayonnomalari",
                "5. Vazifa hodisalari",
                "6. Hakam qarori",
            ],
        ),
        (
            PdfLocale::Ru,
            "ru",
            [
                "Содержание",
                "1. Спор и требования сторон",
                "2. Действующий договор и история версий",
                "3. Учётные записи и проверка цепочки",
                "4. Протоколы сверок",
                "5. Случаи по обязанностям",
                "6. Решение арбитра",
            ],
        ),
    ] {
        let r = folder(locale).render(&engine, today()).unwrap();
        assert!(r.warnings.is_empty(), "{name}: {:?}", r.warnings);
        assert!(r.document.pages().len() >= 2, "{name}");
        let text = page_text(&r.document);
        for s in sections {
            // Mundarijada va bo'limning o'zida — kamida ikki marta.
            let n = text.matches(&squash(s)).count();
            assert!(
                n >= if s.starts_with(char::is_numeric) {
                    2
                } else {
                    1
                },
                "{name}: {s} ({n})"
            );
        }
        for (i, page) in r.document.pages().iter().enumerate() {
            let pixmap = typst_render::render(page, &typst_render::RenderOptions::default());
            std::fs::write(
                dir.join(format!("arbiter_folder-{name}-{}.png", i + 1)),
                pixmap.encode_png().unwrap(),
            )
            .unwrap();
        }
    }
    let a = folder(PdfLocale::Uz).render(&engine, today()).unwrap().pdf;
    let b = folder(PdfLocale::Uz)
        .render(&PdfEngine::new(), today())
        .unwrap()
        .pdf;
    assert_eq!(Sha256::digest(&a), Sha256::digest(&b));
    let mut none = folder(PdfLocale::UzCyrl);
    none.decision = None;
    none.reviews.clear();
    let r = none.render(&engine, today()).unwrap();
    assert!(r.warnings.is_empty());
}

#[test]
fn folder_user_text_is_not_code() {
    let mut f = folder(PdfLocale::Uz);
    f.subject = "#panic(\"x\") = Sarlavha <lbl> @ref".into();
    f.claims[0].claim = "#read(\"/etc/passwd\") $x$ *b*".into();
    f.decision.as_mut().unwrap().decision = "\")] #outline()".into();
    let r = f.render(&PdfEngine::new(), today()).unwrap();
    assert!(r.warnings.is_empty(), "{:?}", r.warnings);
}
