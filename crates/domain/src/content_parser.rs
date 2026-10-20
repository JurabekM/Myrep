//! `chapters.json` ni o'qiydi va tekshiradi. Sxema: `spec/content/content_schema.json` (mobil bilan bir xil).
//!
//! Qoida: hech qachon istisno tashlamaydi. Buzuq bob o'tkazib yuboriladi va sababi
//! [`ContentLoadResult::errors`] ga yoziladi; butun fayl buzuq bo'lsa — bo'sh natija.

use std::collections::{BTreeMap, BTreeSet};

use serde_json::{Map, Value};

use crate::content::{
    Chapter, ContentBlock, ContentLoadResult, LANG_RU, LANG_UZ, Law, LocalizedText,
    ReligiousReviewStatus, TaskTrigger, WeeklyTask,
};

/// Qo'llab-quvvatlanadigan sxema versiyasi.
pub const SUPPORTED_SCHEMA_VERSION: i64 = 1;
/// Har bobdagi haftalik vazifalar soni (aniq).
pub const TASKS_PER_CHAPTER: usize = 3;

/// Kontent JSON matnini o'qiydi. Natija har doim qaytadi (istisno yo'q).
pub fn parse(source: &str) -> ContentLoadResult {
    let root: Value = match serde_json::from_str(source) {
        Ok(root) => root,
        Err(error) => return fatal(format!("json: {error}")),
    };
    let Some(root) = root.as_object() else {
        return fatal("root: obyekt emas".to_owned());
    };
    let version = root.get("schemaVersion").and_then(Value::as_i64);
    if version != Some(SUPPORTED_SCHEMA_VERSION) {
        let shown = root
            .get("schemaVersion")
            .map_or_else(|| "yo'q".to_owned(), Value::to_string);
        return fatal(format!("schemaVersion: {shown} qo'llanmaydi"));
    }
    let Some(list) = root.get("chapters").and_then(Value::as_array) else {
        return fatal("chapters: ro'yxat emas".to_owned());
    };

    let mut errors = Vec::new();
    let mut chapters = Vec::new();
    let mut ids = BTreeSet::new();
    let mut orders = BTreeSet::new();
    let mut task_ids = BTreeSet::new();
    for (index, raw) in list.iter().enumerate() {
        let parsed = chapter(raw).and_then(|chapter| {
            check_unique(&chapter, &ids, &orders, &task_ids)?;
            Ok(chapter)
        });
        match parsed {
            Ok(chapter) => {
                ids.insert(chapter.id.clone());
                orders.insert(chapter.order);
                task_ids.extend(chapter.weekly_tasks.iter().map(|task| task.id.clone()));
                chapters.push(chapter);
            }
            Err(message) => errors.push(format!("chapters[{index}]: {message}")),
        }
    }
    chapters.sort_by_key(|chapter| chapter.order);
    ContentLoadResult { chapters, errors }
}

fn fatal(message: String) -> ContentLoadResult {
    ContentLoadResult {
        chapters: Vec::new(),
        errors: vec![message],
    }
}

/// Bob takrorlanmasligini tekshiradi: id, order va vazifa id'lari butun kontentda yagona.
fn check_unique(
    chapter: &Chapter,
    ids: &BTreeSet<String>,
    orders: &BTreeSet<u32>,
    task_ids: &BTreeSet<String>,
) -> Result<(), String> {
    if ids.contains(&chapter.id) {
        return Err(format!("id takrorlangan: {}", chapter.id));
    }
    if orders.contains(&chapter.order) {
        return Err(format!("order takrorlangan: {}", chapter.order));
    }
    for task in &chapter.weekly_tasks {
        if task_ids.contains(&task.id) {
            return Err(format!("vazifa id takrorlangan: {}", task.id));
        }
    }
    Ok(())
}

fn chapter(raw: &Value) -> Result<Chapter, String> {
    let m = object(Some(raw), "bob")?;
    let id = string(m, "id")?;
    if !is_slug(id) {
        return Err(format!("id noto'g'ri: {id}"));
    }
    let order = u32::try_from(int(m, "order")?)
        .ok()
        .filter(|order| *order >= 1)
        .ok_or_else(|| "order ≥ 1 bo'lishi kerak".to_owned())?;
    let blocks = list(m, "blocks")?
        .iter()
        .map(|raw| block(Some(raw)))
        .collect::<Result<Vec<_>, _>>()?;
    if blocks.is_empty() {
        return Err("blocks bo'sh".to_owned());
    }
    let tasks = list(m, "weeklyTasks")?
        .iter()
        .map(|raw| task(Some(raw)))
        .collect::<Result<Vec<_>, _>>()?;
    if tasks.len() != TASKS_PER_CHAPTER {
        return Err(format!(
            "weeklyTasks aniq {TASKS_PER_CHAPTER} ta bo'lishi kerak: {}",
            tasks.len()
        ));
    }
    for task in &tasks {
        if !task.id.starts_with(&format!("{id}.")) {
            return Err(format!(
                "vazifa id bob id bilan boshlanishi kerak: {}",
                task.id
            ));
        }
    }
    let audio_url = match m.get("audioUrl") {
        None | Some(Value::Null) => None,
        Some(Value::String(url)) if url.starts_with("https://") && url.len() > "https://".len() => {
            Some(url.clone())
        }
        Some(_) => return Err("audioUrl https bo'lishi kerak".to_owned()),
    };
    let law_map = object(m.get("law"), "law")?;
    let law_number = u32::try_from(int(law_map, "number")?)
        .map_err(|_| "law.number manfiy bo'lishi mumkin emas".to_owned())?;
    Ok(Chapter {
        id: id.to_owned(),
        order,
        title: localized(m.get("title"), "title")?,
        blocks,
        law: Law {
            number: law_number,
            text: localized(law_map.get("text"), "law.text")?,
        },
        weekly_tasks: tasks,
        audio_url,
    })
}

fn block(raw: Option<&Value>) -> Result<ContentBlock, String> {
    let m = object(raw, "blok")?;
    match m.get("type").and_then(Value::as_str) {
        Some("paragraph") => Ok(ContentBlock::Paragraph(localized(
            m.get("text"),
            "paragraph.text",
        )?)),
        Some("quote") => Ok(ContentBlock::Quote(localized(m.get("text"), "quote.text")?)),
        Some("religious") => {
            let status = match m.get("religiousReviewStatus").and_then(Value::as_str) {
                Some("APPROVED") => ReligiousReviewStatus::Approved,
                Some("PENDING") => ReligiousReviewStatus::Pending,
                other => {
                    return Err(format!(
                        "religiousReviewStatus noto'g'ri: {}",
                        other.unwrap_or("yo'q")
                    ));
                }
            };
            Ok(ContentBlock::Religious {
                text: localized(m.get("text"), "religious.text")?,
                source: localized(m.get("source"), "religious.source")?,
                status,
            })
        }
        other => Err(format!("blok turi noma'lum: {}", other.unwrap_or("yo'q"))),
    }
}

fn task(raw: Option<&Value>) -> Result<WeeklyTask, String> {
    let m = object(raw, "vazifa")?;
    let id = string(m, "id")?;
    if !is_task_id(id) {
        return Err(format!("vazifa id noto'g'ri: {id}"));
    }
    let trigger = match m.get("autoComplete") {
        None | Some(Value::Null) => None,
        Some(Value::String(code)) => Some(
            TaskTrigger::from_code(code).ok_or_else(|| format!("autoComplete noma'lum: {code}"))?,
        ),
        Some(other) => return Err(format!("autoComplete noma'lum: {other}")),
    };
    Ok(WeeklyTask {
        id: id.to_owned(),
        text: localized(m.get("text"), "task.text")?,
        trigger,
    })
}

/// Ko'p tilli matn: faqat `uz` va `ru` kalitlari, bo'sh bo'lmagan qiymatlar, `uz` majburiy.
fn localized(raw: Option<&Value>, field: &str) -> Result<LocalizedText, String> {
    let map = object(raw, field)?;
    let mut values = BTreeMap::new();
    for (language, value) in map {
        if language != LANG_UZ && language != LANG_RU {
            return Err(format!("{field}: til noma'lum: {language}"));
        }
        match value.as_str() {
            Some(text) if !text.trim().is_empty() => {
                values.insert(language.clone(), text.to_owned());
            }
            _ => return Err(format!("{field}.{language}: bo'sh")),
        }
    }
    LocalizedText::new(values).ok_or_else(|| format!("{field}: uz majburiy"))
}

fn object<'a>(raw: Option<&'a Value>, field: &str) -> Result<&'a Map<String, Value>, String> {
    raw.and_then(Value::as_object)
        .ok_or_else(|| format!("{field}: obyekt emas"))
}

fn list<'a>(m: &'a Map<String, Value>, key: &str) -> Result<&'a Vec<Value>, String> {
    m.get(key)
        .and_then(Value::as_array)
        .ok_or_else(|| format!("{key}: ro'yxat emas"))
}

fn string<'a>(m: &'a Map<String, Value>, key: &str) -> Result<&'a str, String> {
    m.get(key)
        .and_then(Value::as_str)
        .filter(|text| !text.is_empty())
        .ok_or_else(|| format!("{key}: matn emas"))
}

fn int(m: &Map<String, Value>, key: &str) -> Result<i64, String> {
    m.get(key)
        .and_then(Value::as_i64)
        .ok_or_else(|| format!("{key}: butun son emas"))
}

/// `[a-z0-9]+` — bob identifikatori.
fn is_slug(text: &str) -> bool {
    !text.is_empty()
        && text
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit())
}

/// `<bob>.t1|t2|t3` — haftalik vazifa identifikatori.
fn is_task_id(text: &str) -> bool {
    match text.rsplit_once('.') {
        Some((chapter, task)) => is_slug(chapter) && matches!(task, "t1" | "t2" | "t3"),
        None => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Bitta to'g'ri bobli minimal kontent; testlar uning bir qismini buzadi.
    fn minimal(chapter_body: &str) -> String {
        format!(r#"{{"schemaVersion":1,"chapters":[{chapter_body}]}}"#)
    }

    fn chapter_json(id: &str, order: u32, tasks: &str) -> String {
        format!(
            r#"{{"id":"{id}","order":{order},"title":{{"uz":"{order}-bob"}},
            "blocks":[{{"type":"paragraph","text":{{"uz":"Matn"}}}}],
            "law":{{"number":{order},"text":{{"uz":"Qonun"}}}},
            "weeklyTasks":[{tasks}]}}"#
        )
    }

    fn three_tasks(prefix: &str) -> String {
        format!(
            r#"{{"id":"{prefix}.t1","text":{{"uz":"A"}},"autoComplete":"VAULT_OPENED"}},
            {{"id":"{prefix}.t2","text":{{"uz":"B"}}}},
            {{"id":"{prefix}.t3","text":{{"uz":"C"}},"autoComplete":"AUDIT_COMPLETED"}}"#
        )
    }

    #[test]
    fn haqiqiy_kontent_xatosiz_yuklanadi() {
        let result = parse(include_str!("../../../spec/content/chapters.json"));
        assert!(result.errors.is_empty(), "xatolar: {:?}", result.errors);
        assert_eq!(result.chapters.len(), 7);
        let orders: Vec<u32> = result.chapters.iter().map(|c| c.order).collect();
        assert_eq!(orders, vec![1, 2, 3, 4, 5, 6, 7]);
        for chapter in &result.chapters {
            assert_eq!(chapter.weekly_tasks.len(), TASKS_PER_CHAPTER);
        }
    }

    #[test]
    fn haqiqiy_kontentda_diniy_bloklar_pending() {
        let result = parse(include_str!("../../../spec/content/chapters.json"));
        let religious: Vec<ReligiousReviewStatus> = result
            .chapters
            .iter()
            .flat_map(|chapter| chapter.blocks.iter())
            .filter_map(|block| match block {
                ContentBlock::Religious { status, .. } => Some(*status),
                _ => None,
            })
            .collect();
        assert_eq!(religious.len(), 7);
        assert!(
            religious
                .iter()
                .all(|s| *s == ReligiousReviewStatus::Pending)
        );
    }

    #[test]
    fn noto_gri_versiya_bosh_natija_beradi() {
        let result = parse(r#"{"schemaVersion":2,"chapters":[]}"#);
        assert!(result.chapters.is_empty());
        assert_eq!(
            result.errors,
            vec!["schemaVersion: 2 qo'llanmaydi".to_owned()]
        );
    }

    #[test]
    fn buzuq_json_istisno_bermaydi() {
        let result = parse("{nosoz");
        assert!(result.chapters.is_empty());
        assert_eq!(result.errors.len(), 1);
    }

    #[test]
    fn bitta_buzuq_bob_otkazib_yuboriladi() {
        let good = chapter_json("ch01", 1, &three_tasks("ch01"));
        let bad = chapter_json("ch02", 2, &three_tasks("ch02")).replace(
            r#""autoComplete":"AUDIT_COMPLETED""#,
            r#""autoComplete":"NOMA_LUM""#,
        );
        let result = parse(&format!(
            r#"{{"schemaVersion":1,"chapters":[{good},{bad}]}}"#
        ));
        assert_eq!(result.chapters.len(), 1);
        assert_eq!(result.chapters[0].id, "ch01");
        assert_eq!(result.errors.len(), 1);
        assert!(result.errors[0].starts_with("chapters[1]: autoComplete noma'lum"));
    }

    #[test]
    fn takroriy_bob_idsi_rad_etiladi() {
        let first = chapter_json("ch01", 1, &three_tasks("ch01"));
        let again = chapter_json("ch01", 2, &three_tasks("ch01"));
        let result = parse(&format!(
            r#"{{"schemaVersion":1,"chapters":[{first},{again}]}}"#
        ));
        assert_eq!(result.chapters.len(), 1);
        assert!(result.errors[0].contains("id takrorlangan"));
    }

    #[test]
    fn vazifa_idsi_bob_idsi_bilan_boshlanmasa_rad_etiladi() {
        let bad = chapter_json("ch01", 1, &three_tasks("ch09"));
        let result = parse(&minimal(&bad));
        assert!(result.chapters.is_empty());
        assert!(result.errors[0].contains("bob id bilan boshlanishi kerak"));
    }

    #[test]
    fn uch_dan_kam_vazifa_rad_etiladi() {
        let two = r#"{"id":"ch01.t1","text":{"uz":"A"}},{"id":"ch01.t2","text":{"uz":"B"}}"#;
        let result = parse(&minimal(&chapter_json("ch01", 1, two)));
        assert!(result.chapters.is_empty());
        assert!(result.errors[0].contains("aniq 3 ta"));
    }

    #[test]
    fn https_bolmagan_audio_rad_etiladi() {
        let body = chapter_json("ch01", 1, &three_tasks("ch01"))
            .replace(r#""title""#, r#""audioUrl":"http://x.uz/a.mp3","title""#);
        let result = parse(&minimal(&body));
        assert!(result.errors[0].contains("audioUrl https"));
    }

    #[test]
    fn uz_bolmagan_matn_rad_etiladi() {
        let body = chapter_json("ch01", 1, &three_tasks("ch01"))
            .replace(r#""title":{"uz":"1-bob"}"#, r#""title":{"ru":"1-глава"}"#);
        let result = parse(&minimal(&body));
        assert!(result.errors[0].contains("uz majburiy"));
    }

    #[test]
    fn noma_lum_til_rad_etiladi() {
        let body = chapter_json("ch01", 1, &three_tasks("ch01")).replace(
            r#""title":{"uz":"1-bob"}"#,
            r#""title":{"uz":"1-bob","en":"x"}"#,
        );
        let result = parse(&minimal(&body));
        assert!(result.errors[0].contains("til noma'lum: en"));
    }

    #[test]
    fn diniy_blok_holati_majburiy() {
        let body = chapter_json("ch01", 1, &three_tasks("ch01")).replace(
            r#""blocks":[{"type":"paragraph","text":{"uz":"Matn"}}]"#,
            r#""blocks":[{"type":"religious","text":{"uz":"Oyat"},"source":{"uz":"Manba"}}]"#,
        );
        let result = parse(&minimal(&body));
        assert!(result.errors[0].contains("religiousReviewStatus noto'g'ri"));
    }

    #[test]
    fn slug_va_vazifa_idlari_tekshiriladi() {
        assert!(is_slug("ch01"));
        assert!(!is_slug("Ch01"));
        assert!(!is_slug("ch-01"));
        assert!(is_task_id("ch01.t3"));
        assert!(!is_task_id("ch01.t4"));
        assert!(!is_task_id("ch01t1"));
    }
}
