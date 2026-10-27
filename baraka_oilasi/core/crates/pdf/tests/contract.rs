#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! Sheriklik shartnomasi (U11): lokallar, chizilgan imzolar, determinizm, in'eksiyaga
//! chidamlilik, PNG snapshot (barcha sahifalar).

use baraka_agreements::{signature_svg, Stroke};
use baraka_pdf::{
    ContractBuyout, ContractBuyoutRow, ContractCapital, ContractClause, ContractDuty,
    ContractParty, ContractSigner, PartnershipContract, PdfEngine, PdfLocale,
};
use chrono::NaiveDate;
use sha2::{Digest, Sha256};

fn today() -> NaiveDate {
    NaiveDate::from_ymd_opt(2026, 10, 15).unwrap()
}

fn answered(rows: &[(&str, &str)]) -> ContractClause {
    ContractClause {
        status: "ANSWERED".into(),
        reason: None,
        rows: rows
            .iter()
            .map(|(k, v)| ((*k).to_string(), (*v).to_string()))
            .collect(),
    }
}

fn contract(locale: PdfLocale) -> PartnershipContract {
    let svg = signature_svg(&[Stroke(vec![[60, 300], [260, 90], [480, 310], [760, 120]])]);
    PartnershipContract {
        ident: "par-0192a000".into(),
        locale,
        title: "Tikuvchilik ustaxonasi".into(),
        kind: "MUDARABA".into(),
        version: Some("v2".into()),
        hash_code: "F8B2-EF8C-8E72-218F".into(),
        review_pending: true,
        parties: vec![
            ContractParty {
                name: "Dilshod Tursunov".into(),
                role: "CAPITAL_PROVIDER".into(),
                capital: "30 000 000 soʻm".into(),
                profit_share: "50%".into(),
                loss_share: Some("100%".into()),
            },
            ContractParty {
                name: "Feruza Karimova".into(),
                role: "WORKER".into(),
                capital: "0 soʻm".into(),
                profit_share: "50%".into(),
                loss_share: Some("0%".into()),
            },
        ],
        capital: vec![ContractCapital {
            party: "Dilshod Tursunov".into(),
            kind: "EQUIPMENT".into(),
            description: "Tikuv mashinasi (2 ta)".into(),
            amount: "24 000 000 soʻm".into(),
        }],
        duties: answered(&[]),
        duty_rows: vec![ContractDuty {
            title: "Buyurtmalarni tikish".into(),
            owner: "Feruza Karimova".into(),
            breach: "1 kun ichida xabar beradi. Ўзбекча: ў қ ғ ҳ".into(),
        }],
        negligence: Some("Uskunani boshqa ishga berish".into()),
        custody: answered(&[
            ("contract.custody.location", "Alohida karta"),
            ("contract.custody.keeper", "Feruza Karimova"),
            ("contract.custody.review", "30"),
        ]),
        exit: answered(&[
            ("contract.exit.notice", "30"),
            ("contract.exit.valuation", "Bozor narxi"),
            ("contract.exit.payout", "3 oy ichida"),
            ("contract.exit.assets", "Uskuna Dilshod akaga qaytadi"),
        ]),
        buyout: Some(ContractBuyout {
            seller: "Dilshod Tursunov".into(),
            buyer: "Feruza Karimova".into(),
            rows: (1..=10)
                .map(|i| ContractBuyoutRow {
                    period: i.to_string(),
                    date: format!("30.{:02}.2027", i),
                    payment: "3 000 000 soʻm".into(),
                    remaining: format!("{} 000 000 soʻm", 30 - 3 * i),
                    seller: format!("{}%", 100 - 10 * i),
                    buyer: format!("{}%", 10 * i),
                })
                .collect(),
        }),
        arbiter: answered(&[
            ("contract.arbiter.name", "Hamid aka"),
            ("contract.arbiter.role", "qoʻshni"),
        ]),
        term: ContractClause {
            status: "NOT_APPLICABLE".into(),
            reason: Some("Muddatsiz, har yili koʻrib chiqamiz".into()),
            rows: vec![],
        },
        witnesses: vec!["Dilnoza opa".into()],
        signers: vec![
            ContractSigner {
                role: "PARTY".into(),
                name: "Dilshod Tursunov".into(),
                signed_at: Some("15.10.2026".into()),
                svg: Some(svg.clone()),
            },
            ContractSigner {
                role: "PARTY".into(),
                name: "Feruza Karimova".into(),
                signed_at: None,
                svg: None,
            },
            ContractSigner {
                role: "WITNESS".into(),
                name: "Dilnoza opa".into(),
                signed_at: Some("15.10.2026".into()),
                svg: Some(svg),
            },
            ContractSigner {
                role: "ARBITER".into(),
                name: "Hamid aka".into(),
                signed_at: None,
                svg: None,
            },
        ],
    }
}

#[test]
fn contract_renders_in_all_locales_with_signatures() {
    let engine = PdfEngine::new();
    let dir =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../target/pdf-snapshots");
    std::fs::create_dir_all(&dir).unwrap();
    for (locale, name) in [
        (PdfLocale::Uz, "uz"),
        (PdfLocale::UzCyrl, "uz-Cyrl"),
        (PdfLocale::Ru, "ru"),
    ] {
        let r = contract(locale).render(&engine, today()).unwrap();
        assert!(r.warnings.is_empty(), "{name}: {:?}", r.warnings);
        assert!(r.pdf.starts_with(b"%PDF-"));
        for (i, page) in r.document.pages().iter().enumerate() {
            let pixmap = typst_render::render(page, &typst_render::RenderOptions::default());
            std::fs::write(
                dir.join(format!("partnership_contract-{name}-{}.png", i + 1)),
                pixmap.encode_png().unwrap(),
            )
            .unwrap();
        }
    }
    let a = contract(PdfLocale::Uz)
        .render(&engine, today())
        .unwrap()
        .pdf;
    let b = contract(PdfLocale::Uz)
        .render(&PdfEngine::new(), today())
        .unwrap()
        .pdf;
    assert_eq!(Sha256::digest(&a), Sha256::digest(&b));
}

#[test]
fn contract_user_text_is_not_code() {
    let mut c = contract(PdfLocale::Uz);
    c.title = "#panic(\"x\") #read(\"/etc/hostname\")".into();
    c.parties[0].name = "$x^2$ *qalin* <lbl> @ref ]".into();
    c.duty_rows[0].breach = "#import \"/etc/passwd\"".into();
    c.term.reason = Some("#image(\"sig-0.svg\")".into());
    c.signers[1].name = "\")] #panic(\"y".into();
    let r = c.render(&PdfEngine::new(), today()).unwrap();
    assert!(r.warnings.is_empty(), "{:?}", r.warnings);
}
