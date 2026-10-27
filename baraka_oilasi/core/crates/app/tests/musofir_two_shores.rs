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
    bobur: String,
    mohira: String,
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
            household_name: "Bobur akaning oilasi".into(),
            device_name: "Boburning telefoni".into(),
            platform: "android".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into(), "MUSOFIR".into()],
            members: vec![
                NewMemberInput {
                    display_name: "Bobur".into(),
                    role: "ADULT".into(),
                },
                NewMemberInput {
                    display_name: "Mohira".into(),
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
            self_investment: false,
        },
    )
    .unwrap();
    app.mf_record_move(&mf, mv("FUND_IN", "520 000")).unwrap();
    let mohira = member("Mohira");
    let terms = app
        .mf_set_terms(
            &mf,
            MfTermsInput {
                shares: vec![
                    share("HOUSEHOLD", "50"),
                    share("DEBT", "30"),
                    share("BUILD", "20"),
                ],
                receiver_member_id: Some(mohira.clone()),
                title: "Ikki qirgʻoq".into(),
                items: vec![
                    "Har yuborilgan pulning 50 % — uy xarajati, 30 % — qarz, 20 % — qurilish"
                        .into(),
                    "Pulni Mohira qabul qiladi va ilovaga yozadi".into(),
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
        bobur: member("Bobur"),
        mohira,
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
    let owner_dev = Device::new(dir.path(), "bobur", 1);
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
    home.confirm_family_agreement(&o.uy, &a.id, &o.mohira)
        .unwrap();

    // Qabul: 10 900 000 so'm — Uy daromadi; maqsadlarga bo'linish (mf_remittance rm-001).
    let receipt = |amount: &str| MfReceiptInput {
        received: amount.into(),
        channel: "CARD".into(),
        member_id: Some(o.mohira.clone()),
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
        Some("Mohira")
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
            self_investment: false,
            learning_plan_id: None,
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
        .confirm_family_agreement(&o.uy, &a.id, &o.bobur)
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
    let owner_dev = Device::new(dir.path(), "bobur", 1);
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
    let owner_dev = Device::new(dir.path(), "bobur", 1);
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

// ---- M3 (docs/musofir/SPEC.md 6): yo'l qarzi uyda to'lanadi, «Qaytdim», sovutish davri ----

fn at(s: &str) -> DateTime<Utc> {
    DateTime::parse_from_rfc3339(s).unwrap().with_timezone(&Utc)
}

fn answers(pairs: &[(&str, &str)]) -> Vec<MfAnswerInput> {
    pairs
        .iter()
        .map(|(k, r)| MfAnswerInput {
            key: (*k).into(),
            reply: (*r).into(),
        })
        .collect()
}

fn decision(kind: &str, amount: &str, a: &[(&str, &str)], choice: Option<&str>) -> MfDecisionInput {
    MfDecisionInput {
        kind: kind.into(),
        title: "Togʻamga qarz".into(),
        amount: amount.into(),
        answers: answers(a),
        choice: choice.map(Into::into),
        note: None,
        promised_percent: None,
    }
}

/// Yo'l uchun tog'adan olingan qarz — Uy makonida, 6 oyda 2 500 000 dan.
fn travel_debt(app: &App, uy: &str) -> String {
    let lines = [
        "15.11.2026",
        "15.12.2026",
        "15.01.2027",
        "15.02.2027",
        "15.03.2027",
        "15.04.2027",
    ]
    .iter()
    .map(|d| ScheduleLineInput {
        date: (*d).into(),
        amount: "2 500 000".into(),
    })
    .collect();
    app.add_debt(
        uy,
        NewDebtInput {
            creditor_type: "RELATIVE".into(),
            creditor: "Togʻam".into(),
            reason: Some("Koreyaga yoʻl va viza".into()),
            currency: "UZS".into(),
            principal: "15 000 000".into(),
            original_principal: None,
            paid_before: None,
            plan_kind: "MANUAL".into(),
            annual_bp: None,
            markup: None,
            months: None,
            first_date: None,
            schedule: lines,
            early_repayment_terms: None,
            prepayment_fee_bp: None,
            is_new: false,
            borrow_check: None,
        },
    )
    .unwrap()
    .id
}

#[test]
fn travel_debt_is_paid_at_home_and_plan_stays_private() {
    let dir = tempfile::tempdir().unwrap();
    let owner_dev = Device::new(dir.path(), "bobur", 1);
    let home_dev = Device::new(dir.path(), "uy", 2);
    let o = owner_setup(&owner_dev);
    let debt_id = travel_debt(&o.app, &o.uy);

    // Belgilash: standart muddat 6 oy; hali qarz maqsadiga pul kelmagan.
    let unknown = MfTravelDebtInput {
        debt_id: Some("yoq".into()),
        target_months: None,
    };
    assert_eq!(err(o.app.mf_set_travel_debt(&o.mf, unknown)), "NOT_FOUND");
    let bad = MfTravelDebtInput {
        debt_id: Some(debt_id.clone()),
        target_months: Some(0),
    };
    assert_eq!(err(o.app.mf_set_travel_debt(&o.mf, bad)), "INVALID_MONTHS");
    let t = o
        .app
        .mf_set_travel_debt(
            &o.mf,
            MfTravelDebtInput {
                debt_id: Some(debt_id.clone()),
                target_months: None,
            },
        )
        .unwrap();
    assert_eq!(t.target_months, 6);
    assert_eq!(t.candidates.len(), 1);
    assert_eq!(t.debt.as_ref().unwrap().creditor, "Togʻam");
    let plan = t.plan.unwrap();
    assert_eq!(minor(&plan.remaining), 1_500_000_000);
    assert_eq!(plan.status, "NO_PAYMENTS");
    assert_eq!(minor(&plan.required_monthly), 250_000_000);

    // Uydagi oila: qabul (30 % — 3 270 000 qarz maqsadiga) va qarz maqsadidan to'lov.
    let home = pair_home(&o, &home_dev);
    import(&o.app, &export(&home, &owner_dev.id));
    let move_id = home.mf_two_shores(&o.mf).unwrap().remittances[0]
        .move_id
        .clone();
    home.mf_confirm_receipt(
        &o.mf,
        &move_id,
        MfReceiptInput {
            received: "10 900 000".into(),
            channel: "CARD".into(),
            member_id: Some(o.mohira.clone()),
            received_on: None,
            note: None,
        },
    )
    .unwrap();
    let pay = |amount: &str| MfDebtPaymentInput {
        debt_id: debt_id.clone(),
        amount: amount.into(),
        paid_on: None,
        note: Some("Togʻamga".into()),
    };
    let v = home.mf_pay_debt(&o.mf, pay("3 270 000")).unwrap();
    let debt_purpose = v.purposes.iter().find(|p| p.purpose == "DEBT").unwrap();
    assert_eq!(minor(&debt_purpose.spent), 327_000_000);
    assert_eq!(minor(&debt_purpose.balance), 0);
    let s = &v.spends[0];
    assert_eq!(
        (s.kind.as_str(), s.purpose.as_str(), s.creditor.as_deref()),
        ("DEBT_PAYMENT", "DEBT", Some("Togʻam"))
    );
    assert!(s.category_id.is_none());
    let home_debt = home.debts_overview(&o.uy).unwrap().debts[0].clone();
    assert_eq!(minor(&home_debt.balance), 1_173_000_000);
    // Reja, qaytish va qarorlar — musofirning shaxsiy hisobi.
    assert_eq!(err(home.mf_travel_debt(&o.mf)), "ROLE_FORBIDDEN");
    let ret = MfReturnInput {
        returned_on: Some("2026-10-01".into()),
        brought_home: None,
        brought_currency: None,
        brought_rate: None,
    };
    assert_eq!(err(home.mf_set_return(&o.mf, ret)), "ROLE_FORBIDDEN");
    assert_eq!(err(home.mf_decisions(&o.mf)), "ROLE_FORBIDDEN");

    // Oila → musofir: to'lov qabul qilinadi; qarz kamaydi.
    let file = export(&home, &owner_dev.id);
    let preview = o.app.inspect_baraka(&file.bytes, PASSWORD).unwrap();
    assert!(preview.rejected.is_empty(), "{:?}", preview.rejected);
    import(&o.app, &file);
    assert_eq!(o.app.mf_two_shores(&o.mf).unwrap().spends.len(), 1);

    // Noyabr: oktyabrda qarz maqsadiga 3 270 000 kelgan → 4 oyda yopiladi (6 oylik maqsadda).
    owner_dev.clock.set(at("2026-11-10T09:00:00+05:00"));
    let plan = o.app.mf_travel_debt(&o.mf).unwrap().plan.unwrap();
    assert_eq!(minor(&plan.remaining), 1_173_000_000);
    assert_eq!(minor(plan.avg_monthly.as_ref().unwrap()), 327_000_000);
    assert_eq!(plan.months_used, 1);
    assert_eq!(plan.months_to_clear, Some(4));
    assert_eq!(plan.clear_on.as_deref(), Some("2027-03-10"));
    assert_eq!(minor(&plan.required_monthly), 195_500_000);
    assert_eq!(plan.status, "ON_TRACK");

    // «Qaytdim»: 1-noyabr, 120 000 000 so'm olib keldi → 90 kunlik sovutish davri.
    let future = MfReturnInput {
        returned_on: Some("2026-11-11".into()),
        brought_home: None,
        brought_currency: None,
        brought_rate: None,
    };
    assert_eq!(err(o.app.mf_set_return(&o.mf, future)), "FUTURE_DATE");
    let ov = o
        .app
        .mf_set_return(
            &o.mf,
            MfReturnInput {
                returned_on: Some("2026-11-01".into()),
                brought_home: Some("120 000 000".into()),
                brought_currency: None,
                brought_rate: None,
            },
        )
        .unwrap();
    let c = ov.cooling.unwrap();
    assert!(c.in_cooling);
    assert_eq!(c.ends_on.as_deref(), Some("2027-01-30"));
    assert_eq!(c.days_left, 81);
    assert_eq!(minor(c.brought_home.as_ref().unwrap()), 12_000_000_000);

    // Katta qaror: tog'am 15 000 000 qarz so'radi (olib kelinganning 12,5 %i, muddatsiz).
    assert_eq!(o.app.mf_decision_questions("LEND").unwrap().len(), 5);
    assert_eq!(o.app.mf_decision_questions("INVEST").unwrap().len(), 13);
    let lend = [
        ("approached", "YES"),
        ("upfront", "NO"),
        ("abroadJobFee", "NO"),
        ("repaymentDate", "NO"),
        ("familyDiscussed", "YES"),
    ];
    let check = o
        .app
        .mf_check_decision(&o.mf, decision("LEND", "15 000 000", &lend, None))
        .unwrap();
    assert_eq!(check.verdict, "YELLOW");
    assert_eq!(check.share_percent.as_deref(), Some("12,5"));
    assert_eq!(check.wait_until.as_deref(), Some("2027-01-30"));
    let codes: Vec<&str> = check.flags.iter().map(|f| f.code.as_str()).collect();
    assert_eq!(
        codes,
        [
            "FRESH_RETURN_APPROACH",
            "NO_REPAYMENT_DATE",
            "COOLING_BIG_DECISION"
        ]
    );
    assert_eq!(
        err(o
            .app
            .mf_check_decision(&o.mf, decision("LEND", "15 000 000", &lend[..4], None))),
        "MISSING_ANSWER"
    );
    let mut wrong = lend.to_vec();
    wrong.push(("guaranteed", "NO"));
    assert_eq!(
        err(o
            .app
            .mf_check_decision(&o.mf, decision("LEND", "15 000 000", &wrong, None))),
        "INVALID_ANSWER"
    );
    assert_eq!(
        err(o
            .app
            .mf_record_decision(&o.mf, decision("LEND", "15 000 000", &lend, None))),
        "INVALID_CHOICE"
    );
    let log = o
        .app
        .mf_record_decision(&o.mf, decision("LEND", "15 000 000", &lend, Some("WAIT")))
        .unwrap();
    assert_eq!(log.len(), 1);
    assert_eq!(
        (log[0].choice.as_str(), log[0].verdict.as_str()),
        ("WAIT", "YELLOW")
    );
    assert_eq!(log[0].answers.len(), 5);
    assert_eq!(log[0].wait_until.as_deref(), Some("2027-01-30"));
    // Sheriklik: 40 000 000 — olib kelinganning 30 %idan ko'pi → qizil.
    let mut partner = vec![
        ("guaranteed", "NO"),
        ("lossShared", "YES"),
        ("realActivity", "YES"),
        ("recruitment", "NO"),
        ("urgency", "NO"),
        ("written", "YES"),
        ("licensed", "YES"),
        ("inspection", "YES"),
        ("exitEasy", "YES"),
    ];
    partner.extend(lend.iter().filter(|(k, _)| *k != "repaymentDate"));
    let mut big = decision("PARTNERSHIP", "40 000 000", &partner, Some("DECLINE"));
    big.title = "Doʻst bilan doʻkon".into();
    let log = o.app.mf_record_decision(&o.mf, big).unwrap();
    assert_eq!(log.len(), 2);
    assert!(log
        .iter()
        .any(|d| d.verdict == "RED" && d.flags.iter().any(|f| f.code == "LARGE_SHARE")));

    // Musofir → oila: qarorlar, qaytish va reja sozlamalari oilaga bormaydi.
    let res = import(&home, &export(&o.app, &home_dev.id));
    assert_eq!(res.conflicts_local + res.conflicts_remote, 0);
    assert_private(&home_dev, &o.mf);
    assert!(home_dev.rows("mf_decisions").is_empty());
    assert_eq!(home_dev.rows("mf_debt_payments").len(), 1);
    // Jurnal o'zgarmas.
    let db = owner_dev.db();
    let r = db.write(|tx| {
        tx.execute("UPDATE mf_decisions SET choice = 'PROCEED'", [])?;
        Ok(())
    });
    assert!(r.is_err());
    drop(db);

    // Belgini olib tashlash — sovutish davri yo'q.
    let ov = o
        .app
        .mf_set_return(
            &o.mf,
            MfReturnInput {
                returned_on: None,
                brought_home: None,
                brought_currency: None,
                brought_rate: None,
            },
        )
        .unwrap();
    assert!(ov.cooling.is_none());

    // M4: zaxira pul va qaror natijasi ham oilaga bormaydi.
    let mut opening = mv("RESERVE_OPENING", "800 000");
    opening.occurred_on = Some("2026-11-01".into());
    o.app.mf_record_move(&o.mf, opening).unwrap();
    let decision = o.app.mf_decisions(&o.mf).unwrap()[0].id.clone();
    o.app
        .mf_set_outcome(
            &o.mf,
            &decision,
            MfOutcomeInput {
                outcome: "DROPPED".into(),
                outcome_on: None,
                note: None,
            },
        )
        .unwrap();
    import(&home, &export(&o.app, &home_dev.id));
    assert!(home_dev.rows("mf_reserve_moves").is_empty());
    assert!(home_dev.rows("mf_decision_outcomes").is_empty());
    assert_eq!(
        err(home.mf_set_plan(
            &o.mf,
            MfPlanInput {
                reserve_months: Some(2),
                startup: None,
                startup_idea_id: None,
            }
        )),
        "ROLE_FORBIDDEN"
    );
}
