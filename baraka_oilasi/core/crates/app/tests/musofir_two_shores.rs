#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! M2 — «Ikki qirg'oq» (docs/musofir/SPEC.md 5, ADR-0004): uydagi oila qurilmasi (`HOME`) musofirning
//! maoshi, xarajatlari, jamg'armasi, sozlamalari va kurslarini olmaydi; uyga yuborilganni qabul qiladi,
//! maqsad bo'yicha sarflaydi; musofir maqsadlar qoldig'ini ko'radi.

use std::path::{Path, PathBuf};
use std::sync::Arc;

use baraka_app::*;
use baraka_storage::repo::sync;
use baraka_storage::{Database, Meta};
use chrono::{DateTime, Utc};
use serde_json::{json, Value};

const PASSWORD: &str = "Ikki-qirgoq-2026!";

struct Device {
    path: PathBuf,
    key: DbKey,
    id: String,
    clock: Arc<FixedClock>,
}

impl Device {
    fn new(dir: &Path, name: &str, key: u8) -> Self {
        Self {
            path: dir.join(format!("{name}.db")),
            key: DbKey::from_bytes([key; 32]),
            id: format!("dev-{name}"),
            clock: Arc::new(FixedClock::new(
                DateTime::parse_from_rfc3339("2026-10-18T09:00:00+05:00")
                    .unwrap()
                    .with_timezone(&Utc),
            )),
        }
    }

    fn app(&self) -> App {
        let app = App::open(
            &self.path,
            &self.key,
            &self.id,
            self.clock.clone(),
            Arc::new(UuidV7Gen),
        )
        .unwrap();
        app.set_interchange_kdf(64, 1, 1);
        app
    }

    fn db(&self) -> Database {
        Database::open(&self.path, &self.key).unwrap()
    }

    fn rows(&self, table: &str) -> Vec<serde_json::Map<String, Value>> {
        self.db()
            .read(|c| {
                let hid: String = c.query_row("SELECT id FROM households", [], |r| r.get(0))?;
                sync::dump(c, &hid, table)
            })
            .unwrap()
    }

    fn rows_in(&self, table: &str, space: &str) -> usize {
        self.rows(table)
            .iter()
            .filter(|r| r["space_id"] == json!(space))
            .count()
    }
}

fn minor(m: &MoneyDto) -> i64 {
    m.minor.parse().unwrap()
}

fn err<T: std::fmt::Debug>(r: Result<T, AppError>) -> String {
    r.unwrap_err().code
}

struct Owner {
    app: App,
    mf: String,
    uy: String,
    rustam: String,
    gulnora: String,
}

fn share(purpose: &str, percent: &str) -> MfShareInput {
    MfShareInput {
        purpose: purpose.into(),
        percent: percent.into(),
    }
}

fn mv(kind: &str, amount: &str) -> MfMoveInput {
    MfMoveInput {
        kind: kind.into(),
        amount: amount.into(),
        fee: None,
        received: None,
        occurred_on: None,
        note: None,
        purposes: None,
    }
}

/// Musofirning qurilmasi (xonadon egasi): Uy + Musofir, sozlamalar, kurs, maosh, xarajat, jamg'arma,
/// «Ikki qirg'oq» shartlari 50/30/20 va uyga 1 200 000 von.
fn owner_setup(dev: &Device) -> Owner {
    let app = dev.app();
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Rustam akaning oilasi".into(),
            device_name: "Rustamning telefoni".into(),
            platform: "android".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into(), "MUSOFIR".into()],
            members: vec![
                NewMemberInput {
                    display_name: "Rustam".into(),
                    role: "ADULT".into(),
                },
                NewMemberInput {
                    display_name: "Gulnora".into(),
                    role: "ADULT".into(),
                },
            ],
            income_rhythm: None,
            debts_declared: false,
        })
        .unwrap();
    let id = |k: &str| h.spaces.iter().find(|s| s.kind == k).unwrap().id.clone();
    let member = |n: &str| {
        h.members
            .iter()
            .find(|m| m.display_name == n)
            .unwrap()
            .id
            .clone()
    };
    let (mf, uy) = (id("MUSOFIR"), id("UY"));
    app.mf_set_settings(
        &mf,
        MfSettingsInput {
            country: Some("Koreya".into()),
            work_currency: "KRW".into(),
            share_percent: "20".into(),
            target: Some("120 000 000".into()),
            return_on: Some("2027-12-01".into()),
        },
    )
    .unwrap();
    app.mf_set_rate(
        &mf,
        MfRateInput {
            rate: "9,1".into(),
            rate_on: None,
            source: None,
        },
    )
    .unwrap();
    app.mf_record_income(
        &mf,
        MfIncomeInput {
            kind: "SALARY".into(),
            amount: "2 600 000".into(),
            channel: "CARD".into(),
            occurred_on: None,
            note: Some("Zavod".into()),
        },
    )
    .unwrap();
    let cat = app.categories(&mf).unwrap()[0].id.clone();
    app.mf_record_expense(
        &mf,
        MfExpenseInput {
            amount: "400 000".into(),
            category_id: cat,
            channel: "CARD".into(),
            occurred_on: None,
            note: Some("Ijara".into()),
        },
    )
    .unwrap();
    app.mf_record_move(&mf, mv("FUND_IN", "520 000")).unwrap();
    let gulnora = member("Gulnora");
    let terms = app
        .mf_set_terms(
            &mf,
            MfTermsInput {
                shares: vec![
                    share("HOUSEHOLD", "50"),
                    share("DEBT", "30"),
                    share("BUILD", "20"),
                ],
                receiver_member_id: Some(gulnora.clone()),
                title: "Ikki qirgʻoq".into(),
                items: vec![
                    "Har yuborilgan pulning 50 % — uy xarajati, 30 % — qarz, 20 % — qurilish"
                        .into(),
                    "Pulni Gulnora qabul qiladi va ilovaga yozadi".into(),
                ],
            },
        )
        .unwrap();
    assert_eq!(terms.shares.len(), 3);
    assert_eq!(terms.agreement.as_ref().unwrap().template_key, "REMITTANCE");
    let mut send = mv("SENT_HOME", "1 200 000");
    send.fee = Some("5 000".into());
    send.received = Some("10 900 000".into());
    app.mf_record_move(&mf, send).unwrap();
    Owner {
        app,
        mf,
        uy,
        rustam: member("Rustam"),
        gulnora,
    }
}

fn pair_home(o: &Owner, dev: &Device) -> App {
    let offer = o
        .app
        .pairing_offer(PairingInput {
            role: Some("HOME".into()),
            space_id: Some(o.mf.clone()),
        })
        .unwrap();
    let app = dev.app();
    app.join_household(
        &offer.bytes,
        JoinInput {
            secret: offer.code.clone(),
            device_name: "Uydagi kompyuter".into(),
            platform: "windows".into(),
        },
    )
    .unwrap();
    app
}

fn export(app: &App, peer: &str) -> ExportFileDto {
    app.export_baraka(ExportInput {
        password: PASSWORD.into(),
        mode: "INCREMENTAL".into(),
        peer_device_id: Some(peer.into()),
    })
    .unwrap()
}

fn import(app: &App, file: &ExportFileDto) -> ImportResultDto {
    app.apply_baraka(&file.bytes, PASSWORD, vec![]).unwrap()
}

/// Oila qurilmasida musofirning shaxsiy ma'lumoti fizik jihatdan yo'q.
fn assert_private(dev: &Device, mf: &str) {
    for t in [
        "mf_settings",
        "mf_rates",
        "mf_remittance_terms",
        "incomes",
        "expenses",
        "categories",
    ] {
        assert_eq!(
            dev.rows_in(t, mf),
            0,
            "{t}: Musofir yozuvi oilaga yuborilmasligi kerak"
        );
    }
    let moves = dev.rows("mf_moves");
    assert!(!moves.is_empty());
    for m in &moves {
        assert_eq!(m["kind"], json!("SENT_HOME"));
        assert_eq!(m["fee_minor"], json!(0));
    }
}

#[test]
fn home_device_receives_and_spends_without_seeing_private_data() {
    let dir = tempfile::tempdir().unwrap();
    let owner_dev = Device::new(dir.path(), "rustam", 1);
    let home_dev = Device::new(dir.path(), "uy", 2);
    let o = owner_setup(&owner_dev);
    let home = pair_home(&o, &home_dev);

    // Oila qurilmasi: rol, maxfiylik, shaxsiy bo'limlar yopiq.
    assert_eq!(home.device_role().unwrap().role, "HOME");
    assert_private(&home_dev, &o.mf);
    assert_eq!(home_dev.rows("mf_remittance_parts").len(), 3);
    assert_eq!(err(home.mf_overview(&o.mf, None)), "ROLE_FORBIDDEN");
    assert_eq!(err(home.mf_terms(&o.mf)), "ROLE_FORBIDDEN");
    assert_eq!(
        err(home.mf_record_move(&o.mf, mv("FUND_IN", "1"))),
        "ROLE_FORBIDDEN"
    );
    assert_eq!(
        err(home.pairing_offer(PairingInput {
            role: None,
            space_id: None
        })),
        "ROLE_FORBIDDEN"
    );

    // Uy tomoni: yuborish «yo'lda», ulushlar 50/30/20, musofir yozgan summa taklif sifatida.
    let v = home.mf_two_shores(&o.mf).unwrap();
    assert_eq!(v.pending, 1);
    let r = &v.remittances[0];
    assert!(r.receipt.is_none());
    assert_eq!(minor(&r.sent), 1_200_000);
    assert_eq!(r.sent.currency, "KRW");
    assert_eq!(minor(r.expected.as_ref().unwrap()), 1_090_000_000);
    let shares: Vec<(&str, &str)> = r
        .shares
        .iter()
        .map(|s| (s.purpose.as_str(), s.percent.as_str()))
        .collect();
    assert_eq!(
        shares,
        [("HOUSEHOLD", "50"), ("DEBT", "30"), ("BUILD", "20")]
    );

    // Kelishuv — Uy makonida, oila tasdiqlaydi.
    let agreements = home.family_agreements(&o.uy).unwrap();
    let a = agreements
        .iter()
        .find(|a| a.template_key == "REMITTANCE")
        .unwrap();
    assert_eq!(a.status, "DRAFT");
    home.confirm_family_agreement(&o.uy, &a.id, &o.gulnora)
        .unwrap();

    // Qabul: 10 900 000 so'm — Uy daromadi; maqsadlarga bo'linish (mf_remittance rm-001).
    let receipt = |amount: &str| MfReceiptInput {
        received: amount.into(),
        channel: "CARD".into(),
        member_id: Some(o.gulnora.clone()),
        received_on: None,
        note: None,
    };
    let move_id = r.move_id.clone();
    let v = home
        .mf_confirm_receipt(&o.mf, &move_id, receipt("10 900 000"))
        .unwrap();
    assert_eq!(v.pending, 0);
    assert_eq!(
        v.remittances[0]
            .receipt
            .as_ref()
            .unwrap()
            .member_name
            .as_deref(),
        Some("Gulnora")
    );
    let alloc: Vec<i64> = v.remittances[0]
        .allocation
        .iter()
        .map(|a| minor(&a.amount))
        .collect();
    assert_eq!(alloc, [545_000_000, 327_000_000, 218_000_000]);
    assert_eq!(
        err(home.mf_confirm_receipt(&o.mf, &move_id, receipt("1"))),
        "ALREADY_RECEIVED"
    );
    let uy_incomes = home_dev.rows("incomes");
    assert!(uy_incomes
        .iter()
        .any(|i| i["space_id"] == json!(o.uy) && i["amount_minor"] == json!(1_090_000_000)));

    // Maqsad bo'yicha xarajat (Uy makonida) va oddiy Uy xarajati.
    let uy_cat = home.categories(&o.uy).unwrap()[0].id.clone();
    let spend = |purpose: &str, amount: &str| MfSpendInput {
        purpose: purpose.into(),
        amount: amount.into(),
        category_id: uy_cat.clone(),
        channel: "CASH".into(),
        occurred_on: None,
        note: Some("Bozor".into()),
    };
    home.mf_record_spend(&o.mf, spend("HOUSEHOLD", "2 000 000"))
        .unwrap();
    let v = home
        .mf_record_spend(&o.mf, spend("DEBT", "3 270 000"))
        .unwrap();
    let bal: Vec<(&str, i64)> = v
        .purposes
        .iter()
        .map(|p| (p.purpose.as_str(), minor(&p.balance)))
        .collect();
    assert_eq!(
        bal,
        [
            ("HOUSEHOLD", 345_000_000),
            ("DEBT", 0),
            ("BUILD", 218_000_000)
        ]
    );
    assert!(!v.overspent);
    home.record_expense(
        &o.uy,
        NewExpenseInput {
            amount: "150 000".into(),
            category_id: uy_cat.clone(),
            channel: "CASH".into(),
            member_id: None,
            occurred_on: None,
            necessity: None,
            obligation_id: None,
            is_gift: false,
            is_ostentation: false,
            funded_by_debt: false,
            note: Some("Non".into()),
        },
    )
    .unwrap();
    let home_view = home.mf_two_shores(&o.mf).unwrap();

    // Oila → musofir: hammasi qabul qilinadi, musofir ham xuddi shu qoldiqni ko'radi.
    let file = export(&home, &owner_dev.id);
    let preview = o.app.inspect_baraka(&file.bytes, PASSWORD).unwrap();
    assert!(preview.rejected.is_empty(), "{:?}", preview.rejected);
    let res = import(&o.app, &file);
    assert_eq!(res.rejected, 0);
    let owner_view = o.app.mf_two_shores(&o.mf).unwrap();
    assert_eq!(owner_view.purposes, home_view.purposes);
    assert_eq!(owner_view.spends.len(), 2);
    let devices = o.app.devices().unwrap();
    assert_eq!(
        devices
            .iter()
            .find(|d| d.id == home_dev.id)
            .unwrap()
            .role
            .as_deref(),
        Some("HOME")
    );
    // Uy xarajati musofirda; uning shaxsiy ma'lumoti joyida (maosh, jamg'arma).
    assert!(owner_dev
        .rows("expenses")
        .iter()
        .any(|e| e["note"] == json!("Non")));
    let o_overview = o.app.mf_overview(&o.mf, None).unwrap();
    assert_eq!(minor(&o_overview.fund.unwrap().balance), 520_000);
    // Musofir ham tasdiqlaydi — kelishuv kuchga kiradi.
    let a = o
        .app
        .confirm_family_agreement(&o.uy, &a.id, &o.rustam)
        .unwrap();
    assert_eq!(a.status, "ACTIVE");

    // Musofir → oila: yangi yuborish va maosh; oila faqat yuborishni oladi.
    o.app
        .mf_record_income(
            &o.mf,
            MfIncomeInput {
                kind: "OTHER_INCOME".into(),
                amount: "300 000".into(),
                channel: "CASH".into(),
                occurred_on: None,
                note: Some("Bonus".into()),
            },
        )
        .unwrap();
    let mut send = mv("SENT_HOME", "500 000");
    send.purposes = Some(vec![share("HOUSEHOLD", "100")]);
    o.app.mf_record_move(&o.mf, send).unwrap();
    let res = import(&home, &export(&o.app, &home_dev.id));
    assert_eq!(res.conflicts_local + res.conflicts_remote, 0);
    assert_private(&home_dev, &o.mf);
    let v = home.mf_two_shores(&o.mf).unwrap();
    assert_eq!(v.pending, 1);
    assert_eq!(v.remittances.len(), 2);
    let a = home
        .family_agreements(&o.uy)
        .unwrap()
        .into_iter()
        .find(|a| a.template_key == "REMITTANCE")
        .unwrap();
    assert_eq!(a.status, "ACTIVE");
}

#[test]
fn owner_rejects_private_rows_forged_on_home_device() {
    let dir = tempfile::tempdir().unwrap();
    let owner_dev = Device::new(dir.path(), "rustam", 1);
    let home_dev = Device::new(dir.path(), "uy", 2);
    let o = owner_setup(&owner_dev);
    let home = pair_home(&o, &home_dev);
    // Birinchi fayl — musofir qurilmani rolga bog'laydi.
    import(&o.app, &export(&home, &owner_dev.id));

    // Ilovasi o'zgartirilgan oila qurilmasi musofirning jamg'armasiga yozuv qo'shdi.
    let db = home_dev.db();
    db.write(|tx| {
        let hid: String = tx.query_row("SELECT id FROM households", [], |r| r.get(0))?;
        let m = Meta {
            now: "2026-10-18T05:00:00.000Z".into(),
            device_id: home_dev.id.clone(),
        };
        tx.execute(
            "INSERT INTO mf_moves (id, household_id, space_id, kind, amount_minor, currency, occurred_on,
                note, created_at, updated_at, origin_device_id, updated_by_device_id)
             VALUES ('forged', ?1, ?2, 'FUND_OUT', 520000, 'KRW', '2026-10-18', 'olindi', ?3, ?3, ?4, ?4)",
            [hid.as_str(), o.mf.as_str(), m.now.as_str(), m.device_id.as_str()],
        )?;
        Ok(())
    })
    .unwrap();
    drop(db);
    let file = export(&home, &owner_dev.id);
    let preview = o.app.inspect_baraka(&file.bytes, PASSWORD).unwrap();
    let reasons: Vec<(&str, &str)> = preview
        .rejected
        .iter()
        .map(|r| (r.table.as_str(), r.reason.as_str()))
        .collect();
    assert_eq!(reasons, [("mf_moves", "ROLE_FORBIDDEN")]);
    import(&o.app, &file);
    assert_eq!(
        minor(
            &o.app
                .mf_overview(&o.mf, None)
                .unwrap()
                .fund
                .unwrap()
                .balance
        ),
        520_000
    );
}

#[test]
fn shares_validation_and_overspend() {
    let dir = tempfile::tempdir().unwrap();
    let owner_dev = Device::new(dir.path(), "rustam", 1);
    let o = owner_setup(&owner_dev);
    let mut send = mv("SENT_HOME", "100 000");
    send.purposes = Some(vec![share("HOUSEHOLD", "60"), share("DEBT", "30")]);
    assert_eq!(err(o.app.mf_record_move(&o.mf, send)), "SHARES_NOT_FULL");
    let mut fund = mv("FUND_IN", "1 000");
    fund.purposes = Some(vec![share("HOUSEHOLD", "100")]);
    assert_eq!(err(o.app.mf_record_move(&o.mf, fund)), "FIELD_NOT_ALLOWED");

    // Musofirning o'zi ham qabul qila oladi (oilasi ilovasiz bo'lsa); ortiq sarf taqiqlanmaydi.
    let v = o.app.mf_two_shores(&o.mf).unwrap();
    let id = v.remittances[0].move_id.clone();
    o.app
        .mf_confirm_receipt(
            &o.mf,
            &id,
            MfReceiptInput {
                received: "10 900 000".into(),
                channel: "CARD".into(),
                member_id: None,
                received_on: None,
                note: None,
            },
        )
        .unwrap();
    let cat = o.app.categories(&o.uy).unwrap()[0].id.clone();
    let v = o
        .app
        .mf_record_spend(
            &o.mf,
            MfSpendInput {
                purpose: "CEREMONY".into(),
                amount: "1 000 000".into(),
                category_id: cat,
                channel: "CASH".into(),
                occurred_on: None,
                note: None,
            },
        )
        .unwrap();
    assert!(v.overspent);
    let ceremony = v.purposes.iter().find(|p| p.purpose == "CEREMONY").unwrap();
    assert_eq!(minor(&ceremony.balance), -100_000_000);
}
