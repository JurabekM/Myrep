//! `.baraka` eksport/import va qurilmalarni ulash (U14; `docs/BARAKA_OILASI.md` 8.3–8.5, 6.6).
//!
//! * Eksport — to'liq yoki inkremental (qabul qiluvchi qurilma bilan oxirgi kelishilgan
//!   holatdan farq qiladigan yozuvlar). Yuborilgan yozuvlar «kutilmoqda» bo'ladi va qabul
//!   qiluvchining keyingi faylidagi `ackExportId` bilan tasdiqlanadi.
//! * Import — avval ko'rinish (nima qo'shiladi, o'zgaradi, ziddiyatlar, ayrilishlar), keyin
//!   foydalanuvchi har ziddiyat uchun tanlagan holda qo'llash. Pul va sana maydonlarida LWW yo'q.
//! * Yopilgan yozuvlar (jurnal, imzolangan versiya, yopilgan davr, bayonnoma va h.k.) import
//!   orqali o'zgarmaydi; jurnal zanjiri qayta hisoblanadi, ayrilish (fork) — import to'xtaydi.
use std::collections::{BTreeMap, HashMap, HashSet};

use baraka_interchange::canon::{row_hash, Row};
use baraka_interchange::chain::{check as check_chain, ChainOutcome};
use baraka_interchange::container::{self, normalize_pairing_code};
use baraka_interchange::merge::{decide, diff, Decision};
use baraka_interchange::model::{
    decode, encode, Audience as XAudience, Meta as XMeta, Mode, RowRecord,
};
use baraka_interchange::tables::{sync_tables, TableMode};
use baraka_journal::{EntryKind, JournalAmount, JournalEntry};
use baraka_money::{format, Currency, Money};
use baraka_storage::repo::{household, kk_ledger, kk_stock, roles, sync};
use baraka_storage::SpaceScope;
use chrono::SecondsFormat;
use serde_json::Value;

use crate::access::{Audience, Role, Verdict};
use crate::events::Topic;
use crate::text::{clean_opt, required};
use crate::*;

const JOURNAL: &str = "journal_entries";
const MAX_LABEL: usize = 80;
/// `*_json` ustunlari (xarajatlar ro'yxati, stsenariylar) ziddiyat jadvalida shu uzunlikkacha.
const MAX_JSON_VALUE: usize = 400;

pub(crate) const ALL_TOPICS: [Topic; 18] = [
    Topic::Household,
    Topic::Categories,
    Topic::Incomes,
    Topic::Expenses,
    Topic::Vault,
    Topic::AllocationRule,
    Topic::Agreements,
    Topic::Journal,
    Topic::Debts,
    Topic::Budget,
    Topic::Ceremonies,
    Topic::Partnerships,
    Topic::Ventures,
    Topic::Ideas,
    Topic::Governance,
    Topic::Devices,
    Topic::Sync,
    Topic::Kasbkor,
];

fn corrupt() -> AppError {
    AppError::new("INTERCHANGE_CORRUPT")
}

fn u32_of(n: usize) -> u32 {
    u32::try_from(n).unwrap_or(u32::MAX)
}

fn text(row: &Row, k: &str) -> Option<String> {
    row.get(k).and_then(Value::as_str).map(str::to_string)
}

fn pk_of(row: &Row, pk: &str) -> Result<String, AppError> {
    text(row, pk).ok_or_else(corrupt)
}

/// Fayldagi yoki bazadagi jurnal satridan `JournalEntry` (zanjirni qayta hisoblash uchun).
fn journal_entry(row: &Row) -> Result<JournalLine, AppError> {
    let s = |k: &str| text(row, k);
    let amount = match (
        row.get("amount_minor").and_then(Value::as_i64),
        s("currency"),
    ) {
        (Some(minor), Some(currency)) => Some(JournalAmount { minor, currency }),
        (None, None) => None,
        _ => return Err(corrupt()),
    };
    let refs: Vec<String> = match s("refs_json") {
        Some(j) => serde_json::from_str(&j).map_err(|_| corrupt())?,
        None => Vec::new(),
    };
    let entry = JournalEntry {
        id: s("id").ok_or_else(corrupt)?,
        agreement_id: s("agreement_id").ok_or_else(corrupt)?,
        kind: EntryKind::parse(&s("kind").ok_or_else(corrupt)?).ok_or_else(corrupt)?,
        party_id: s("party_id"),
        amount,
        date: s("entry_date").ok_or_else(corrupt)?,
        note: s("note"),
        corrects_entry_id: s("corrects_entry_id"),
        refs,
    };
    let seq = row.get("seq").and_then(Value::as_i64).ok_or_else(corrupt)?;
    Ok((seq, entry, s("hash").ok_or_else(corrupt)?))
}

/// Jurnal satri: (seq, yozuv, saqlangan xesh).
type JournalLine = (i64, JournalEntry, String);

/// Kelishuv bo'yicha jurnal satrlari, `seq` tartibida.
fn journals(rows: &[&Row]) -> Result<BTreeMap<String, Vec<JournalLine>>, AppError> {
    let mut out: BTreeMap<String, Vec<JournalLine>> = BTreeMap::new();
    for r in rows {
        let e = journal_entry(r)?;
        out.entry(e.1.agreement_id.clone()).or_default().push(e);
    }
    for list in out.values_mut() {
        list.sort_by_key(|e| e.0);
    }
    Ok(out)
}

/// Rolli qurilma faylidagi yozuv qo'llanmaydi (K8).
#[derive(Clone, Debug, PartialEq, Eq)]
enum Skip {
    /// Egasining o'z yozuvi qaytib kelgan.
    Ignored,
    /// Sababi bilan rad etilgan.
    Rejected(String),
}

/// Bitta kelgan yozuv va unga qaror.
struct Item {
    table: String,
    pk: String,
    remote: Row,
    remote_hash: String,
    local: Option<Row>,
    decision: Decision,
    skip: Option<Skip>,
}

impl Item {
    fn key(&self) -> String {
        format!("{}:{}", self.table, self.pk)
    }
}

struct Plan {
    meta: XMeta,
    items: Vec<Item>,
    forks: Vec<ForkDto>,
    /// `ackExportId` tasdiqlagan, yuborilgan yozuvlar: (jadval, kalit, xesh).
    acked: Vec<(String, String, String)>,
    /// Rolli ulash faylini tasdiqlagan yangi qurilma — egasi uni rolga bog'laydi (K8).
    bind: Option<roles::DeviceAccessRow>,
}

impl App {
    fn household_id(&self) -> Result<String, AppError> {
        Ok(self.ctx()?.household_id)
    }

    fn kdf(&self) -> container::Kdf {
        self.export_kdf
            .lock()
            .map_or(container::Kdf::STANDARD, |k| *k)
    }

    fn schema_version(&self) -> Result<i64, AppError> {
        Ok(self.db.schema_version()?)
    }

    fn this_device_name(&self, household_id: &str) -> Result<String, AppError> {
        let devices = self.db.read(|c| sync::dump(c, household_id, "devices"))?;
        Ok(devices
            .iter()
            .find(|d| text(d, "id").as_deref() == Some(self.device_id.as_str()))
            .and_then(|d| text(d, "name"))
            .unwrap_or_default())
    }

    /// Xonadon qurilmalari va har biri bilan oxirgi sinxronlash.
    pub fn devices(&self) -> Result<Vec<DeviceDto>, AppError> {
        let h = self.household_id()?;
        let peers = self.db.read(|c| sync::peers(c, &h))?;
        let access = self.db.read(|c| roles::device_access(c, &h))?;
        let rows = self.db.read(|c| sync::dump(c, &h, "devices"))?;
        Ok(rows
            .iter()
            .filter(|r| r.get("deleted_at").is_none_or(Value::is_null))
            .map(|r| {
                let id = text(r, "id").unwrap_or_default();
                let peer = peers.iter().find(|p| p.peer_device_id == id);
                let acc = access.iter().find(|a| a.device_id == id);
                DeviceDto {
                    role: acc.map(|a| a.role.clone()),
                    space_id: acc.map(|a| a.space_id.clone()),
                    revoked: acc.is_some_and(|a| a.revoked_at.is_some()),
                    is_this: id == self.device_id,
                    name: text(r, "name").unwrap_or_default(),
                    platform: text(r, "platform").unwrap_or_default(),
                    paired_at: text(r, "paired_at").unwrap_or_default(),
                    last_import_at: peer.and_then(|p| p.last_import_at.clone()),
                    last_export_at: peer.and_then(|p| p.last_export_at.clone()),
                    id,
                }
            })
            .collect())
    }

    /// Eksport qilinadigan yozuvlar va ularning xeshlari (jadval tartibida). `audience` bo'lsa —
    /// rolli qurilma uchun kamaytirilgan (K8); xesh kamaytirilgan nusxadan.
    fn export_rows(
        &self,
        household_id: &str,
        peer: Option<&str>,
        incremental: bool,
        audience: Option<&Audience>,
    ) -> Result<Vec<(RowRecord, String, String)>, AppError> {
        let bases = match peer {
            Some(p) if incremental => self.db.read(|c| sync::bases(c, p))?,
            _ => HashMap::new(),
        };
        let mut all = Vec::new();
        for spec in sync_tables() {
            let rows = self.db.read(|c| sync::dump(c, household_id, &spec.name))?;
            all.push((spec.name.clone(), rows));
        }
        if let Some(a) = audience {
            all = a.filter(all);
        }
        let mut out = Vec::new();
        for (spec, (_, rows)) in sync_tables().iter().zip(all) {
            let mut chosen = Vec::new();
            for r in rows {
                let pk = pk_of(&r, &spec.primary_key)?;
                let h = row_hash(&spec.name, &r)?;
                let changed = bases.get(&(spec.name.clone(), pk.clone())) != Some(&h);
                chosen.push((changed, pk, h, r));
            }
            if spec.name == JOURNAL && incremental {
                // Jurnal zanjirini qabul qiluvchi qayta hisoblaydi: kelishuvning bitta yozuvi
                // yuborilsa — butun zanjiri yuboriladi.
                let touched: Vec<String> = chosen
                    .iter()
                    .filter(|x| x.0)
                    .filter_map(|x| text(&x.3, "agreement_id"))
                    .collect();
                for x in &mut chosen {
                    if text(&x.3, "agreement_id").is_some_and(|a| touched.contains(&a)) {
                        x.0 = true;
                    }
                }
            }
            for (changed, pk, h, r) in chosen {
                if changed || !incremental {
                    out.push((
                        RowRecord {
                            table: spec.name.clone(),
                            data: r,
                        },
                        pk,
                        h,
                    ));
                }
            }
        }
        Ok(out)
    }

    fn seal_export(
        &self,
        household_id: &str,
        password: &str,
        mode: Mode,
        peer: Option<&str>,
        audience: Option<&Audience>,
    ) -> Result<(String, u32, Vec<u8>), AppError> {
        let rows = self.export_rows(household_id, peer, mode == Mode::Incremental, audience)?;
        let ack = match peer {
            Some(p) => self
                .db
                .read(|c| sync::peer(c, household_id, p))?
                .and_then(|x| x.last_ack_export_id),
            None => None,
        };
        let export_id = self.new_id();
        let meta = XMeta {
            format_version: baraka_interchange::FORMAT_VERSION,
            schema_version: self.schema_version()?,
            household_id: household_id.to_string(),
            source_device_id: self.device_id.clone(),
            source_device_name: self.this_device_name(household_id)?,
            export_id: export_id.clone(),
            ack_export_id: ack,
            mode,
            exported_at: self
                .clock
                .now()
                .to_rfc3339_opts(SecondsFormat::Millis, true),
            row_count: 0,
            audience: audience
                .filter(|_| mode == Mode::Pairing)
                .map(|a| XAudience {
                    role: a.role.as_str().into(),
                    space_id: a.space_id.clone(),
                }),
        };
        let records: Vec<RowRecord> = rows.iter().map(|r| r.0.clone()).collect();
        let plain = zeroize::Zeroizing::new(encode(&meta, &records)?);
        let bytes = container::seal(&plain, password, self.kdf())?;
        // Kutilayotgan yozuvlar faqat qabul qiluvchi ma'lum bo'lsa yoki ulash faylida.
        let pending: Vec<(String, String, String)> = if peer.is_some() || mode == Mode::Pairing {
            rows.iter()
                .map(|(r, pk, h)| (r.table.clone(), pk.clone(), h.clone()))
                .collect()
        } else {
            Vec::new()
        };
        let count = u32_of(rows.len());
        let m = self.meta();
        let role = audience
            .filter(|_| mode == Mode::Pairing)
            .map(|a| (a.role.as_str(), a.space_id.as_str()));
        self.db.write_sync(|tx| {
            sync::record_export(
                tx,
                household_id,
                &export_id,
                peer,
                mode.as_str(),
                i64::from(count),
                &pending,
                &m,
            )?;
            match role {
                Some((r, sp)) => roles::set_export_role(tx, &export_id, r, sp),
                None => Ok(()),
            }
        })?;
        Ok((export_id, count, bytes))
    }

    fn file_name(&self, mode: Mode) -> String {
        let day = self.clock.now().format("%Y%m%d");
        format!("baraka-{day}-{}.baraka", mode.as_str().to_lowercase())
    }

    /// Shifrlangan `.baraka` fayl: zaxira nusxa (to'liq) yoki boshqa qurilma uchun.
    pub fn export_baraka(&self, input: ExportInput) -> Result<ExportFileDto, AppError> {
        container::check_password(&input.password)?;
        let h = self.household_id()?;
        let mode = match input.mode.as_str() {
            "FULL" => Mode::Full,
            "INCREMENTAL" => Mode::Incremental,
            _ => return Err(AppError::on("INVALID_MODE", "mode")),
        };
        let peer = clean_opt(input.peer_device_id.as_deref());
        if mode == Mode::Incremental && peer.is_none() {
            return Err(AppError::on("REQUIRED", "peerDeviceId"));
        }
        if let Some(p) = &peer {
            let known = self.devices()?.iter().any(|d| &d.id == p && !d.is_this);
            if !known {
                return Err(AppError::on("UNKNOWN_DEVICE", "peerDeviceId"));
            }
        }
        let audience = match &peer {
            Some(p) => self.peer_audience(&h, p)?,
            None => None,
        };
        let (export_id, rows, bytes) = self.seal_export(
            &h,
            &input.password,
            mode,
            peer.as_deref(),
            audience.as_ref(),
        )?;
        self.publish(None, &[Topic::Sync]);
        Ok(ExportFileDto {
            export_id,
            file_name: self.file_name(mode),
            mode: mode.as_str().into(),
            rows,
            bytes,
        })
    }

    /// Egasining qurilmasida: rolli qurilma uchun kim (bekor qilingan — eksport yo'q). Rolli
    /// qurilma faqat egasiga eksport qiladi — u o'zi kamaytirilgan.
    fn peer_audience(&self, household_id: &str, peer: &str) -> Result<Option<Audience>, AppError> {
        if self.access_in(household_id)?.role != Role::Owner {
            return Ok(None);
        }
        match self.db.read(|c| roles::access_of(c, household_id, peer))? {
            Some(a) if a.revoked_at.is_some() => Err(AppError::new("DEVICE_REVOKED")),
            Some(a) => Ok(Some(Audience {
                role: Role::parse(&a.role).ok_or_else(corrupt)?,
                space_id: a.space_id,
                device_id: Some(a.device_id),
            })),
            None => Ok(None),
        }
    }

    /// Yangi qurilmani ulash (8.5): bir martalik kod, QR va shu kod bilan shifrlangan fayl.
    /// Rol bilan (K8) — fayl kamaytirilgan, yangi qurilma rolini shundan biladi.
    pub fn pairing_offer(&self, input: PairingInput) -> Result<PairingOfferDto, AppError> {
        let ctx = self.ctx()?;
        self.ensure_owner(&ctx)?;
        let h = self.household()?;
        let audience = match clean_opt(input.role.as_deref()) {
            None => None,
            Some(r) => {
                let role = Role::parse(&r)
                    .filter(|r| *r != Role::Owner)
                    .ok_or(AppError::on("INVALID_ROLE", "role"))?;
                let space = clean_opt(input.space_id.as_deref())
                    .ok_or(AppError::on("REQUIRED", "spaceId"))?;
                self.kk_scope(&ctx, &space)?;
                Some(Audience {
                    role,
                    space_id: space,
                    device_id: None,
                })
            }
        };
        let code = container::pairing_code()?;
        let secret = normalize_pairing_code(&code).ok_or_else(corrupt)?;
        let (_, _, bytes) =
            self.seal_export(&h.id, &secret, Mode::Pairing, None, audience.as_ref())?;
        let payload = serde_json::json!({
            "v": 1,
            "h": h.id,
            "c": code,
            "d": self.this_device_name(&h.id)?,
        });
        let qr = baraka_pdf::qr_svg(&format!("BARAKA-PAIR:{payload}"))
            .map_err(|e| AppError::new(e.code))?;
        self.publish(None, &[Topic::Sync]);
        Ok(PairingOfferDto {
            code,
            qr_svg: String::from_utf8(qr).map_err(|_| corrupt())?,
            file_name: self.file_name(Mode::Pairing),
            household_name: h.name,
            bytes,
        })
    }

    /// Rolli qurilmani bekor qilish (K8): unga eksport ham, undan import ham to'xtaydi. Qurilmadagi
    /// mavjud ma'lumot masofadan o'chirilmaydi.
    pub fn revoke_device(&self, device_id: &str) -> Result<Vec<DeviceDto>, AppError> {
        let ctx = self.ctx()?;
        self.ensure_owner(&ctx)?;
        let m = self.meta();
        let done = self
            .db
            .write(|tx| roles::revoke_access(tx, &ctx.household_id, device_id, &m))?;
        if !done {
            return Err(AppError::on("NOT_FOUND", "deviceId"));
        }
        self.publish(None, &[Topic::Devices, Topic::Sync]);
        self.devices()
    }

    /// Faylni ochadi va tekshiradi: xonadon, sxema versiyasi, o'z fayli emasligi.
    fn read_file(&self, bytes: &[u8], password: &str) -> Result<(XMeta, Vec<RowRecord>), AppError> {
        let secret = normalize_pairing_code(password).unwrap_or_else(|| password.to_string());
        let (_, plain) = container::open(bytes, &secret).or_else(|e| match e {
            // Ulash kodi bilan ochilmasa — oddiy parol sifatida ham urinib ko'ramiz.
            baraka_interchange::InterchangeError::BadPassword if secret != password => {
                container::open(bytes, password)
            }
            other => Err(other),
        })?;
        let (meta, rows) = decode(&plain)?;
        if meta.schema_version != self.schema_version()? {
            return Err(AppError::new("INTERCHANGE_SCHEMA_MISMATCH"));
        }
        Ok((meta, rows))
    }

    fn plan(
        &self,
        household_id: &str,
        meta: XMeta,
        rows: Vec<RowRecord>,
    ) -> Result<Plan, AppError> {
        if meta.household_id != household_id {
            return Err(AppError::new("INTERCHANGE_WRONG_HOUSEHOLD"));
        }
        if meta.source_device_id == self.device_id {
            return Err(AppError::new("INTERCHANGE_OWN_FILE"));
        }
        let peer = meta.source_device_id.clone();
        // K8: rolli qurilma faqat egasidan oladi; egasi rolli qurilmadan faqat ruxsat etilganini.
        let mut bind = None;
        let audience = if self.access_in(household_id)?.role == Role::Owner {
            let known = self.db.read(|c| roles::access_of(c, household_id, &peer))?;
            let found = match known {
                Some(a) if a.revoked_at.is_some() => return Err(AppError::new("DEVICE_REVOKED")),
                Some(a) => Some((a.role, a.space_id)),
                None => match &meta.ack_export_id {
                    Some(ack) => {
                        let r = self
                            .db
                            .read(|c| roles::pairing_role(c, household_id, ack, &peer))?;
                        if let Some((role, space)) = &r {
                            bind = Some(roles::DeviceAccessRow {
                                device_id: peer.clone(),
                                role: role.clone(),
                                space_id: space.clone(),
                                revoked_at: None,
                            });
                        }
                        r
                    }
                    None => None,
                },
            };
            match found {
                Some((role, space)) => Some(Audience {
                    role: Role::parse(&role).ok_or_else(corrupt)?,
                    space_id: space,
                    device_id: Some(peer.clone()),
                }),
                None => None,
            }
        } else {
            if self
                .db
                .read(|c| roles::access_of(c, household_id, &peer))?
                .is_some()
            {
                return Err(AppError::new("ROLE_FORBIDDEN"));
            }
            None
        };
        let acked = match &meta.ack_export_id {
            Some(a) => self
                .db
                .read(|c| sync::acked_pending(c, household_id, &peer, a))?,
            None => Vec::new(),
        };
        let mut bases = self.db.read(|c| sync::bases(c, &peer))?;
        for (t, id, h) in &acked {
            bases.insert((t.clone(), id.clone()), h.clone());
        }
        // Jadval tartibi bo'yicha (ota yozuvlar oldin), jadval ichida — fayl tartibi.
        let order: HashMap<&str, usize> = sync_tables()
            .iter()
            .enumerate()
            .map(|(i, t)| (t.name.as_str(), i))
            .collect();
        let mut rows = rows;
        rows.sort_by_key(|r| order.get(r.table.as_str()).copied().unwrap_or(usize::MAX));

        // Jurnal: zanjirni qayta hisoblash va mahalliy nusxa bilan solishtirish.
        let incoming_journal: Vec<&Row> = rows
            .iter()
            .filter(|r| r.table == JOURNAL && audience.is_none())
            .map(|r| &r.data)
            .collect();
        let local_journal_rows = self.db.read(|c| sync::dump(c, household_id, JOURNAL))?;
        let local_refs: Vec<&Row> = local_journal_rows.iter().collect();
        let local_j = journals(&local_refs)?;
        let incoming_j = journals(&incoming_journal)?;
        let agreements = self
            .db
            .read(|c| sync::dump(c, household_id, "agreements"))?;
        let title_of = |id: &str| {
            agreements
                .iter()
                .find(|a| text(a, "id").as_deref() == Some(id))
                .and_then(|a| text(a, "title"))
                .or_else(|| {
                    rows.iter()
                        .find(|r| {
                            r.table == "agreements" && text(&r.data, "id").as_deref() == Some(id)
                        })
                        .and_then(|r| text(&r.data, "title"))
                })
                .unwrap_or_else(|| id.to_string())
        };
        let mut forks = Vec::new();
        // Kelishuv → shu seq dan boshlab yangi (qo'shiladigan) yozuvlar.
        let mut append_from: HashMap<String, i64> = HashMap::new();
        for (agreement, list) in &incoming_j {
            let fork = |seq: usize, reason: &str| ForkDto {
                agreement_id: agreement.clone(),
                title: title_of(agreement),
                seq: u32_of(seq),
                reason: reason.into(),
            };
            let contiguous = list
                .iter()
                .enumerate()
                .all(|(i, e)| i64::try_from(i + 1).ok() == Some(e.0));
            if !contiguous {
                forks.push(fork(1, "TAMPERED"));
                continue;
            }
            let entries: Vec<JournalEntry> = list.iter().map(|e| e.1.clone()).collect();
            let hashes: Vec<String> = list.iter().map(|e| e.2.clone()).collect();
            let local: Vec<String> = local_j
                .get(agreement)
                .map(|l| l.iter().map(|e| e.2.clone()).collect())
                .unwrap_or_default();
            match check_chain(&local, &entries, &hashes) {
                ChainOutcome::Append { from } => {
                    let keeper = agreements
                        .iter()
                        .find(|a| text(a, "id").as_deref() == Some(agreement.as_str()))
                        .and_then(|a| text(a, "keeper_device_id"));
                    if !local.is_empty() && keeper.as_deref() == Some(self.device_id.as_str()) {
                        // Jurnalga faqat hisob yurituvchi (shu qurilma) yozadi (6.6).
                        forks.push(fork(from, "NOT_KEEPER_WRITE"));
                    } else {
                        append_from
                            .insert(agreement.clone(), i64::try_from(from).unwrap_or(i64::MAX));
                    }
                }
                ChainOutcome::Same | ChainOutcome::LocalAhead => {}
                ChainOutcome::Fork { seq } => forks.push(fork(seq, "FORK")),
                ChainOutcome::Tampered { seq } => forks.push(fork(seq, "TAMPERED")),
            }
        }

        let mut items = Vec::new();
        for r in rows {
            let spec = baraka_interchange::tables::table(&r.table)
                .ok_or(AppError::new("INTERCHANGE_SCHEMA_MISMATCH"))?;
            let owner = if spec.name == "households" {
                "id"
            } else {
                "household_id"
            };
            if text(&r.data, owner).as_deref() != Some(household_id) {
                return Err(AppError::new("INTERCHANGE_WRONG_HOUSEHOLD"));
            }
            let pk = pk_of(&r.data, &spec.primary_key)?;
            let remote_hash = row_hash(&spec.name, &r.data)?;
            let local = self
                .db
                .read(|c| sync::get(c, household_id, &spec.name, &pk))?;
            let decision = if spec.name == JOURNAL {
                let (seq, entry, _) = journal_entry(&r.data)?;
                match append_from.get(&entry.agreement_id) {
                    Some(from) if seq >= *from => Decision::Insert,
                    _ => Decision::Same,
                }
            } else {
                let local_hash = match &local {
                    Some(l) => Some(row_hash(&spec.name, l)?),
                    None => None,
                };
                decide(
                    local_hash.as_deref(),
                    bases
                        .get(&(spec.name.clone(), pk.clone()))
                        .map(String::as_str),
                    &remote_hash,
                    spec.mode == TableMode::AppendOnly,
                )
            };
            let skip =
                audience
                    .as_ref()
                    .and_then(|a| match a.verdict(&peer, &spec.name, &r.data) {
                        Verdict::Accept => None,
                        Verdict::Ignore => Some(Skip::Ignored),
                        Verdict::Reject(code) => Some(Skip::Rejected(code.into())),
                    });
            items.push(Item {
                table: spec.name.clone(),
                pk,
                remote: r.data,
                remote_hash,
                local,
                decision,
                skip,
            });
        }
        if let Some(a) = audience.as_ref().filter(|a| a.role == Role::Seller) {
            let rejected = self.validate_seller_rows(household_id, a, &items)?;
            for i in &mut items {
                if let Some(reason) = rejected.get(&i.key()) {
                    i.skip = Some(Skip::Rejected(reason.clone()));
                }
            }
        }
        Ok(Plan {
            meta,
            items,
            forks,
            acked,
            bind,
        })
    }

    /// Sotuvchi yozuvlarini egasining qoidalari bilan tekshirish (K8): yopilgan oy va kassa kuni,
    /// nasiya qoldig'i, tovar qoldig'i. Bog'langan tushum va harakat birga rad etiladi.
    fn validate_seller_rows(
        &self,
        household_id: &str,
        a: &Audience,
        items: &[Item],
    ) -> Result<HashMap<String, String>, AppError> {
        let ctx = self.ctx()?;
        let scope = SpaceScope {
            household_id: household_id.to_string(),
            space_id: a.space_id.clone(),
        };
        let new: Vec<&Item> = items
            .iter()
            .filter(|i| {
                i.skip.is_none()
                    && i.decision == Decision::Insert
                    && matches!(
                        i.table.as_str(),
                        "incomes" | "kk_credit_events" | "kk_stock_moves"
                    )
            })
            .collect();
        let date = |i: &Item| text(&i.remote, "occurred_on").unwrap_or_default();
        let mut rejected: HashMap<String, String> = HashMap::new();
        for i in &new {
            let column = if i.table == "incomes" {
                "channel"
            } else {
                "wallet"
            };
            let cash = text(&i.remote, column).as_deref() == Some("CASH");
            let d = date(i);
            let check = self
                .kk_ensure_open(&scope, &d, "occurredOn")
                .and_then(|()| self.kk_ensure_cash_open(&scope, &d, cash));
            if let Err(e) = check {
                rejected.insert(i.key(), e.code);
            }
        }
        link_rejections(&new, &mut rejected);
        let mut ordered: Vec<&Item> = new.clone();
        ordered.sort_by_key(|i| date(i));
        let mut events = Vec::new();
        let mut moves = Vec::new();
        for i in ordered {
            if rejected.contains_key(&i.key()) {
                continue;
            }
            let check = match i.table.as_str() {
                "kk_credit_events" => {
                    events.push(credit_event_row(&i.remote)?);
                    let r = self.kk_credit_check_with(&ctx, &scope, &events);
                    if r.is_err() {
                        events.pop();
                    }
                    r
                }
                "kk_stock_moves" => {
                    moves.push(stock_move_row(&i.remote)?);
                    let r = self.kk_stock_value_with(&ctx, &scope, &moves).map(|_| ());
                    if r.is_err() {
                        moves.pop();
                    }
                    r
                }
                _ => Ok(()),
            };
            if let Err(e) = check {
                rejected.insert(i.key(), e.code);
            }
        }
        link_rejections(&new, &mut rejected);
        Ok(rejected)
    }

    fn show_value(
        &self,
        locale: baraka_money::Locale,
        row: &Row,
        field: &str,
        v: &Value,
    ) -> String {
        match v {
            Value::Null => "—".into(),
            Value::Number(n) => {
                let currency = text(row, "currency").and_then(|c| Currency::from_code(&c).ok());
                match (n.as_i64(), currency) {
                    (Some(minor), Some(cur)) if field.ends_with("_minor") => {
                        format(Money::new(minor, cur), locale)
                    }
                    _ => n.to_string(),
                }
            }
            Value::String(s) if field.ends_with("_json") => {
                let currency = text(row, "currency").and_then(|c| Currency::from_code(&c).ok());
                match serde_json::from_str::<Value>(s) {
                    Ok(parsed) => show_json(locale, currency, &parsed),
                    Err(_) => s.clone(),
                }
                .chars()
                .take(MAX_JSON_VALUE)
                .collect()
            }
            Value::String(s) => s.chars().take(MAX_LABEL).collect(),
            Value::Object(_) => baraka_interchange::canon::blob_bytes(v)
                .map_or_else(String::new, |b| format!("[{} B]", b.len())),
            _ => String::new(),
        }
    }

    /// Yozuvning qisqa tavsifi: nomi yoki izohi, summasi va sanasi (mavjud bo'lsa).
    fn label(&self, locale: baraka_money::Locale, row: &Row) -> String {
        let name = [
            "title",
            "name",
            "display_name",
            "source",
            "subject",
            "creditor",
            "debtor",
            "note",
            "reason",
            "file_name",
        ]
        .iter()
        .find_map(|k| text(row, k).filter(|s| !s.is_empty()));
        let amount = [
            "amount_minor",
            "principal_minor",
            "target_minor",
            "estimated_minor",
        ]
        .iter()
        .find_map(|k| {
            row.get(*k)
                .filter(|v| v.is_i64())
                .map(|v| self.show_value(locale, row, k, v))
        });
        let date = [
            "occurred_on",
            "paid_on",
            "entry_date",
            "due_on",
            "planned_on",
            "lent_on",
        ]
        .iter()
        .find_map(|k| text(row, k));
        let parts: Vec<String> = [name, amount, date].into_iter().flatten().collect();
        let s = parts.join(" · ");
        s.chars().take(MAX_LABEL).collect()
    }

    fn preview(&self, plan: &Plan) -> Result<ImportPreviewDto, AppError> {
        let locale = self.ctx()?.locale;
        let count = |d: Decision| {
            u32_of(
                plan.items
                    .iter()
                    .filter(|i| i.decision == d && i.table != JOURNAL && i.skip.is_none())
                    .count(),
            )
        };
        let deleted = |r: &Row| r.get("deleted_at").is_some_and(|v| !v.is_null());
        let mut conflicts = Vec::new();
        let mut protected = Vec::new();
        let mut rejected = Vec::new();
        let mut ignored = 0;
        for i in &plan.items {
            let key = i.key();
            match &i.skip {
                Some(Skip::Ignored) => {
                    ignored += 1;
                    continue;
                }
                Some(Skip::Rejected(reason)) => {
                    rejected.push(RejectedItemDto {
                        key,
                        table: i.table.clone(),
                        row_id: i.pk.clone(),
                        label: self.label(locale, &i.remote),
                        reason: reason.clone(),
                    });
                    continue;
                }
                None => {}
            }
            match i.decision {
                Decision::Conflict => {
                    let local = i.local.clone().unwrap_or_default();
                    conflicts.push(ConflictDto {
                        key,
                        table: i.table.clone(),
                        row_id: i.pk.clone(),
                        label: self.label(locale, &local),
                        fields: diff(&local, &i.remote)
                            .into_iter()
                            // Texnik maydonlar (versiya, qurilma) tanlovga ta'sir qilmaydi.
                            .filter(|d| {
                                !matches!(
                                    d.field.as_str(),
                                    "version" | "updated_at" | "updated_by_device_id"
                                )
                            })
                            .map(|d| FieldDiffDto {
                                local: self.show_value(locale, &local, &d.field, &d.local),
                                remote: self.show_value(locale, &i.remote, &d.field, &d.remote),
                                field: d.field,
                            })
                            .collect(),
                        local_deleted: deleted(&local),
                        remote_deleted: deleted(&i.remote),
                    });
                }
                Decision::Protected => protected.push(ImportItemDto {
                    key,
                    table: i.table.clone(),
                    row_id: i.pk.clone(),
                    label: self.label(locale, &i.remote),
                }),
                _ => {}
            }
        }
        Ok(ImportPreviewDto {
            source_device_id: plan.meta.source_device_id.clone(),
            source_device_name: plan.meta.source_device_name.clone(),
            mode: plan.meta.mode.as_str().into(),
            exported_at: plan.meta.exported_at.clone(),
            rows: u32_of(plan.items.len()),
            inserts: count(Decision::Insert),
            updates: count(Decision::Update),
            same: count(Decision::Same),
            kept_local: count(Decision::KeepLocal),
            journal_appended: u32_of(
                plan.items
                    .iter()
                    .filter(|i| i.table == JOURNAL && i.decision == Decision::Insert)
                    .count(),
            ),
            protected,
            rejected,
            ignored,
            conflicts,
            can_apply: plan.forks.is_empty(),
            forks: plan.forks.clone(),
        })
    }

    /// Import oldidan ko'rinish (hech narsa yozilmaydi).
    pub fn inspect_baraka(
        &self,
        bytes: &[u8],
        password: &str,
    ) -> Result<ImportPreviewDto, AppError> {
        let h = self.household_id()?;
        let (meta, rows) = self.read_file(bytes, password)?;
        let plan = self.plan(&h, meta, rows)?;
        self.preview(&plan)
    }

    /// Import: har bir ziddiyat uchun tanlov (`LOCAL` / `REMOTE`) majburiy. Ayrilish bo'lsa —
    /// hech narsa yozilmaydi.
    pub fn apply_baraka(
        &self,
        bytes: &[u8],
        password: &str,
        choices: Vec<ConflictChoiceInput>,
    ) -> Result<ImportResultDto, AppError> {
        let h = self.household_id()?;
        let (meta, rows) = self.read_file(bytes, password)?;
        let plan = self.plan(&h, meta, rows)?;
        if !plan.forks.is_empty() {
            return Err(AppError::new("INTERCHANGE_FORK"));
        }
        let chosen: HashMap<String, String> =
            choices.into_iter().map(|c| (c.key, c.choice)).collect();
        let mut writes: Vec<(&Item, bool)> = Vec::new();
        let mut result = ImportResultDto {
            inserted: 0,
            updated: 0,
            conflicts_local: 0,
            conflicts_remote: 0,
            protected: 0,
            journal_appended: 0,
            rejected: 0,
            ignored: 0,
        };
        for i in &plan.items {
            match i.skip {
                Some(Skip::Ignored) => {
                    result.ignored += 1;
                    continue;
                }
                Some(Skip::Rejected(_)) => {
                    result.rejected += 1;
                    continue;
                }
                None => {}
            }
            let write = match i.decision {
                Decision::Insert => {
                    if i.table == JOURNAL {
                        result.journal_appended += 1;
                    } else {
                        result.inserted += 1;
                    }
                    true
                }
                Decision::Update => {
                    result.updated += 1;
                    true
                }
                Decision::Conflict => match chosen
                    .get(&format!("{}:{}", i.table, i.pk))
                    .map(String::as_str)
                {
                    Some("REMOTE") => {
                        result.conflicts_remote += 1;
                        true
                    }
                    Some("LOCAL") => {
                        result.conflicts_local += 1;
                        false
                    }
                    _ => return Err(AppError::new("CONFLICTS_UNRESOLVED")),
                },
                Decision::Protected => {
                    result.protected += 1;
                    false
                }
                Decision::Same | Decision::KeepLocal => false,
            };
            writes.push((i, write));
        }
        let peer = plan.meta.source_device_id.clone();
        let summary = serde_json::json!({
            "inserted": result.inserted,
            "updated": result.updated,
            "conflictsLocal": result.conflicts_local,
            "conflictsRemote": result.conflicts_remote,
            "protected": result.protected,
            "journalAppended": result.journal_appended,
            "rejected": result.rejected,
            "ignored": result.ignored,
        })
        .to_string();
        let log = sync::ImportLog {
            id: self.new_id(),
            export_id: plan.meta.export_id.clone(),
            peer_device_id: peer.clone(),
            mode: plan.meta.mode.as_str().into(),
            summary_json: summary,
        };
        let m = self.meta();
        self.db.write_sync(|tx| {
            sync::defer_foreign_keys(tx)?;
            if let Some(b) = &plan.bind {
                roles::insert_access(tx, &h, b, &m)?;
            }
            for (i, write) in &writes {
                if *write {
                    sync::write(tx, &i.table, &i.remote)?;
                }
            }
            for (t, id, hash) in &plan.acked {
                sync::set_base(tx, &peer, t, id, hash)?;
            }
            if let Some(a) = &plan.meta.ack_export_id {
                sync::close_acked(tx, &h, &peer, a)?;
            }
            // Ikkala tomon endi kelgan holatni biladi; «mahalliy qolsin» tanlansa ham base —
            // kelgani: keyingi eksportda bizning nusxamiz ularda «faqat bir tomonda o'zgargan».
            for (i, _) in &writes {
                if i.decision != Decision::Protected {
                    sync::set_base(tx, &peer, &i.table, &i.pk, &i.remote_hash)?;
                }
            }
            sync::record_import_from(
                tx,
                &h,
                &peer,
                &plan.meta.source_device_name,
                &plan.meta.export_id,
                &m,
            )?;
            sync::record_import(tx, &h, &log, &m)
        })?;
        self.refresh_role();
        self.publish(None, &ALL_TOPICS);
        Ok(result)
    }

    /// Yangi o'rnatish: mavjud xonadonga qo'shilish yoki zaxira nusxadan tiklash (8.5).
    /// Fayldagi barcha yozuvlar aynan ko'chiriladi, shu qurilma xonadonga qo'shiladi.
    pub fn join_household(&self, bytes: &[u8], input: JoinInput) -> Result<HouseholdDto, AppError> {
        if self.is_initialized()? {
            return Err(AppError::new("ALREADY_INITIALIZED"));
        }
        let device_name = required(&input.device_name, "deviceName")?;
        let platform = clean_opt(Some(&input.platform)).unwrap_or_else(|| "unknown".into());
        let (meta, rows) = self.read_file(bytes, &input.secret)?;
        if meta.mode == Mode::Incremental {
            return Err(AppError::new("INTERCHANGE_NOT_FULL"));
        }
        let h = meta.household_id.clone();
        let journal_rows: Vec<&Row> = rows
            .iter()
            .filter(|r| r.table == JOURNAL)
            .map(|r| &r.data)
            .collect();
        for list in journals(&journal_rows)?.values() {
            let entries: Vec<JournalEntry> = list.iter().map(|e| e.1.clone()).collect();
            let hashes: Vec<String> = list.iter().map(|e| e.2.clone()).collect();
            if !matches!(
                check_chain(&[], &entries, &hashes),
                ChainOutcome::Append { .. }
            ) {
                return Err(AppError::new("INTERCHANGE_JOURNAL_TAMPERED"));
            }
        }
        let order: HashMap<&str, usize> = sync_tables()
            .iter()
            .enumerate()
            .map(|(i, t)| (t.name.as_str(), i))
            .collect();
        let mut rows = rows;
        rows.sort_by_key(|r| order.get(r.table.as_str()).copied().unwrap_or(usize::MAX));
        let mut hashed = Vec::new();
        for r in rows {
            let spec = baraka_interchange::tables::table(&r.table)
                .ok_or(AppError::new("INTERCHANGE_SCHEMA_MISMATCH"))?;
            let owner = if spec.name == "households" {
                "id"
            } else {
                "household_id"
            };
            if text(&r.data, owner).as_deref() != Some(h.as_str()) {
                return Err(AppError::new("INTERCHANGE_WRONG_HOUSEHOLD"));
            }
            let pk = pk_of(&r.data, &spec.primary_key)?;
            let hash = row_hash(&spec.name, &r.data)?;
            hashed.push((r, pk, hash));
        }
        if !hashed.iter().any(|(r, _, _)| r.table == "households") {
            return Err(AppError::new("INTERCHANGE_NOT_FULL"));
        }
        let role = match &meta.audience {
            Some(a) => {
                let r = Role::parse(&a.role)
                    .filter(|r| *r != Role::Owner)
                    .ok_or_else(corrupt)?;
                Some((r.as_str(), a.space_id.clone()))
            }
            None => None,
        };
        let m = self.meta();
        let source = meta.source_device_id.clone();
        self.db.write_sync(|tx| {
            sync::defer_foreign_keys(tx)?;
            if let Some((r, space)) = &role {
                roles::set_local_role(tx, &h, r, space, &m)?;
            }
            for (r, pk, hash) in &hashed {
                sync::write(tx, &r.table, &r.data)?;
                sync::set_base(tx, &source, &r.table, pk, hash)?;
            }
            household::insert_device(tx, &h, &device_name, &platform, &m)?;
            sync::record_import_from(
                tx,
                &h,
                &source,
                &meta.source_device_name,
                &meta.export_id,
                &m,
            )
        })?;
        self.refresh_role();
        self.publish(None, &ALL_TOPICS);
        self.household()
    }
}

/// Rad etilgan tushum bilan bog'langan harakat (nasiya to'lovi, sotuv) va aksincha (K8).
fn link_rejections(items: &[&Item], rejected: &mut HashMap<String, String>) {
    let bad_incomes: HashSet<String> = items
        .iter()
        .filter(|i| i.table == "incomes" && rejected.contains_key(&i.key()))
        .map(|i| i.pk.clone())
        .collect();
    let bad_linked: HashSet<String> = items
        .iter()
        .filter(|i| i.table != "incomes" && rejected.contains_key(&i.key()))
        .filter_map(|i| text(&i.remote, "income_id"))
        .collect();
    for i in items {
        let hit = if i.table == "incomes" {
            bad_linked.contains(&i.pk)
        } else {
            text(&i.remote, "income_id").is_some_and(|x| bad_incomes.contains(&x))
        };
        if hit {
            rejected
                .entry(i.key())
                .or_insert_with(|| "LINKED_REJECTED".into());
        }
    }
}

fn int(row: &Row, k: &str) -> Option<i64> {
    row.get(k).and_then(Value::as_i64)
}

fn credit_event_row(r: &Row) -> Result<kk_ledger::KkCreditEventRow, AppError> {
    Ok(kk_ledger::KkCreditEventRow {
        id: text(r, "id").ok_or_else(corrupt)?,
        sale_id: text(r, "sale_id").ok_or_else(corrupt)?,
        kind: text(r, "kind").ok_or_else(corrupt)?,
        occurred_on: text(r, "occurred_on").ok_or_else(corrupt)?,
        amount_minor: int(r, "amount_minor"),
        months: int(r, "months"),
        wallet: text(r, "wallet"),
        income_id: text(r, "income_id"),
        note: text(r, "note"),
    })
}

fn stock_move_row(r: &Row) -> Result<kk_stock::KkStockMoveRow, AppError> {
    Ok(kk_stock::KkStockMoveRow {
        id: text(r, "id").ok_or_else(corrupt)?,
        item_id: text(r, "item_id").ok_or_else(corrupt)?,
        kind: text(r, "kind").ok_or_else(corrupt)?,
        occurred_on: text(r, "occurred_on").ok_or_else(corrupt)?,
        qty: int(r, "qty").ok_or_else(corrupt)?,
        amount_minor: int(r, "amount_minor"),
        wallet: text(r, "wallet"),
        income_id: text(r, "income_id"),
        reason: text(r, "reason"),
    })
}

/// `*_json` ustunidagi qiymatni odam o'qiydigan qilib chiqaradi: ro'yxat elementlari «; » bilan,
/// obyektda matnlar va summalar (`…Minor` — pul) — `Overlok: 4 500 000 so'm`.
fn show_json(locale: baraka_money::Locale, currency: Option<Currency>, v: &Value) -> String {
    match v {
        Value::Array(items) => items
            .iter()
            .map(|i| show_json(locale, currency, i))
            .collect::<Vec<_>>()
            .join("; "),
        Value::Object(map) => {
            let mut texts = Vec::new();
            let mut values = Vec::new();
            for (k, x) in map {
                match x {
                    Value::String(t) => texts.push(t.clone()),
                    Value::Number(n) => values.push(match (n.as_i64(), currency) {
                        (Some(minor), Some(cur))
                            if k.ends_with("Minor") || k.ends_with("_minor") =>
                        {
                            format(Money::new(minor, cur), locale)
                        }
                        _ => n.to_string(),
                    }),
                    Value::Bool(b) => values.push(if *b { "✓" } else { "✗" }.into()),
                    Value::Null => {}
                    nested => values.push(format!("({})", show_json(locale, currency, nested))),
                }
            }
            match (texts.is_empty(), values.is_empty()) {
                (false, false) => format!("{}: {}", texts.join(", "), values.join(" / ")),
                (false, true) => texts.join(", "),
                _ => values.join(" / "),
            }
        }
        Value::String(t) => t.clone(),
        Value::Number(n) => n.to_string(),
        Value::Bool(b) => if *b { "✓" } else { "✗" }.into(),
        Value::Null => "—".into(),
    }
}

#[cfg(test)]
mod tests {
    use super::show_json;
    use baraka_money::{Currency, Locale};

    #[test]
    fn json_columns_are_readable_in_conflicts() {
        let uzs = Currency::from_code("UZS").ok();
        let capex = serde_json::json!([
            {"title": "Overlok", "amountMinor": 450_000_000},
            {"title": "Stol", "amountMinor": 150_000_000}
        ]);
        let s = show_json(Locale::Uz, uzs, &capex);
        assert!(s.starts_with("Overlok: 4"), "{s}");
        assert!(s.contains("; Stol: 1"), "{s}");
        assert!(!s.contains("amountMinor"), "{s}");
        // Valyuta noma'lum bo'lsa — butun son o'zgarishsiz.
        assert_eq!(
            show_json(
                Locale::Uz,
                None,
                &serde_json::json!({"n": "A", "xMinor": 5})
            ),
            "A: 5"
        );
    }
}
