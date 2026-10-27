#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! R6 — 1.1.0 → 1.2.0 bazasini yangilash: 1.1.0 sxemasi (v22, faqat 001–022 migratsiyalari) bilan
//! shifrlangan baza Uy (daromad, xarajat, «Kelajagim», qarz), Kasb-kor (tushum, chiqim, «Hisob kuni» —
//! K9 dan oldingi `v: 1` bayonnoma, o'z mehnatisiz), Musofir (maosh, xarajat) va kelishuv jurnali
//! yozuvlari bilan to'ldiriladi, keyin hozirgi ilova uni ochadi (023–025 qo'llanadi).
//!
//! Ma'lumotlar haqiqiy use-case'lar bilan yoziladi (vaqtinchalik bazada), so'ng **faqat v22 sxemasidagi**
//! jadval va ustunlar bilan haqiqiy v22 bazaga ko'chiriladi; «Hisob kuni» bayonnomasi 1.1.0 yozgan
//! ko'rinishga (`v: 1`, `owner_labor` yo'q, xesh zanjiri qayta hisoblangan) qaytariladi.

use std::collections::BTreeMap;
use std::path::Path;
use std::sync::Arc;

use baraka_app::*;
use baraka_interchange::canon::Row;
use baraka_journal::GENESIS_HASH;
use baraka_storage::Database;
use chrono::{DateTime, Utc};
use serde_json::Value;
use sha2::{Digest, Sha256};

/// 1.1.0 relizining sxema versiyasi (`docs/RELEASE_CHECKLIST.md`): 001–022 migratsiyalari.
const V1_1_SCHEMA: usize = 22;
/// 1.2.0 da qo'shilgan jadvallar (023–025) — yangilangandan keyin bor va bo'sh.
const NEW_TABLES: [&str; 10] = [
    "learning_hour_values",
    "learning_plans",
    "learning_study_logs",
    "teaching_logs",
    "kk_owner_hours",
    "kk_delegations",
    "kk_teaching_logs",
    "mf_hour_values",
    "mf_learning_plans",
    "mf_teaching_logs",
];

fn clock() -> Arc<FixedClock> {
    Arc::new(FixedClock::new(
        DateTime::parse_from_rfc3339("2026-10-15T10:00:00+05:00")
            .unwrap()
            .with_timezone(&Utc),
    ))
}

fn open(path: &Path, key: &DbKey) -> App {
    App::open(path, key, "dev-uy", clock(), Arc::new(UuidV7Gen)).unwrap()
}

struct Spaces {
    uy: String,
    kk: String,
    mf: String,
    agreement: String,
}

fn category(app: &App, space: &str, key: &str) -> String {
    app.categories(space)
        .unwrap()
        .into_iter()
        .find(|c| c.name_key == key)
        .unwrap_or_else(|| panic!("{key}"))
        .id
}

fn expense(category_id: String, amount: &str, on: &str, debt: bool) -> NewExpenseInput {
    NewExpenseInput {
        amount: amount.into(),
        category_id,
        channel: "CASH".into(),
        member_id: None,
        occurred_on: Some(on.into()),
        necessity: None,
        obligation_id: None,
        is_gift: false,
        is_ostentation: false,
        funded_by_debt: debt,
        note: None,
        self_investment: false,
        learning_plan_id: None,
        study_debt: None,
    }
}

/// 1.1.0 da bo'lishi mumkin bo'lgan yozuvlar (hech qanday 8-tamoyil ma'lumoti yo'q).
fn fill(app: &App) -> Spaces {
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Rustamlar oilasi".into(),
            device_name: "Uy kompyuteri".into(),
            platform: "linux".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into(), "KASBKOR".into(), "MUSOFIR".into()],
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
            income_rhythm: Some("MONTHLY".into()),
            debts_declared: true,
        })
        .unwrap();
    let id = |k: &str| h.spaces.iter().find(|s| s.kind == k).unwrap().id.clone();
    let (uy, kk, mf) = (id("UY"), id("KASBKOR"), id("MUSOFIR"));

    // Uy: daromad, xarajatlar (biri qarzga), «Kelajagim», qarz va to'lov.
    for (who, amount, on) in [
        (0, "6 000 000", "2026-09-05"),
        (1, "2 500 000", "2026-09-20"),
        (0, "6 200 000", "2026-10-05"),
    ] {
        app.record_income(
            &uy,
            NewIncomeInput {
                amount: amount.into(),
                source: "Maosh".into(),
                channel: "CARD".into(),
                member_id: Some(h.members[who].id.clone()),
                occurred_on: Some(on.into()),
                source_type: None,
                note: None,
            },
        )
        .unwrap();
    }
    let rent = category(app, &uy, "category.rent");
    app.record_expense(&uy, expense(rent.clone(), "2 000 000", "2026-10-06", false))
        .unwrap();
    app.record_expense(&uy, expense(rent, "350 000", "2026-10-08", true))
        .unwrap();
    app.deposit_to_vault(&uy, "1 240 000", Some("Oktyabr ulushi"))
        .unwrap();
    app.withdraw_from_vault(&uy, "200 000", "Dori").unwrap();
    let debt = app
        .add_debt(
            &uy,
            NewDebtInput {
                creditor_type: "RELATIVE".into(),
                creditor: "Akam".into(),
                reason: Some("Uy taʼmiri".into()),
                currency: "UZS".into(),
                principal: "3 000 000".into(),
                original_principal: None,
                paid_before: None,
                plan_kind: "MANUAL".into(),
                annual_bp: None,
                markup: None,
                months: None,
                first_date: Some("2026-09-01".into()),
                schedule: vec![
                    ScheduleLineInput {
                        date: "2026-10-10".into(),
                        amount: "1 500 000".into(),
                    },
                    ScheduleLineInput {
                        date: "2026-11-10".into(),
                        amount: "1 500 000".into(),
                    },
                ],
                early_repayment_terms: None,
                prepayment_fee_bp: None,
                is_new: false,
                borrow_check: None,
            },
        )
        .unwrap();
    app.record_repayment(
        &uy,
        "DEBT",
        &debt.id,
        RepaymentInput {
            amount: "1 500 000".into(),
            date: Some("2026-10-10".into()),
            is_prepayment: false,
            note: None,
            contributor_id: None,
        },
    )
    .unwrap();

    // Kelishuv jurnali (hash zanjiri).
    let agreement = app
        .create_agreement(&uy, "PARTNERSHIP", "Qoʻshni bilan issiqxona")
        .unwrap()
        .id;
    for (kind, amount, note) in [
        ("CONTRIBUTION", "4 000 000", "Rustam hissasi"),
        ("REVENUE", "1 100 000", "Pomidor sotildi"),
    ] {
        app.append_journal(
            &uy,
            &agreement,
            NewJournalEntryInput {
                kind: kind.into(),
                party_id: Some("P1".into()),
                amount: Some(amount.into()),
                currency: None,
                date: Some("2026-10-01".into()),
                note: Some(note.into()),
                corrects_entry_id: None,
                refs: vec![],
            },
        )
        .unwrap();
    }

    // Kasb-kor: sentyabr tushumi va chiqimi, o'z mehnati bahosi va yopilgan oy.
    app.kk_set_owner_labor(&kk, "3 000 000".into()).unwrap();
    for (amount, on) in [("7 000 000", "2026-09-10"), ("4 000 000", "2026-09-24")] {
        app.kk_record_sale(
            &kk,
            KkSaleInput {
                amount: amount.into(),
                channel: "CASH".into(),
                occurred_on: Some(on.into()),
                note: None,
            },
        )
        .unwrap();
    }
    let kk_cat = app.categories(&kk).unwrap()[0].id.clone();
    app.record_expense(&kk, expense(kk_cat, "2 500 000", "2026-09-15", false))
        .unwrap();
    app.kk_close_month(
        &kk,
        KkCloseInput {
            period_start: "2026-09-01".into(),
            carry_overdraw: false,
            explanation: None,
        },
    )
    .unwrap();

    // Musofir: sozlama, maosh, chet eldagi xarajat.
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
    for (amount, on) in [("2 600 000", "2026-09-10"), ("2 700 000", "2026-10-10")] {
        app.mf_record_income(
            &mf,
            MfIncomeInput {
                kind: "SALARY".into(),
                amount: amount.into(),
                channel: "CARD".into(),
                occurred_on: Some(on.into()),
                note: None,
            },
        )
        .unwrap();
    }
    let mf_cat = app.categories(&mf).unwrap()[0].id.clone();
    app.mf_record_expense(
        &mf,
        MfExpenseInput {
            amount: "420 000".into(),
            category_id: mf_cat,
            channel: "CARD".into(),
            occurred_on: Some("2026-10-12".into()),
            note: Some("Yotoqxona".into()),
            self_investment: false,
        },
    )
    .unwrap();
    Spaces {
        uy,
        kk,
        mf,
        agreement,
    }
}

/// 1.1.0 bayonnomasi: JSON o'qiladi, `owner_labor` olib tashlanadi, `v: 1`; xesh zanjiri qayta —
/// `sha256(oldingi xesh \n matn)`.
fn to_v1_close(row: &mut Row, prev: &mut String) {
    let mut record: serde_json::Map<String, Value> =
        serde_json::from_str(row["result_json"].as_str().unwrap()).unwrap();
    assert_eq!(record.get("v"), Some(&Value::from(2)), "v2 bayonnoma");
    assert!(record.remove("owner_labor").is_some(), "owner_labor");
    record.insert("v".into(), Value::from(1));
    let v1 = serde_json::to_string(&record).unwrap();
    let mut h = Sha256::new();
    h.update(prev.as_bytes());
    h.update(b"\n");
    h.update(v1.as_bytes());
    let hash: String = h.finalize().iter().map(|b| format!("{b:02x}")).collect();
    row.insert("prev_hash".into(), Value::String(prev.clone()));
    row.insert("content_hash".into(), Value::String(hash.clone()));
    row.insert("result_json".into(), Value::String(v1));
    *prev = hash;
}

/// Jadval → ustunlar (shu bazaning sxemasi bo'yicha).
fn schema(db: &Database) -> BTreeMap<String, Vec<String>> {
    db.read(|c| {
        let mut st = c.prepare(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'",
        )?;
        let names: Vec<String> = st.query_map([], |r| r.get(0))?.collect::<Result<_, _>>()?;
        let mut out = BTreeMap::new();
        for t in names {
            let mut st = c.prepare(&format!("PRAGMA table_info(\"{t}\")"))?;
            let cols = st
                .query_map([], |r| r.get::<_, String>(1))?
                .collect::<Result<Vec<_>, _>>()?;
            out.insert(t, cols);
        }
        Ok(out)
    })
    .unwrap()
}

/// `cols` ustunlaridagi barcha qiymatlar (qo'shilish tartibida) — eski yozuvlar o'zgarmaganini
/// tekshirish uchun.
fn snapshot(db: &Database, cols: &BTreeMap<String, Vec<String>>) -> BTreeMap<String, Vec<String>> {
    db.read(|c| {
        let mut out = BTreeMap::new();
        for (t, cs) in cols {
            let mut st = c.prepare(&format!(
                "SELECT {} FROM \"{t}\" ORDER BY rowid",
                cs.join(", ")
            ))?;
            let mut rows = st.query([])?;
            let mut all = Vec::new();
            while let Some(r) = rows.next()? {
                let vals: Vec<String> = (0..cs.len())
                    .map(|i| r.get_ref(i).map(|v| format!("{v:?}")))
                    .collect::<Result<_, _>>()?;
                all.push(vals.join(" | "));
            }
            out.insert(t.clone(), all);
        }
        Ok(out)
    })
    .unwrap()
}

fn count(db: &Database, sql: &str) -> i64 {
    db.read(|c| Ok(c.query_row(sql, [], |r| r.get(0))?))
        .unwrap()
}

#[test]
fn database_from_1_1_0_upgrades_with_all_rows_intact() {
    let dir = tempfile::tempdir().unwrap();
    let key = DbKey::from_bytes([11; 32]);
    let (src_path, old_path) = (dir.path().join("src.db"), dir.path().join("baraka.db"));

    // 1) Ma'lumotlar haqiqiy use-case'lar bilan; natijalar keyin solishtiriladi.
    let app = open(&src_path, &key);
    let s = fill(&app);
    let summary = app.monthly_summary(&s.uy, None, None).unwrap();
    let vault = app.vault(&s.uy).unwrap();
    let debts = app.debts_overview(&s.uy).unwrap();
    let chain = app.verify_journal(&s.uy, &s.agreement).unwrap();
    assert!(chain.ok && chain.entries == 2);
    let kk_overview = app.kk_overview(&s.kk, Some("2026-09-15".into())).unwrap();
    let closes = app.kk_month_closes(&s.kk).unwrap();
    assert_eq!(closes.len(), 1);
    let mf_overview = app.mf_overview(&s.mf, None).unwrap();
    drop(app);

    // 2) Haqiqiy 1.1.0 sxemasi (v22) — faqat shu sxemadagi jadval va ustunlar ko'chiriladi.
    let old = Database::create_at_version(&old_path, &key, V1_1_SCHEMA).unwrap();
    assert_eq!(old.schema_version().unwrap(), 22);
    let mut prev = GENESIS_HASH.to_string();
    let copied = old
        .copy_rows_from(&Database::open(&src_path, &key).unwrap(), |t, row| {
            if t == "kk_month_closes" {
                to_v1_close(row, &mut prev);
            }
        })
        .unwrap();
    assert!(copied > 50, "{copied}");
    let v22 = schema(&old);
    for t in NEW_TABLES {
        assert!(!v22.contains_key(t), "{t} 1.1.0 sxemasida yo'q");
    }
    assert!(!v22["expenses"].contains(&"self_investment".to_string()));
    let before = snapshot(&old, &v22);
    for t in [
        "incomes",
        "expenses",
        "vault_transactions",
        "debts",
        "journal_entries",
        "kk_month_closes",
    ] {
        assert!(
            before.get(t).is_some_and(|r| !r.is_empty()),
            "{t}: namunaviy 1.1.0 yozuvi bo'lishi kerak"
        );
    }
    drop(old);

    // 3) Hozirgi ilova ochadi: 023–025 qo'llanadi.
    drop(open(&old_path, &key));
    let db = Database::open(&old_path, &key).unwrap();
    let latest = Database::open_in_memory(&key)
        .unwrap()
        .schema_version()
        .unwrap();
    assert_eq!(db.schema_version().unwrap(), latest);
    assert_eq!(latest, 25);
    // Eski jadvallardagi har bir yozuv va qiymat — o'zgarmagan (soni ham).
    assert_eq!(snapshot(&db, &v22), before);
    // Yangi jadvallar bor va bo'sh; xarajatdagi yangi ustunlar — 0 / NULL.
    let now = schema(&db);
    for t in NEW_TABLES {
        assert!(now.contains_key(t), "{t}");
        assert_eq!(count(&db, &format!("SELECT count(*) FROM {t}")), 0, "{t}");
    }
    assert_eq!(
        count(&db, "SELECT count(*) FROM expenses"),
        i64::try_from(before["expenses"].len()).unwrap()
    );
    assert_eq!(
        count(
            &db,
            "SELECT count(*) FROM expenses WHERE self_investment <> 0 OR learning_plan_id IS NOT NULL"
        ),
        0
    );
    // v1 bayonnoma matni aynan saqlangan.
    assert_eq!(
        count(
            &db,
            "SELECT count(*) FROM kk_month_closes WHERE json_extract(result_json, '$.v') = 1
             AND json_type(result_json, '$.owner_labor') IS NULL"
        ),
        1
    );
    drop(db);

    // 4) Use-case'lar yangilangan bazada: natijalar 1.1.0 ma'lumotidagidek.
    let app = open(&old_path, &key);
    assert_eq!(app.monthly_summary(&s.uy, None, None).unwrap(), summary);
    assert_eq!(app.vault(&s.uy).unwrap(), vault);
    assert_eq!(app.debts_overview(&s.uy).unwrap(), debts);
    let chain2 = app.verify_journal(&s.uy, &s.agreement).unwrap();
    assert_eq!(chain2, chain);
    assert_eq!(
        app.kk_overview(&s.kk, Some("2026-09-15".into())).unwrap(),
        kk_overview
    );
    assert_eq!(app.mf_overview(&s.mf, None).unwrap(), mf_overview);
    // «Hisob kuni» tarixi: v1 bayonnoma o'qiladi, raqamlari o'zgarmagan (xesh — yangi zanjirdan).
    let after = app.kk_month_closes(&s.kk).unwrap();
    assert_eq!(after.len(), 1);
    assert_eq!(after[0].summary, closes[0].summary);
    assert_ne!(after[0].short_code, closes[0].short_code);
    // 8-tamoyil ekranlari bo'sh holatda ishlaydi.
    let l = app.learning_overview(&s.uy, None).unwrap();
    assert_eq!(l.members.len(), 2);
    assert!(l.plans.is_empty() && l.teaching.is_empty());
    assert!(l.members.iter().all(|m| m.hour_value.is_none()));
    assert_eq!(l.self_investment.total.minor, "0");
    let kl = app.kk_learning_overview(&s.kk, None).unwrap();
    assert!(kl.hour_value.is_none() && kl.teaching.is_empty());
    let ml = app.mf_learning_overview(&s.mf, None).unwrap();
    assert!(ml.plans.is_empty());
    // v1 bayonnomada o'z mehnati yo'q — taklif hozirgi sozlamadan (kasbkor/SPEC 8A.4).
    let first = app.kk_owner_hour_suggest(&s.kk).unwrap();
    assert_eq!(first.months.len(), 1);
    assert_eq!(first.months[0].owner_labor.minor, "300000000");
    app.kk_set_owner_labor(&s.kk, "2 000 000".into()).unwrap();
    let changed = app.kk_owner_hour_suggest(&s.kk).unwrap();
    assert_eq!(changed.months[0].owner_labor.minor, "200000000");
    assert_eq!(changed.months[0].true_profit, first.months[0].true_profit);
    // Yangi yozuvlar ham ishlaydi.
    app.hour_value_save(
        &s.uy,
        HourValueInput {
            member_id: l.members[0].member_id.clone(),
            income: None,
            minutes_per_day: 480,
            days: 22,
        },
    )
    .unwrap();
}
