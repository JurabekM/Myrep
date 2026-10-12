//! `.baraka` almashish hujjati: jadvalga bog'liq bo'lmagan (introspeksiya asosidagi) eksport va
//! birlashtiruvchi import (DESKTOP_PROMPT 6.3). Shifrlash `security::container` da; bu yerda faqat JSON.
//!
//! Qoidalar:
//! - yozuvlar `id` bo'yicha moslashadi; `version` kattasi yutadi, teng bo'lsa `updated_at` kechrog'i;
//!   teng bo'lsa lokal qoladi. `deleted_at` (tombstone) oddiy yangilanish sifatida qo'llanadi;
//! - bir xil `version` bilan turlicha tarkib — ziddiyat (ro'yxatga yoziladi);
//! - yopilgan davr (va uning yozuvlari/taqsimoti), imzolangan shartnoma versiyalari va imzolar
//!   import orqali **o'zgarmaydi**;
//! - standart (seed) yozuvlar (toifalar, «Kelajagim», a'zo «Men», qoida) tabiiy kalit bo'yicha
//!   lokal yozuvga ulanadi, shunda ikkinchi qurilmada dublikat paydo bo'lmaydi;
//! - xonadon identifikatori lokal xonadonga qayta moslanadi.
//!
//! Jadval va ustun nomlari faqat lokal sxemadan (`PRAGMA`) olinadi: SQL'ga hujjatdagi nom tushmaydi.

use std::collections::{BTreeMap, BTreeSet, HashMap};

use domain::{ts_from_str, ts_to_string, OffsetDateTime};
use rusqlite::{types::Value, Connection};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value as Json};

use crate::StorageError;

pub const FORMAT: &str = "baraka-export";
pub const FORMAT_VERSION: u32 = 1;

/// Qurilmaga xos yoki maxfiy jadvallar: PIN xeshlari va qurilma sozlamalari fayl bilan ketmaydi.
const EXCLUDED: [&str; 2] = ["member_credentials", "settings"];

/// Import orqali o'zgarmaydigan (faqat qo'shiladigan) jadvallar.
const IMMUTABLE: [(&str, &str); 3] = [
    ("venture_distributions", "CLOSED_PERIOD"),
    ("partnership_versions", "SIGNED_CONTRACT"),
    ("partnership_signatures", "SIGNED_CONTRACT"),
];

/// Seed yozuvlarni qurilmalar o'rtasida ulash uchun tabiiy kalitlar: (jadval, ustunlar, filtr).
/// (jadval, kalit ustunlari, ixtiyoriy `ustun = qiymat` filtri)
type NaturalKey = (
    &'static str,
    &'static [&'static str],
    Option<(&'static str, &'static str)>,
);

const NATURAL_KEYS: [NaturalKey; 4] = [
    ("categories", &["name"], None),
    ("members", &["display_name", "role"], None),
    (
        "assets",
        &["asset_type", "name", "vault_type"],
        Some(("asset_type", "VAULT")),
    ),
    ("allocation_rules", &["kind", "currency"], None),
];

const NAME_COLS: [&str; 5] = ["name", "description", "display_name", "item", "title"];

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TableDump {
    pub name: String,
    pub rows: Vec<Map<String, Json>>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExportDoc {
    pub format: String,
    pub format_version: u32,
    pub schema_version: u32,
    pub exported_at: String,
    pub device_id: String,
    pub household_id: String,
    /// Inkremental eksportda: shu vaqtdan keyin o'zgargan yozuvlar.
    pub since: Option<String>,
    pub tables: Vec<TableDump>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum ConflictKind {
    /// Bir xil `version`, turlicha tarkib: ikki qurilmada mustaqil tahrir.
    Diverged,
    /// Yopilgan davr o'zgartirilmadi.
    ClosedPeriod,
    /// Imzolangan shartnoma versiyasi/imzosi o'zgartirilmadi.
    SignedContract,
    /// Yozuv bazaga sig'madi (unikal cheklov yoki ota yozuv yo'q); o'tkazib yuborildi.
    Rejected,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum Resolution {
    KeptLocal,
    TookIncoming,
    Skipped,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Conflict {
    pub table: String,
    pub id: String,
    pub kind: ConflictKind,
    pub resolution: Resolution,
    /// Foydalanuvchiga ko'rsatiladigan qisqa nom (summalarsiz).
    pub label: String,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize)]
pub struct ImportReport {
    pub inserted: u32,
    pub updated: u32,
    pub unchanged: u32,
    pub kept_local: u32,
    pub conflicts: Vec<Conflict>,
    /// Xonadondagi `ADULT` a'zolar, ularning PIN'i yo'q (import qilingan kattalar shu ro'yxatda).
    /// PIN'siz kattalar havas chegarasiga rozilik bera olmaydi: avval PIN o'rnatilishi kerak.
    pub adults_without_pin: Vec<String>,
}

struct TableInfo {
    name: String,
    cols: Vec<String>,
    /// (ustun, ota jadval)
    fks: Vec<(String, String)>,
}

fn corrupt(m: impl Into<String>) -> StorageError {
    StorageError::Corrupt(m.into())
}

/// Eksport qilinadigan jadvallar, FK bo'yicha ota-jadval oldin.
fn tables(conn: &Connection) -> Result<Vec<TableInfo>, StorageError> {
    let mut stmt = conn.prepare(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' \
         AND name NOT LIKE '%migration%' ORDER BY name",
    )?;
    let names: Vec<String> = stmt
        .query_map([], |r| r.get(0))?
        .collect::<Result<_, _>>()?;
    let mut infos = Vec::new();
    for name in names {
        if EXCLUDED.contains(&name.as_str()) {
            continue;
        }
        let mut cs = conn.prepare(&format!("PRAGMA table_info(\"{name}\")"))?;
        let cols: Vec<String> = cs.query_map([], |r| r.get(1))?.collect::<Result<_, _>>()?;
        if !["id", "household_id", "version", "updated_at"]
            .iter()
            .all(|c| cols.iter().any(|x| x == c))
        {
            continue;
        }
        let mut fk = conn.prepare(&format!("PRAGMA foreign_key_list(\"{name}\")"))?;
        let fks: Vec<(String, String)> = fk
            .query_map([], |r| Ok((r.get::<_, String>(3)?, r.get::<_, String>(2)?)))?
            .collect::<Result<_, _>>()?;
        infos.push(TableInfo { name, cols, fks });
    }
    // Topologik tartib (ota oldin); o'z-o'ziga havolalar e'tiborsiz.
    let names: BTreeSet<String> = infos.iter().map(|t| t.name.clone()).collect();
    let mut done: Vec<TableInfo> = Vec::new();
    let mut placed: BTreeSet<String> = BTreeSet::new();
    while !infos.is_empty() {
        let before = infos.len();
        let mut rest = Vec::new();
        for t in infos {
            let ready = t
                .fks
                .iter()
                .all(|(_, p)| *p == t.name || placed.contains(p) || !names.contains(p));
            if ready {
                placed.insert(t.name.clone());
                done.push(t);
            } else {
                rest.push(t);
            }
        }
        if rest.len() == before {
            return Err(corrupt("jadvallar orasida FK sikli"));
        }
        infos = rest;
    }
    Ok(done)
}

/// Eksport qilinadigan jadval nomlari (sxema fayli bilan solishtirish uchun).
///
/// # Errors
/// SQL xatosi.
pub fn exported_tables(conn: &Connection) -> Result<Vec<String>, StorageError> {
    Ok(tables(conn)?.into_iter().map(|t| t.name).collect())
}

fn to_json(v: Value) -> Result<Json, StorageError> {
    Ok(match v {
        Value::Null => Json::Null,
        Value::Integer(i) => Json::from(i),
        Value::Text(s) => Json::String(s),
        Value::Blob(b) => {
            let mut m = Map::new();
            m.insert("$blob".into(), Json::String(hex(&b)));
            Json::Object(m)
        }
        Value::Real(_) => return Err(corrupt("kasr son (REAL) eksport qilinmaydi")),
    })
}

fn from_json(v: &Json) -> Result<Value, StorageError> {
    Ok(match v {
        Json::Null => Value::Null,
        Json::Number(n) => Value::Integer(n.as_i64().ok_or_else(|| corrupt("butun son kutilgan"))?),
        Json::String(s) => Value::Text(s.clone()),
        Json::Object(m) => match m.get("$blob") {
            Some(Json::String(h)) if m.len() == 1 => Value::Blob(unhex(h)?),
            _ => return Err(corrupt("qiymat turi noto'g'ri")),
        },
        _ => return Err(corrupt("qiymat turi noto'g'ri")),
    })
}

fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

fn unhex(s: &str) -> Result<Vec<u8>, StorageError> {
    if !s.len().is_multiple_of(2) || !s.is_ascii() {
        return Err(corrupt("hex noto'g'ri"));
    }
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).map_err(|_| corrupt("hex noto'g'ri")))
        .collect()
}

fn parse_ts(s: &str) -> Result<OffsetDateTime, StorageError> {
    ts_from_str(s).map_err(|e| corrupt(e.to_string()))
}

fn dump_row(r: &rusqlite::Row<'_>, cols: &[String]) -> Result<Map<String, Json>, StorageError> {
    let mut m = Map::new();
    for (i, c) in cols.iter().enumerate() {
        m.insert(c.clone(), to_json(r.get::<_, Value>(i)?)?);
    }
    Ok(m)
}

/// Xonadon ma'lumotlarini hujjatga yig'adi. `since` berilsa faqat shundan keyin o'zgarganlar
/// (tombstone'lar ham) kiradi.
///
/// # Errors
/// SQL yoki format xatosi.
pub fn export(
    conn: &Connection,
    household_id: &str,
    device_id: &str,
    now: OffsetDateTime,
    since: Option<OffsetDateTime>,
) -> Result<ExportDoc, StorageError> {
    let mut out = Vec::new();
    for t in tables(conn)? {
        let filter = if t.name == "households" {
            "id = ?1"
        } else {
            "household_id = ?1"
        };
        let sql = format!(
            "SELECT {} FROM \"{}\" WHERE {filter} ORDER BY id",
            t.cols
                .iter()
                .map(|c| format!("\"{c}\""))
                .collect::<Vec<_>>()
                .join(", "),
            t.name
        );
        let mut stmt = conn.prepare(&sql)?;
        let mut rows = stmt.query([household_id])?;
        let mut dumped = Vec::new();
        while let Some(r) = rows.next()? {
            let m = dump_row(r, &t.cols)?;
            if let Some(s) = since {
                let upd = m
                    .get("updated_at")
                    .and_then(Json::as_str)
                    .ok_or_else(|| corrupt("updated_at yo'q"))?;
                if parse_ts(upd)? <= s {
                    continue;
                }
            }
            dumped.push(m);
        }
        out.push(TableDump {
            name: t.name,
            rows: dumped,
        });
    }
    Ok(ExportDoc {
        format: FORMAT.into(),
        format_version: FORMAT_VERSION,
        schema_version: u32::try_from(crate::SCHEMA_VERSION).unwrap_or(u32::MAX),
        exported_at: ts_to_string(now).map_err(|e| corrupt(e.to_string()))?,
        device_id: device_id.to_owned(),
        household_id: household_id.to_owned(),
        since: since
            .map(ts_to_string)
            .transpose()
            .map_err(|e| corrupt(e.to_string()))?,
        tables: out,
    })
}

fn text(m: &Map<String, Json>, k: &str) -> Option<String> {
    m.get(k).and_then(Json::as_str).map(str::to_owned)
}

fn label(m: &Map<String, Json>, table: &str) -> String {
    NAME_COLS
        .iter()
        .find_map(|c| text(m, c))
        .unwrap_or_else(|| table.to_owned())
}

fn local_row(
    conn: &Connection,
    t: &TableInfo,
    id: &str,
) -> Result<Option<Map<String, Json>>, StorageError> {
    let sql = format!(
        "SELECT {} FROM \"{}\" WHERE id = ?1",
        t.cols
            .iter()
            .map(|c| format!("\"{c}\""))
            .collect::<Vec<_>>()
            .join(", "),
        t.name
    );
    let mut stmt = conn.prepare(&sql)?;
    let mut rows = stmt.query([id])?;
    match rows.next()? {
        Some(r) => Ok(Some(dump_row(r, &t.cols)?)),
        None => Ok(None),
    }
}

fn natural_match(
    conn: &Connection,
    t: &TableInfo,
    row: &Map<String, Json>,
    household_id: &str,
    claimed: &BTreeSet<String>,
) -> Result<Option<String>, StorageError> {
    let Some((_, cols, filter)) = NATURAL_KEYS.iter().find(|(n, _, _)| *n == t.name) else {
        return Ok(None);
    };
    if row.get("deleted_at").is_some_and(|v| !v.is_null()) {
        return Ok(None);
    }
    if let Some((c, v)) = filter {
        if row.get(*c).and_then(Json::as_str) != Some(*v) {
            return Ok(None);
        }
    }
    let mut conds = vec![
        "household_id = ?1".to_owned(),
        "deleted_at IS NULL".to_owned(),
    ];
    let mut params: Vec<Value> = vec![Value::Text(household_id.to_owned())];
    for c in *cols {
        if !t.cols.iter().any(|x| x == c) {
            return Ok(None);
        }
        match row.get(*c) {
            Some(Json::Null) | None => conds.push(format!("\"{c}\" IS NULL")),
            // Matn: «Anvar», «anvar», « Anvar » bir xil a'zo deb olinadi (dublikat bo'lmasin).
            Some(Json::String(s)) => {
                params.push(Value::Text(s.trim().to_lowercase()));
                conds.push(format!("lower(trim(\"{c}\")) = ?{}", params.len()));
            }
            Some(v) => {
                params.push(from_json(v)?);
                conds.push(format!("\"{c}\" = ?{}", params.len()));
            }
        }
    }
    let sql = format!(
        "SELECT id FROM \"{}\" WHERE {} ORDER BY id",
        t.name,
        conds.join(" AND ")
    );
    let mut stmt = conn.prepare(&sql)?;
    let ids: Vec<String> = stmt
        .query_map(rusqlite::params_from_iter(params), |r| r.get(0))?
        .collect::<Result<_, _>>()?;
    Ok(ids.into_iter().find(|i| !claimed.contains(i)))
}

fn period_closed(conn: &Connection, period_id: &str) -> Result<bool, StorageError> {
    let s: Option<String> = rusqlite::OptionalExtension::optional(conn.query_row(
        "SELECT status FROM venture_periods WHERE id = ?1",
        [period_id],
        |r| r.get(0),
    ))?;
    Ok(s.as_deref() == Some("CLOSED"))
}

/// Qator yopilgan davrga tegishlimi (lokal holat bo'yicha).
fn in_closed_period(
    conn: &Connection,
    table: &str,
    row: &Map<String, Json>,
) -> Result<bool, StorageError> {
    match table {
        "venture_periods" => match text(row, "id") {
            Some(id) => period_closed(conn, &id),
            None => Ok(false),
        },
        "venture_entries" => match text(row, "period_id") {
            Some(p) => period_closed(conn, &p),
            None => Ok(false),
        },
        "venture_attachments" => {
            let Some(e) = text(row, "entry_id") else {
                return Ok(false);
            };
            let p: Option<String> = rusqlite::OptionalExtension::optional(conn.query_row(
                "SELECT period_id FROM venture_entries WHERE id = ?1",
                [e],
                |r| r.get(0),
            ))?;
            match p {
                Some(p) => period_closed(conn, &p),
                None => Ok(false),
            }
        }
        _ => Ok(false),
    }
}

fn same_content(a: &Map<String, Json>, b: &Map<String, Json>) -> bool {
    a.iter()
        .filter(|(k, _)| *k != "origin_device_id")
        .all(|(k, v)| b.get(k) == Some(v))
        && a.len() == b.len()
}

enum Decision {
    Insert,
    Update,
    Unchanged,
    KeepLocal(Option<ConflictKind>),
    Protected(ConflictKind),
}

fn decide(
    conn: &Connection,
    t: &TableInfo,
    inc: &Map<String, Json>,
    local: Option<&Map<String, Json>>,
) -> Result<Decision, StorageError> {
    let Some(loc) = local else {
        // Yopilgan lokal davrga yangi yozuv qo'shilmaydi.
        return Ok(if in_closed_period(conn, &t.name, inc)? {
            Decision::Protected(ConflictKind::ClosedPeriod)
        } else {
            Decision::Insert
        });
    };
    if same_content(inc, loc) {
        return Ok(Decision::Unchanged);
    }
    if let Some((_, kind)) = IMMUTABLE.iter().find(|(n, _)| *n == t.name) {
        return Ok(Decision::Protected(if *kind == "CLOSED_PERIOD" {
            ConflictKind::ClosedPeriod
        } else {
            ConflictKind::SignedContract
        }));
    }
    if in_closed_period(conn, &t.name, loc)? || in_closed_period(conn, &t.name, inc)? {
        return Ok(Decision::Protected(ConflictKind::ClosedPeriod));
    }
    let ver = |m: &Map<String, Json>| m.get("version").and_then(Json::as_i64);
    let (Some(iv), Some(lv)) = (ver(inc), ver(loc)) else {
        return Err(corrupt("version yo'q"));
    };
    let ts = |m: &Map<String, Json>| -> Result<OffsetDateTime, StorageError> {
        parse_ts(&text(m, "updated_at").ok_or_else(|| corrupt("updated_at yo'q"))?)
    };
    let (iu, lu) = (ts(inc)?, ts(loc)?);
    // Versiya teng bo'lsa vaqt hal qiladi; ikkala holatda ham ziddiyat `apply` da qayd etiladi.
    Ok(if (iv, iu) > (lv, lu) {
        Decision::Update
    } else {
        Decision::KeepLocal((iv == lv).then_some(ConflictKind::Diverged))
    })
}

fn write_row(
    conn: &Connection,
    t: &TableInfo,
    row: &Map<String, Json>,
    update: bool,
) -> Result<(), StorageError> {
    let cols: Vec<&String> = t.cols.iter().filter(|c| row.contains_key(*c)).collect();
    let mut vals = Vec::new();
    for c in &cols {
        vals.push(from_json(&row[*c])?);
    }
    if update {
        let sets = cols
            .iter()
            .enumerate()
            .filter(|(_, c)| c.as_str() != "id")
            .map(|(i, c)| format!("\"{c}\" = ?{}", i + 1))
            .collect::<Vec<_>>()
            .join(", ");
        let id_pos = cols
            .iter()
            .position(|c| c.as_str() == "id")
            .ok_or_else(|| corrupt("id yo'q"))?;
        conn.execute(
            &format!(
                "UPDATE \"{}\" SET {sets} WHERE id = ?{}",
                t.name,
                id_pos + 1
            ),
            rusqlite::params_from_iter(vals),
        )?;
    } else {
        let names = cols
            .iter()
            .map(|c| format!("\"{c}\""))
            .collect::<Vec<_>>()
            .join(", ");
        let ph = (1..=cols.len())
            .map(|i| format!("?{i}"))
            .collect::<Vec<_>>()
            .join(", ");
        conn.execute(
            &format!("INSERT INTO \"{}\" ({names}) VALUES ({ph})", t.name),
            rusqlite::params_from_iter(vals),
        )?;
    }
    Ok(())
}

/// Hujjatni qo'llaydi. **Tranzaksiya ichida chaqiring** (oldindan ko'rish uchun orqaga qaytariladi,
/// qo'llash uchun commit qilinadi: ikkala holatda hisobot bir xil).
///
/// # Errors
/// Hujjat noto'g'ri/yangi format yoki SQL xatosi (bunda hech narsa saqlanmaydi).
pub fn apply(
    conn: &Connection,
    doc: &ExportDoc,
    local_household: Option<&str>,
) -> Result<ImportReport, StorageError> {
    if doc.format != FORMAT {
        return Err(corrupt("bu .baraka eksport fayli emas"));
    }
    if doc.format_version > FORMAT_VERSION
        || usize::try_from(doc.schema_version).unwrap_or(usize::MAX) > crate::SCHEMA_VERSION
    {
        return Err(corrupt("fayl yangiroq versiyada: ilovani yangilang"));
    }
    let infos = tables(conn)?;
    let by_name: HashMap<&str, &TableInfo> = infos.iter().map(|t| (t.name.as_str(), t)).collect();
    for d in &doc.tables {
        if !by_name.contains_key(d.name.as_str()) {
            return Err(corrupt("noma'lum jadval hujjatda"));
        }
    }
    let target_household = local_household.unwrap_or(&doc.household_id).to_owned();
    let mut id_map: HashMap<(String, String), String> = HashMap::new();
    id_map.insert(
        ("households".into(), doc.household_id.clone()),
        target_household.clone(),
    );
    let mut claimed: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let mut to_close: Vec<(String, Map<String, Json>)> = Vec::new();
    let mut report = ImportReport::default();
    let dumps: HashMap<&str, &TableDump> =
        doc.tables.iter().map(|d| (d.name.as_str(), d)).collect();

    for t in &infos {
        let Some(dump) = dumps.get(t.name.as_str()) else {
            continue;
        };
        for raw in &dump.rows {
            let Some(inc_id) = text(raw, "id") else {
                return Err(corrupt("yozuvda id yo'q"));
            };
            if raw.keys().any(|k| !t.cols.contains(k)) {
                return Err(corrupt("yozuvda noma'lum ustun"));
            }
            // Xonadonning o'zi: lokal xonadon bor bo'lsa, hujjatdagisi o'tkazib yuboriladi.
            if t.name == "households" && local_household.is_some() {
                report.unchanged += 1;
                continue;
            }
            let mut row = raw.clone();
            if row.contains_key("household_id") && t.name != "households" {
                row.insert(
                    "household_id".into(),
                    Json::String(target_household.clone()),
                );
            }
            for (col, parent) in &t.fks {
                if let Some(Json::String(v)) = row.get(col) {
                    if let Some(m) = id_map.get(&(parent.clone(), v.clone())) {
                        row.insert(col.clone(), Json::String(m.clone()));
                    }
                }
            }
            let mut local = local_row(conn, t, &inc_id)?;
            if local.is_none() {
                let taken = claimed.entry(t.name.clone()).or_default();
                if let Some(lid) = natural_match(conn, t, &row, &target_household, taken)? {
                    taken.insert(lid.clone());
                    local = local_row(conn, t, &lid)?;
                    id_map.insert((t.name.clone(), inc_id.clone()), lid.clone());
                    // Tabiiy kalit ustunlari lokal qiymatga tenglashtiriladi: «anvar» ↔ «Anvar»
                    // faqat registr farqi ziddiyat hisoblanmasin.
                    if let (Some(loc), Some((_, keys, _))) = (
                        local.as_ref(),
                        NATURAL_KEYS.iter().find(|(n, _, _)| *n == t.name),
                    ) {
                        for k in keys.iter() {
                            if let Some(v) = loc.get(*k) {
                                row.insert((*k).to_owned(), v.clone());
                            }
                        }
                    }
                    row.insert("id".into(), Json::String(lid));
                }
            }
            let lbl = label(&row, &t.name);
            let conflict = |kind, resolution| Conflict {
                table: t.name.clone(),
                id: inc_id.clone(),
                kind,
                resolution,
                label: lbl.clone(),
            };
            match decide(conn, t, &row, local.as_ref())? {
                Decision::Unchanged => report.unchanged += 1,
                Decision::KeepLocal(c) => {
                    report.kept_local += 1;
                    if let Some(k) = c {
                        report.conflicts.push(conflict(k, Resolution::KeptLocal));
                    }
                }
                Decision::Protected(k) => {
                    report.kept_local += 1;
                    report.conflicts.push(conflict(k, Resolution::KeptLocal));
                }
                d @ (Decision::Insert | Decision::Update) => {
                    let update = matches!(d, Decision::Update);
                    let mut to_write = row.clone();
                    // Yopiladigan davr: bolalari yozilgach oxirida yopiladi (DB triggerlari).
                    let closing = t.name == "venture_periods"
                        && to_write.get("status") == Some(&Json::String("CLOSED".into()));
                    if closing {
                        to_write.insert("status".into(), Json::String("OPEN".into()));
                    }
                    conn.execute_batch("SAVEPOINT imp_row")?;
                    match write_row(conn, t, &to_write, update) {
                        Ok(()) => {
                            conn.execute_batch("RELEASE imp_row")?;
                            if closing {
                                to_close.push((t.name.clone(), row.clone()));
                            }
                            if update {
                                report.updated += 1;
                                if matches!(
                                    local
                                        .as_ref()
                                        .map(|l| l.get("version") == row.get("version")),
                                    Some(true)
                                ) {
                                    report.conflicts.push(conflict(
                                        ConflictKind::Diverged,
                                        Resolution::TookIncoming,
                                    ));
                                }
                            } else {
                                report.inserted += 1;
                            }
                        }
                        Err(StorageError::Sqlite(_)) => {
                            conn.execute_batch("ROLLBACK TO imp_row; RELEASE imp_row")?;
                            report
                                .conflicts
                                .push(conflict(ConflictKind::Rejected, Resolution::Skipped));
                        }
                        Err(e) => {
                            conn.execute_batch("ROLLBACK TO imp_row; RELEASE imp_row")?;
                            return Err(e);
                        }
                    }
                }
            }
        }
    }
    for (name, row) in to_close {
        if let Some(t) = by_name.get(name.as_str()) {
            write_row(conn, t, &row, true)?;
        }
    }
    report.adults_without_pin = adults_without_pin(conn, &target_household)?;
    Ok(report)
}

/// Xonadondagi faol `ADULT` a'zolar, PIN (`member_credentials`) yozuvi yo'q bo'lganlari.
fn adults_without_pin(conn: &Connection, household_id: &str) -> Result<Vec<String>, StorageError> {
    let mut stmt = conn.prepare(
        "SELECT m.display_name FROM members m \
         WHERE m.household_id = ?1 AND m.role = 'ADULT' AND m.deleted_at IS NULL \
           AND NOT EXISTS (SELECT 1 FROM member_credentials c \
                           WHERE c.member_id = m.id AND c.deleted_at IS NULL) \
         ORDER BY m.display_name",
    )?;
    let names = stmt
        .query_map([household_id], |r| r.get::<_, String>(0))?
        .collect::<Result<_, _>>()?;
    Ok(names)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Database;

    #[test]
    fn schema_file_lists_exactly_the_exported_tables() {
        let db = Database::open_in_memory(&[3; 32]).unwrap();
        let schema: Json = serde_json::from_str(include_str!(
            "../../../../spec/interchange/export-format.schema.json"
        ))
        .unwrap();
        let listed: Vec<String> = schema["$defs"]["tableName"]["enum"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_str().unwrap().to_owned())
            .collect();
        let mut actual = exported_tables(db.conn()).unwrap();
        let mut listed_sorted = listed;
        actual.sort();
        listed_sorted.sort();
        assert_eq!(listed_sorted, actual, "spec/interchange sxemasi eskirgan");
        assert_eq!(
            schema["properties"]["format_version"]["const"],
            FORMAT_VERSION
        );
        assert_eq!(
            schema["properties"]["schema_version"]["maximum"],
            crate::SCHEMA_VERSION
        );
    }

    #[test]
    fn example_file_parses() {
        let doc: ExportDoc = serde_json::from_str(include_str!(
            "../../../../spec/interchange/example-export.json"
        ))
        .unwrap();
        assert_eq!(doc.format, FORMAT);
        assert_eq!(doc.tables[0].name, "households");
    }
}
