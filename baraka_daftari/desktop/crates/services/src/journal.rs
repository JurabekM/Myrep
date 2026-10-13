//! Kelishuv jurnali (SPEC 2F.6): faqat qo'shiladigan yozuvlar, xesh-zanjir va tekshiruv.
//!
//! - Yozuvni faqat kelishuvning **hisob yurituvchi qurilmasi** qo'shadi (`keeper_device_id`, OPEN_QUESTIONS 91).
//!   Boshqa qurilmada jurnal faqat o'qish uchun turadi.
//! - O'chirish va tahrirlash yo'q: tuzatish `CORRECTION` yozuvi bilan qilinadi (OPEN_QUESTIONS 89). DB triggerlari
//!   buni baribir rad etadi.
//! - `verify` zanjirni qayta hisoblaydi va birinchi buzilgan yozuvning tartib raqamini qaytaradi.
use domain::{
    date_to_string, entry_hash, first_broken, Agreement, Date, HashedEntry, JournalEntry,
    JournalKind, Meta, GENESIS_HASH,
};
use money::Money;
use storage::{repo, Connection};

use crate::{Ctx, Env, ServiceError};

const MAX_NOTE_CHARS: usize = 300;

/// Yangi yozuv ma'lumoti. `corrects` faqat `CORRECTION` uchun (asl yozuv id si).
#[derive(Debug, Clone)]
pub struct NewEntry<'a> {
    pub kind: JournalKind,
    pub party_id: Option<&'a str>,
    pub amount: Option<Money>,
    pub date: Date,
    pub note: &'a str,
    pub reference: Option<&'a str>,
    pub corrects: Option<&'a str>,
}

/// Zanjir holati: yozuvlar soni, oxirgi xesh va birinchi buzilgan tartib raqami (bo'lsa).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ChainCheck {
    pub length: usize,
    pub head: String,
    pub broken_seq: Option<u32>,
}

/// Kelishuvning barcha yozuvlari, tartib raqami bo'yicha.
///
/// # Errors
/// Baza xatosi.
pub fn entries(
    conn: &Connection,
    ctx: &Ctx,
    agreement_id: &str,
) -> Result<Vec<JournalEntry>, ServiceError> {
    let mut v: Vec<JournalEntry> = repo::list::<JournalEntry>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|e| e.agreement_id == agreement_id)
        .collect();
    v.sort_by_key(|e| e.seq);
    Ok(v)
}

/// Yangi yozuvni qo'shadi. Tranzaksiya ichida chaqiriladi (tashqi amal bilan birga yoziladi).
///
/// # Errors
/// Qurilma hisob yurituvchi emas, izoh yoki summa yaroqsiz, tuzatish asl yozuvsiz yoki noto'g'ri.
pub fn append(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    agreement: &Agreement,
    new: NewEntry<'_>,
) -> Result<JournalEntry, ServiceError> {
    if agreement.keeper_device_id.as_deref() != Some(env.device_id) {
        return Err(ServiceError::Invalid(
            "bu kelishuv jurnaliga faqat hisob yurituvchi qurilma yozadi",
        ));
    }
    let note = new.note.split_whitespace().collect::<Vec<_>>().join(" ");
    if note.is_empty() || note.chars().count() > MAX_NOTE_CHARS {
        return Err(ServiceError::Invalid(
            "jurnal izohi 1 dan 300 belgigacha bo'lsin",
        ));
    }
    if let Some(a) = new.amount {
        if a.currency() != ctx.currency || a.minor() < 0 {
            return Err(ServiceError::Invalid(
                "jurnal summasi musbat va asosiy valyutada bo'lsin",
            ));
        }
    }
    let existing = entries(conn, ctx, &agreement.meta.id)?;
    match (new.kind, new.corrects) {
        (JournalKind::Correction, None) => {
            return Err(ServiceError::Invalid(
                "tuzatish asl yozuvga havola qilishi kerak",
            ));
        }
        (JournalKind::Correction, Some(orig)) => {
            if !existing.iter().any(|e| e.meta.id == orig) {
                return Err(ServiceError::NotFound);
            }
        }
        (_, Some(_)) => {
            return Err(ServiceError::Invalid(
                "faqat tuzatish yozuvi asl yozuvga havola qiladi",
            ));
        }
        (_, None) => {}
    }
    let seq =
        u32::try_from(existing.len() + 1).map_err(|_| ServiceError::Invalid("jurnal juda uzun"))?;
    let prev_hash = existing
        .last()
        .map_or_else(|| GENESIS_HASH.to_owned(), |e| e.hash.clone());
    let meta = Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id);
    let hashed = HashedEntry {
        id: meta.id.clone(),
        agreement_id: agreement.meta.id.clone(),
        kind: new.kind,
        party_id: new.party_id.map(str::to_owned),
        amount: new.amount,
        date: date_to_string(new.date)
            .map_err(|_| ServiceError::Invalid("jurnal sanasi noto'g'ri"))?,
        note: note.clone(),
        reference: new.reference.map(str::to_owned),
        corrects: new.corrects.map(str::to_owned),
    };
    let hash = entry_hash(&prev_hash, &hashed)
        .map_err(|_| ServiceError::Invalid("jurnal mazmuni yaroqsiz"))?;
    let entry = JournalEntry {
        meta,
        agreement_id: agreement.meta.id.clone(),
        seq,
        kind: new.kind,
        party_id: hashed.party_id,
        amount: new.amount,
        entry_date: new.date,
        note,
        reference: hashed.reference,
        corrects: hashed.corrects,
        prev_hash,
        hash,
    };
    repo::insert(conn, &entry)?;
    Ok(entry)
}

/// Zanjirni qayta hisoblaydi: tartib raqamlari, bog'lanish (`prev_hash`) va xeshlar.
///
/// # Errors
/// Baza yoki xeshlash xatosi.
pub fn verify(
    conn: &Connection,
    ctx: &Ctx,
    agreement_id: &str,
) -> Result<ChainCheck, ServiceError> {
    let list = entries(conn, ctx, agreement_id)?;
    let mut pairs = Vec::with_capacity(list.len());
    let mut broken: Option<u32> = None;
    let mut prev = GENESIS_HASH.to_owned();
    for (i, e) in list.iter().enumerate() {
        let expected_seq = u32::try_from(i + 1).unwrap_or(u32::MAX);
        if e.seq != expected_seq || e.prev_hash != prev {
            broken = Some(expected_seq);
            break;
        }
        prev.clone_from(&e.hash);
        let hashed = e
            .hashed()
            .map_err(|_| ServiceError::Invalid("jurnal sanasi buzilgan"))?;
        pairs.push((hashed, e.hash.clone()));
    }
    if let Some(i) =
        first_broken(&pairs).map_err(|_| ServiceError::Invalid("jurnal mazmuni yaroqsiz"))?
    {
        let seq = u32::try_from(i).unwrap_or(u32::MAX);
        broken = Some(broken.map_or(seq, |b| b.min(seq)));
    }
    Ok(ChainCheck {
        length: list.len(),
        head: list
            .last()
            .map_or_else(|| GENESIS_HASH.to_owned(), |e| e.hash.clone()),
        broken_seq: broken,
    })
}
