//! Qo'lda tekshiruv: `cargo run -p pdf --example dump -- out.pdf`
use pdf::{council_minutes, CouncilMinutes, MinutesCategory, MinutesConsent};

fn main() {
    let path = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "minutes.pdf".into());
    let m = CouncilMinutes {
        household: "Karimovlar oilasi".into(),
        date: "2026-10-09".into(),
        month: "2026-09".into(),
        attendees: vec![
            ("Karim aka".into(), "Katta".into()),
            ("Dilnoza".into(), "Katta".into()),
        ],
        review: vec![
            ("Daromad".into(), "8 000 000 so'm".into()),
            ("Oʻzbekiston · gʻoya · oʼrik".into(), "950 000 so'm".into()),
        ],
        categories: vec![
            MinutesCategory {
                name: "Oziq-ovqat".into(),
                necessity: "Zarur".into(),
                last_change: None,
            },
            MinutesCategory {
                name: "Gazak va ichimlik".into(),
                necessity: "Havas".into(),
                last_change: Some("Dilnoza, 2026-10-09".into()),
            },
        ],
        limit_amount: Some("1 000 000 so'm".into()),
        limit_status: "Faol: barcha kattalar rozi".into(),
        consents: vec![
            MinutesConsent {
                name: "Karim aka".into(),
                at: Some("2026-10-09".into()),
            },
            MinutesConsent {
                name: "Dilnoza".into(),
                at: None,
            },
        ],
        signers: vec!["Karim aka".into(), "Dilnoza".into()],
        disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".into(),
    };
    std::fs::write(&path, council_minutes(&m).expect("pdf")).expect("write");
}
