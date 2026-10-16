#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! U14: `.baraka` — telefon ↔ desktop. Ulash fayli orqali yangi qurilma (round-trip 1:1),
//! inkremental sinxronlash (bir tomonda o'zgargan — avtomatik, ikkala tomonda — ziddiyat,
//! LWW yo'q), noto'g'ri parol / boshqa xonadon / o'z fayli, jurnal: telefondan kelgan xeshlar
//! desktopda qayta hisoblanadi, buzilgan zanjir va ayrilish (fork) importni to'xtatadi,
//! yopilgan yozuvni import orqali o'zgartirib bo'lmaydi.

use std::path::{Path, PathBuf};
use std::sync::Arc;

use baraka_agreements::{Answer, Arbiter, Custody, Duty, ExitClause, Stroke, Term};
use baraka_app::*;
use baraka_interchange::container::{open, seal, Kdf};
use baraka_interchange::model::{decode, encode};
use baraka_interchange::tables::sync_tables;
use baraka_journal::{EntryKind, JournalAmount, JournalEntry};
use baraka_storage::repo::{journal, sync};
use baraka_storage::{Database, Meta, SpaceScope};
use chrono::{DateTime, Utc};
use serde_json::json;

const PASSWORD: &str = "Baraka-2026!";

fn at(ts: &str) -> DateTime<Utc> {
    DateTime::parse_from_rfc3339(ts)
        .unwrap()
        .with_timezone(&Utc)
}

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
            clock: Arc::new(FixedClock::new(at("2026-12-02T09:00:00+05:00"))),
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
}

fn bootstrap(app: &App) -> (String, Vec<MemberDto>) {
    let member = |n: &str, r: &str| NewMemberInput {
        display_name: n.into(),
        role: r.into(),
    };
    let h = app
        .bootstrap(BootstrapInput {
            income_rhythm: None,
            debts_declared: false,
            household_name: "Nilufarning oilasi".into(),
            device_name: "Kompyuter".into(),
            platform: "linux".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into()],
            members: vec![member("Nilufar", "ADULT"), member("Rustam", "ADULT")],
        })
        .unwrap();
    (h.spaces[0].id.clone(), h.members)
}

fn income(app: &App, uy: &str, amount: &str, source: &str) {
    app.record_income(
        uy,
        NewIncomeInput {
            amount: amount.into(),
            source: source.into(),
            channel: "CARD".into(),
            member_id: None,
            occurred_on: Some("2026-12-01".into()),
            source_type: None,
            note: None,
        },
    )
    .unwrap();
}

fn full(app: &App) -> ExportFileDto {
    app.export_baraka(ExportInput {
        password: PASSWORD.into(),
        mode: "FULL".into(),
        peer_device_id: None,
    })
    .unwrap()
}

fn incremental(app: &App, peer: &str) -> ExportFileDto {
    app.export_baraka(ExportInput {
        password: PASSWORD.into(),
        mode: "INCREMENTAL".into(),
        peer_device_id: Some(peer.into()),
    })
    .unwrap()
}

/// Ulash: desktop kod va fayl beradi, telefon shu bilan xonadonga qo'shiladi.
fn pair(desktop: &App, phone_dev: &Device) -> App {
    let offer = desktop.pairing_offer().unwrap();
    let phone = phone_dev.app();
    phone
        .join_household(
            &offer.bytes,
            JoinInput {
                // QR'siz, qo'lda: kichik harf va bo'shliqlar bilan ham ishlaydi.
                secret: offer.code.to_lowercase().replace('-', " "),
                device_name: "Nilufarning telefoni".into(),
                platform: "android".into(),
            },
        )
        .unwrap();
    phone
}

fn scenarios() -> Vec<IdeaScenarioInput> {
    ["PESSIMISTIC", "BASE", "OPTIMISTIC"]
        .iter()
        .zip(["4 000 000", "6 000 000", "8 000 000"])
        .map(|(n, inc)| IdeaScenarioInput {
            name: (*n).into(),
            income: inc.into(),
            expense: "3 000 000".into(),
        })
        .collect()
}

/// Ulangandan keyin telefon birinchi faylini yuboradi: desktop uni shundan keyin taniydi.
fn introduce(phone: &App, desktop: &App, desktop_id: &str) {
    let f = incremental(phone, desktop_id);
    desktop
        .apply_baraka(&f.bytes, PASSWORD, Vec::new())
        .unwrap();
}

fn category_id(app: &App, uy: &str) -> String {
    app.categories(uy).unwrap()[0].id.clone()
}

fn answered<T>(value: T) -> Answer<T> {
    Answer::Answered { value }
}

fn capital(kind: &str, description: &str, amount: &str) -> CapitalItemInput {
    CapitalItemInput {
        kind: kind.into(),
        description: description.into(),
        amount: amount.into(),
    }
}

/// Sobir hoji tikuv uskunasi va mato puli beradi, Nilufar (shu oila) tikadi — mudoraba 50/50.
fn mudaraba(me_is_worker: bool) -> PartnershipInput {
    PartnershipInput {
        kind: "MUDARABA".into(),
        title: "Tikuvchilik ustaxonasi".into(),
        parties: vec![
            PartnerInput {
                id: "P1".into(),
                full_name: "Sobir Qodirov".into(),
                role: "CAPITAL_PROVIDER".into(),
                profit_share_bp: 5000,
                is_me: !me_is_worker,
                capital: vec![
                    capital("EQUIPMENT", "Tikuv mashinasi (2 ta)", "24 000 000"),
                    capital("MONEY", "Mato uchun", "6 000 000"),
                ],
            },
            PartnerInput {
                id: "P2".into(),
                full_name: "Nilufar Karimova".into(),
                role: "WORKER".into(),
                profit_share_bp: 5000,
                is_me: me_is_worker,
                capital: vec![],
            },
        ],
        fixed_return: None,
        duties: answered(vec![Duty {
            id: String::new(),
            title: "Buyurtmalarni tikish va topshirish".into(),
            owner_party_id: Some("P2".into()),
            breach_clause: Some("1 kun ichida xabar beradi va oʻrniga yechim topadi".into()),
        }]),
        negligence_clause: Some("Uskunani boshqa ishga berish".into()),
        custody: answered(Custody {
            location: "Alohida karta".into(),
            keeper_party_id: "P2".into(),
            review_every_days: 30,
            keeper_device_id: None,
        }),
        exit_clause: answered(ExitClause {
            notice_days: 30,
            valuation_method: "Bozor narxi, ikki tomon kelishuvi bilan".into(),
            payout_terms: "3 oy ichida".into(),
            asset_split: None,
        }),
        arbiter: answered(Arbiter {
            full_name: "Mahalla oqsoqoli Hamid aka".into(),
            role: Some("qoʻshni".into()),
            party_id: None,
        }),
        term: answered(Term {
            effective_from: "01.11.2026".into(),
            duration_months: Some(12),
            review_date: "01.11.2027".into(),
        }),
        witnesses: vec!["Dilnoza opa".into()],
        buyout: Some(BuyoutTermsInput {
            seller_party_id: "P1".into(),
            buyer_party_id: "P2".into(),
            units: 10,
            units_per_period: 1,
            period_months: 1,
            start: "30.11.2026".into(),
            expected_profit: Some("8 000 000".into()),
        }),
    }
}

fn sig() -> Vec<Stroke> {
    vec![Stroke(vec![[100, 300], [300, 120], [500, 280], [700, 100]])]
}

fn sign_all(app: &App, uy: &str, p: &PartnershipDto) -> PartnershipDto {
    let mut last = p.clone();
    for s in &p.signers {
        last = app
            .sign_partnership(
                uy,
                &p.id,
                SignInput {
                    signer_key: s.key.clone(),
                    strokes: sig(),
                },
            )
            .unwrap();
    }
    last
}

/// Nilufar (shu oila) — mehnat egasi va hisob yurituvchi; shartnoma imzolanib, faollashtirilgan.
fn active(app: &App, uy: &str, members: &[MemberDto], input: PartnershipInput) -> PartnershipDto {
    let p = app.create_partnership(uy, input).unwrap();
    let p = sign_all(app, uy, &p);
    app.acknowledge_not_debt(uy, &p.id).unwrap();
    for m in members {
        app.consent_partnership(uy, &p.id, &m.id).unwrap();
    }
    app.activate_partnership(uy, &p.id).unwrap()
}

fn entry(
    kind: &str,
    cat: Option<&str>,
    amount: &str,
    on: &str,
    note: Option<&str>,
) -> VentureEntryInput {
    VentureEntryInput {
        kind: kind.into(),
        category: cat.map(Into::into),
        amount: amount.into(),
        occurred_on: on.into(),
        note: note.map(Into::into),
        corrects_entry_id: None,
        attachments: Vec::new(),
    }
}

fn png() -> Vec<u8> {
    let mut b = vec![0x89, b'P', b'N', b'G', 0x0D, 0x0A, 0x1A, 0x0A];
    b.extend_from_slice(b"chek-rasmi");
    b
}

fn close(end: &str) -> ClosePeriodInput {
    ClosePeriodInput {
        end_on: end.into(),
        negligence: None,
        buyout_prices: Vec::new(),
        channel: "CARD".into(),
    }
}

/// Desktop: xonadon, daromad, sheriklik (jurnal), kassa daftari (chek bilan), yopilgan davr.
fn rich_desktop(dir: &Path) -> (Device, App, String, PartnershipDto) {
    let dev = Device::new(dir, "desktop", 1);
    let app = dev.app();
    let (uy, members) = bootstrap(&app);
    income(&app, &uy, "8 000 000", "Taksi");
    let p = active(&app, &uy, &members, mudaraba(true));
    let mut order = entry(
        "INCOME",
        Some("ORDER"),
        "12 000 000",
        "05.11.2026",
        Some("Toʻy koʻylaklari"),
    );
    order.attachments.push(AttachmentInput {
        file_name: "chek.png".into(),
        bytes: png(),
    });
    app.add_venture_entry(&uy, &p.id, order).unwrap();
    app.add_venture_entry(
        &uy,
        &p.id,
        entry(
            "EXPENSE",
            Some("MATERIAL"),
            "5 000 000",
            "09.11.2026",
            Some("Mato"),
        ),
    )
    .unwrap();
    app.close_venture_period(&uy, &p.id, close("30.11.2026"))
        .unwrap();
    (dev, app, uy, p)
}

fn dumps(
    db: &Database,
    household: &str,
) -> Vec<(String, Vec<serde_json::Map<String, serde_json::Value>>)> {
    sync_tables()
        .iter()
        .map(|t| {
            (
                t.name.clone(),
                db.read(|c| sync::dump(c, household, &t.name)).unwrap(),
            )
        })
        .collect()
}

#[test]
fn pairing_round_trip_is_one_to_one() {
    let dir = tempfile::tempdir().unwrap();
    let (desktop_dev, desktop, uy, p) = rich_desktop(dir.path());
    let household = desktop.household().unwrap().id;
    let offer = desktop.pairing_offer().unwrap();
    assert!(offer.qr_svg.contains("<svg"));
    assert_eq!(offer.code.len(), 39);

    // Noto'g'ri kod — aniq xato, baza yaratilmaydi.
    let stranger = Device::new(dir.path(), "stranger", 9).app();
    let bad = stranger
        .join_household(
            &offer.bytes,
            JoinInput {
                secret: "AAAA-BBBB-CCCC-DDDD-EEEE-FFFF-GGGG-HHHH".into(),
                device_name: "Begona".into(),
                platform: "android".into(),
            },
        )
        .unwrap_err();
    assert_eq!(bad.code, "INTERCHANGE_BAD_PASSWORD");
    assert!(!stranger.is_initialized().unwrap());

    let phone_dev = Device::new(dir.path(), "phone", 2);
    let phone = pair(&desktop, &phone_dev);
    assert_eq!(phone.household().unwrap().id, household);
    // Telefondagi jurnal xeshlari qayta hisoblanganda mos.
    let chain = phone.verify_journal(&uy, &p.agreement_id).unwrap();
    assert!(chain.ok);
    assert_eq!(
        chain.head,
        desktop.verify_journal(&uy, &p.agreement_id).unwrap().head
    );
    let l = phone.venture_ledger(&uy, &p.id).unwrap();
    assert_eq!(l.periods.len(), 1);
    assert_eq!(l.read_only_reason.as_deref(), Some("NOT_KEEPER"));
    let att = &l
        .entries
        .iter()
        .find(|e| !e.attachments.is_empty())
        .unwrap()
        .attachments[0];
    assert_eq!(
        phone.venture_attachment(&uy, &p.id, &att.id).unwrap().bytes,
        png()
    );
    let devices = phone.devices().unwrap();
    assert_eq!(devices.len(), 2);
    assert!(devices
        .iter()
        .any(|d| d.is_this && d.name == "Nilufarning telefoni"));

    // 1:1 — barcha jadvallar aynan bir xil (faqat telefonning o'z qurilma yozuvi qo'shimcha).
    drop((desktop, phone, stranger));
    let (a, b) = (
        dumps(&desktop_dev.db(), &household),
        dumps(&phone_dev.db(), &household),
    );
    for ((t, ra), (_, rb)) in a.iter().zip(&b) {
        if t == "devices" {
            assert_eq!(rb.len(), ra.len() + 1);
            assert!(ra.iter().all(|r| rb.contains(r)));
        } else {
            assert_eq!(ra, rb, "{t}");
        }
    }
    assert!(a.iter().map(|(_, r)| r.len()).sum::<usize>() > 40);
}

#[test]
fn incremental_sync_merges_one_sided_changes_and_asks_on_conflicts() {
    let dir = tempfile::tempdir().unwrap();
    let desktop_dev = Device::new(dir.path(), "desktop", 1);
    let desktop = desktop_dev.app();
    let (uy, _) = bootstrap(&desktop);
    let phone_dev = Device::new(dir.path(), "phone", 2);
    let phone = pair(&desktop, &phone_dev);
    let cat = category_id(&desktop, &uy);

    // Telefonda daromad — desktopga avtomatik qo'shiladi.
    income(&phone, &uy, "1 500 000", "Bozor");
    let f = incremental(&phone, &desktop_dev.id);
    let pv = desktop.inspect_baraka(&f.bytes, PASSWORD).unwrap();
    assert!(pv.can_apply && pv.conflicts.is_empty() && pv.forks.is_empty());
    assert_eq!(pv.source_device_name, "Nilufarning telefoni");
    assert_eq!(pv.inserts, 2, "daromad va telefon qurilmasi");
    assert_eq!(pv.updates, 0);
    let r = desktop
        .apply_baraka(&f.bytes, PASSWORD, Vec::new())
        .unwrap();
    assert_eq!(r.inserted, 2);
    // Qayta import — hech narsa o'zgarmaydi.
    let again = desktop.inspect_baraka(&f.bytes, PASSWORD).unwrap();
    assert_eq!(
        (again.inserts, again.updates, again.conflicts.len()),
        (0, 0, 0)
    );

    // Desktopda kategoriya nomi o'zgardi — telefonga faqat shu yozuv boradi.
    desktop.rename_category(&uy, &cat, "Bozorlik").unwrap();
    let f = incremental(&desktop, &phone_dev.id);
    assert_eq!(f.rows, 1);
    let pv = phone.inspect_baraka(&f.bytes, PASSWORD).unwrap();
    assert_eq!((pv.updates, pv.inserts, pv.conflicts.len()), (1, 0, 0));
    phone.apply_baraka(&f.bytes, PASSWORD, Vec::new()).unwrap();
    assert!(phone
        .categories(&uy)
        .unwrap()
        .iter()
        .any(|c| c.id == cat && c.custom_name.as_deref() == Some("Bozorlik")));

    // Ikkala tomonda bir yozuv o'zgardi — ziddiyat, foydalanuvchi tanlaydi (LWW yo'q).
    desktop
        .rename_category(&uy, &cat, "Oziq-ovqat (D)")
        .unwrap();
    phone.rename_category(&uy, &cat, "Oziq-ovqat (T)").unwrap();
    let f = incremental(&phone, &desktop_dev.id);
    let pv = desktop.inspect_baraka(&f.bytes, PASSWORD).unwrap();
    assert_eq!(pv.conflicts.len(), 1);
    let c = &pv.conflicts[0];
    assert_eq!(c.key, format!("categories:{cat}"));
    let name = c.fields.iter().find(|x| x.field == "custom_name").unwrap();
    assert_eq!(
        (name.local.as_str(), name.remote.as_str()),
        ("Oziq-ovqat (D)", "Oziq-ovqat (T)")
    );
    assert!(c.fields.iter().all(|x| x.field != "version"));
    assert_eq!(
        desktop
            .apply_baraka(&f.bytes, PASSWORD, Vec::new())
            .unwrap_err()
            .code,
        "CONFLICTS_UNRESOLVED"
    );
    let r = desktop
        .apply_baraka(
            &f.bytes,
            PASSWORD,
            vec![ConflictChoiceInput {
                key: c.key.clone(),
                choice: "LOCAL".into(),
            }],
        )
        .unwrap();
    assert_eq!(r.conflicts_local, 1);
    // Desktop tanlovi telefonga qaytadi — u yerda ziddiyat emas, oddiy yangilanish.
    let f = incremental(&desktop, &phone_dev.id);
    let pv = phone.inspect_baraka(&f.bytes, PASSWORD).unwrap();
    assert_eq!((pv.updates, pv.conflicts.len()), (1, 0));
    phone.apply_baraka(&f.bytes, PASSWORD, Vec::new()).unwrap();
    assert!(phone
        .categories(&uy)
        .unwrap()
        .iter()
        .any(|c| c.id == cat && c.custom_name.as_deref() == Some("Oziq-ovqat (D)")));
    // Endi ikkala tomon kelishgan: telefonning inkremental fayli bo'sh.
    assert_eq!(incremental(&phone, &desktop_dev.id).rows, 0);

    // Pul maydoni: ikkala tomonda summa o'zgargan g'oya — ziddiyat, summalar formatlangan.
    let idea = desktop
        .create_venture_idea(
            &uy,
            VentureIdeaInput {
                title: "Uyda tikuv".into(),
                skill_id: None,
                capex: vec![CapexLineInput {
                    title: "Overlok".into(),
                    amount: "5 000 000".into(),
                }],
                scenarios: scenarios(),
                worker_share_bp: None,
            },
        )
        .unwrap();
    let f = incremental(&desktop, &phone_dev.id);
    phone.apply_baraka(&f.bytes, PASSWORD, Vec::new()).unwrap();
    // O'chirish va tahrir: desktop o'chirdi, telefon tahrirladi.
    desktop.delete_venture_idea(&uy, &idea.id).unwrap();
    let mut edit = VentureIdeaInput {
        title: "Uyda tikuv (2 ta mashina)".into(),
        skill_id: None,
        capex: vec![CapexLineInput {
            title: "Overlok".into(),
            amount: "9 000 000".into(),
        }],
        scenarios: scenarios(),
        worker_share_bp: None,
    };
    edit.title.push('!');
    phone.update_venture_idea(&uy, &idea.id, edit).unwrap();
    let f = incremental(&desktop, &phone_dev.id);
    let pv = phone.inspect_baraka(&f.bytes, PASSWORD).unwrap();
    assert_eq!(pv.conflicts.len(), 1);
    assert!(pv.conflicts[0].remote_deleted && !pv.conflicts[0].local_deleted);
    let r = phone
        .apply_baraka(
            &f.bytes,
            PASSWORD,
            vec![ConflictChoiceInput {
                key: pv.conflicts[0].key.clone(),
                choice: "REMOTE".into(),
            }],
        )
        .unwrap();
    assert_eq!(r.conflicts_remote, 1);
    assert!(phone.venture_ideas(&uy).unwrap().is_empty());
}

#[test]
fn bad_password_other_household_and_own_file_are_rejected() {
    let dir = tempfile::tempdir().unwrap();
    let a_dev = Device::new(dir.path(), "a", 1);
    let a = a_dev.app();
    bootstrap(&a);
    let b = Device::new(dir.path(), "b", 2).app();
    bootstrap(&b);
    let fa = full(&a);
    assert_eq!(
        a.inspect_baraka(&fa.bytes, PASSWORD).unwrap_err().code,
        "INTERCHANGE_OWN_FILE"
    );
    assert_eq!(
        b.inspect_baraka(&fa.bytes, "Baraka-2025!")
            .unwrap_err()
            .code,
        "INTERCHANGE_BAD_PASSWORD"
    );
    assert_eq!(
        b.inspect_baraka(&fa.bytes, PASSWORD).unwrap_err().code,
        "INTERCHANGE_WRONG_HOUSEHOLD"
    );
    assert_eq!(
        b.inspect_baraka(b"hello", PASSWORD).unwrap_err().code,
        "INTERCHANGE_NOT_BARAKA"
    );
    let weak = a.export_baraka(ExportInput {
        password: "1234".into(),
        mode: "FULL".into(),
        peer_device_id: None,
    });
    assert_eq!(weak.unwrap_err().code, "INTERCHANGE_WEAK_PASSWORD");
    let no_peer = a.export_baraka(ExportInput {
        password: PASSWORD.into(),
        mode: "INCREMENTAL".into(),
        peer_device_id: None,
    });
    assert_eq!(no_peer.unwrap_err().code, "REQUIRED");
    // Zaxira nusxadan tiklash: to'liq fayl + parol (yangi qurilma).
    let restored = Device::new(dir.path(), "restored", 3).app();
    restored
        .join_household(
            &fa.bytes,
            JoinInput {
                secret: PASSWORD.into(),
                device_name: "Yangi noutbuk".into(),
                platform: "windows".into(),
            },
        )
        .unwrap();
    assert_eq!(restored.household().unwrap().id, a.household().unwrap().id);
}

/// Faylni ochib, tarkibini o'zgartirib, xuddi shu parol bilan qayta shifrlash («buzg'unchi»).
fn rewrite(bytes: &[u8], f: impl Fn(&mut Vec<baraka_interchange::model::RowRecord>)) -> Vec<u8> {
    let (_, plain) = open(bytes, PASSWORD).unwrap();
    let (meta, mut rows) = decode(&plain).unwrap();
    f(&mut rows);
    seal(
        &encode(&meta, &rows).unwrap(),
        PASSWORD,
        Kdf::INSECURE_FAST_FOR_TESTS,
    )
    .unwrap()
}

#[test]
fn journal_tampering_and_forks_stop_import_closed_records_are_protected() {
    let dir = tempfile::tempdir().unwrap();
    let (desktop_dev, desktop, uy, p) = rich_desktop(dir.path());
    let phone_dev = Device::new(dir.path(), "phone", 2);
    let phone = pair(&desktop, &phone_dev);
    let household = desktop.household().unwrap().id;
    // Telefon hali ro'yxatda yo'q: avval o'z faylini yuborishi kerak.
    let unknown = desktop.export_baraka(ExportInput {
        password: PASSWORD.into(),
        mode: "INCREMENTAL".into(),
        peer_device_id: Some(phone_dev.id.clone()),
    });
    assert_eq!(unknown.unwrap_err().code, "UNKNOWN_DEVICE");
    introduce(&phone, &desktop, &desktop_dev.id);

    // Desktop (hisob yurituvchi) yangi yozuv qo'shdi — telefonga jurnal davomi sifatida boradi.
    desktop
        .add_venture_entry(
            &uy,
            &p.id,
            entry("INCOME", Some("ORDER"), "3 000 000", "01.12.2026", None),
        )
        .unwrap();
    let f = incremental(&desktop, &phone_dev.id);
    let pv = phone.inspect_baraka(&f.bytes, PASSWORD).unwrap();
    assert!(pv.can_apply);
    assert_eq!(pv.journal_appended, 1);

    // Fayldagi jurnal summasi o'zgartirilgan, xesh eski — import to'xtaydi.
    let forged = rewrite(&f.bytes, |rows| {
        let last = rows
            .iter_mut()
            .rev()
            .find(|r| r.table == "journal_entries")
            .unwrap();
        last.data.insert("amount_minor".into(), json!(900_000_000));
    });
    let pv = phone.inspect_baraka(&forged, PASSWORD).unwrap();
    assert!(!pv.can_apply);
    assert_eq!(pv.forks[0].reason, "TAMPERED");
    assert_eq!(pv.forks[0].title, "Tikuvchilik ustaxonasi");
    assert_eq!(
        phone
            .apply_baraka(&forged, PASSWORD, Vec::new())
            .unwrap_err()
            .code,
        "INTERCHANGE_FORK"
    );

    // Yopilgan davr natijasi fayl ichida o'zgartirilgan — rad etiladi, qolgani qo'llanadi.
    let full_file = full(&desktop);
    let changed = rewrite(&full_file.bytes, |rows| {
        let period = rows
            .iter_mut()
            .find(|r| r.table == "venture_periods")
            .unwrap();
        period.data.insert("result_minor".into(), json!(1));
    });
    let pv = phone.inspect_baraka(&changed, PASSWORD).unwrap();
    assert_eq!(pv.protected.len(), 1);
    assert_eq!(pv.protected[0].table, "venture_periods");
    let r = phone.apply_baraka(&changed, PASSWORD, Vec::new()).unwrap();
    assert_eq!((r.protected, r.journal_appended), (1, 1));
    let period = phone.venture_ledger(&uy, &p.id).unwrap().periods[0].clone();
    assert_eq!(period.result.minor, "700000000");
    assert!(phone.verify_journal(&uy, &p.agreement_id).unwrap().ok);

    // Telefonda (hisob yurituvchi emas) jurnalga yozuv paydo bo'ldi — ayrilish.
    drop(phone);
    let scope = SpaceScope {
        household_id: household.clone(),
        space_id: uy.clone(),
    };
    phone_dev
        .db()
        .write(|tx| {
            let e = JournalEntry {
                id: "rogue-1".into(),
                agreement_id: p.agreement_id.clone(),
                kind: EntryKind::Revenue,
                party_id: None,
                amount: Some(JournalAmount {
                    minor: 100_000_000,
                    currency: "UZS".into(),
                }),
                date: "2026-12-02".into(),
                note: Some("telefonda qo'shilgan".into()),
                corrects_entry_id: None,
                refs: Vec::new(),
            };
            journal::append(
                tx,
                &scope,
                &e,
                &Meta {
                    now: "2026-12-02T04:00:00.000Z".into(),
                    device_id: phone_dev.id.clone(),
                },
            )
            .map(|_| ())
        })
        .unwrap();
    let phone = phone_dev.app();
    // Telefon fayli desktopda: zanjir to'g'ri, lekin unga hisob yurituvchi bo'lmagan qurilma yozgan.
    let from_phone = incremental(&phone, &desktop_dev.id);
    let pv = desktop.inspect_baraka(&from_phone.bytes, PASSWORD).unwrap();
    assert!(pv.forks.iter().any(|f| f.reason == "NOT_KEEPER_WRITE"));
    // Desktop yangi yozuv qo'shdi — telefondagi nusxa bilan bir seq da farq: FORK.
    desktop
        .add_venture_entry(
            &uy,
            &p.id,
            entry("EXPENSE", Some("RENT"), "500 000", "02.12.2026", None),
        )
        .unwrap();
    let f = incremental(&desktop, &phone_dev.id);
    let pv = phone.inspect_baraka(&f.bytes, PASSWORD).unwrap();
    let fork = pv.forks.iter().find(|f| f.reason == "FORK").unwrap();
    assert_eq!(fork.agreement_id, p.agreement_id);
    let before = phone.journal(&uy, &p.agreement_id).unwrap().len();
    assert_eq!(
        phone
            .apply_baraka(&f.bytes, PASSWORD, Vec::new())
            .unwrap_err()
            .code,
        "INTERCHANGE_FORK"
    );
    assert_eq!(phone.journal(&uy, &p.agreement_id).unwrap().len(), before);
}
