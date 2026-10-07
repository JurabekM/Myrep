use std::{collections::HashSet, sync::OnceLock};

use crate::{Block, Chapter, ReviewStatus};

/// Har bobda aniq shuncha haftalik vazifa (SPEC 1.1).
pub const TASKS_PER_CHAPTER: usize = 3;

#[derive(Debug, Clone, thiserror::Error, PartialEq, Eq)]
pub enum ContentError {
    #[error("kontent JSON noto'g'ri ({file}): {message}")]
    Json { file: String, message: String },
    #[error("kontent tekshiruvidan o'tmadi: {}", .0.join("; "))]
    Invalid(Vec<String>),
}

/// Diniy matnlar qaysi rejimda ko'rsatiladi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReleaseMode {
    /// Tasdiqlanmagan (`PENDING`) diniy bloklar **chiqmaydi**.
    Release,
    /// Ishlab chiqish: `PENDING` bloklar «tekshirilmagan» belgisi bilan chiqadi.
    Dev,
}

impl ReleaseMode {
    /// Debug build — `Dev`, release build — `Release`.
    #[must_use]
    pub const fn for_build() -> Self {
        if cfg!(debug_assertions) {
            Self::Dev
        } else {
            Self::Release
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VisibleBlock {
    pub id: String,
    pub text: String,
    /// Diniy blokda manba.
    pub source: Option<String>,
    /// `true` — ulamo tekshiruvidan o'tmagan (faqat `Dev` rejimida ko'rinadi).
    pub unreviewed: bool,
}

#[derive(Debug, Clone)]
pub struct Catalog {
    chapters: Vec<Chapter>,
}

const BUNDLED: [(&str, &str); 5] = [
    ("ch01.json", include_str!("../../../../content/ch01.json")),
    ("ch02.json", include_str!("../../../../content/ch02.json")),
    ("ch03.json", include_str!("../../../../content/ch03.json")),
    ("ch04.json", include_str!("../../../../content/ch04.json")),
    ("ch05.json", include_str!("../../../../content/ch05.json")),
];

impl Catalog {
    /// JSON matnlaridan yuklaydi, tartiblaydi va tekshiradi.
    ///
    /// # Errors
    /// JSON noto'g'ri yoki kontent qoidalarini buzsa.
    pub fn load<'a>(
        files: impl IntoIterator<Item = (&'a str, &'a str)>,
    ) -> Result<Self, ContentError> {
        let mut chapters = files
            .into_iter()
            .map(|(name, text)| {
                serde_json::from_str::<Chapter>(text).map_err(|e| ContentError::Json {
                    file: name.to_owned(),
                    message: e.to_string(),
                })
            })
            .collect::<Result<Vec<_>, _>>()?;
        chapters.sort_by_key(|c| c.order);
        let problems = validate(&chapters);
        if problems.is_empty() {
            Ok(Self { chapters })
        } else {
            Err(ContentError::Invalid(problems))
        }
    }

    /// Ilovaga o'rnatilgan kontent (jarayon bo'yi bir marta yuklanadi).
    ///
    /// # Errors
    /// O'rnatilgan kontent yaroqsiz bo'lsa (CI testi bunga yo'l qo'ymaydi).
    pub fn bundled() -> Result<&'static Self, ContentError> {
        static CELL: OnceLock<Result<Catalog, ContentError>> = OnceLock::new();
        CELL.get_or_init(|| Self::load(BUNDLED))
            .as_ref()
            .map_err(Clone::clone)
    }

    #[must_use]
    pub fn chapters(&self) -> &[Chapter] {
        &self.chapters
    }

    #[must_use]
    pub fn chapter(&self, id: &str) -> Option<&Chapter> {
        self.chapters.iter().find(|c| c.id == id)
    }

    /// Ochilish tartibi bo'yicha keyingi bob.
    #[must_use]
    pub fn next_after(&self, id: &str) -> Option<&Chapter> {
        let i = self.chapters.iter().position(|c| c.id == id)?;
        self.chapters.get(i + 1)
    }

    #[must_use]
    pub fn first(&self) -> Option<&Chapter> {
        self.chapters.first()
    }

    /// Rejimga mos ko'rinadigan bloklar. `Release` da tasdiqlanmagan diniy matn **hech qachon** qaytmaydi.
    #[must_use]
    pub fn visible_blocks(chapter: &Chapter, mode: ReleaseMode) -> Vec<VisibleBlock> {
        chapter
            .blocks
            .iter()
            .filter_map(|b| match b {
                Block::Text { id, text } => Some(VisibleBlock {
                    id: id.clone(),
                    text: text.clone(),
                    source: None,
                    unreviewed: false,
                }),
                Block::Religious {
                    id,
                    text,
                    source,
                    review_status,
                } => {
                    let approved = *review_status == ReviewStatus::Approved;
                    (approved || mode == ReleaseMode::Dev).then(|| VisibleBlock {
                        id: id.clone(),
                        text: text.clone(),
                        source: Some(source.clone()),
                        unreviewed: !approved,
                    })
                }
            })
            .collect()
    }
}

/// Kontent qoidalari; muammolar ro'yxatini qaytaradi.
fn validate(chapters: &[Chapter]) -> Vec<String> {
    let mut problems = Vec::new();
    let mut ids = HashSet::new();
    let mut orders = HashSet::new();
    for c in chapters {
        if !ids.insert(c.id.as_str()) {
            problems.push(format!("{}: bob ID takrorlangan", c.id));
        }
        if !orders.insert(c.order) {
            problems.push(format!(
                "{}: ochilish tartibi {} takrorlangan",
                c.id, c.order
            ));
        }
        if c.title.trim().is_empty() || c.page_prompt.trim().is_empty() {
            problems.push(format!("{}: sarlavha yoki sahifa savoli bo'sh", c.id));
        }
        if !(1..=7).contains(&c.law) {
            problems.push(format!("{}: qonun raqami 1..7 bo'lishi kerak", c.id));
        }
        if c.tasks.len() != TASKS_PER_CHAPTER {
            problems.push(format!(
                "{}: aniq {TASKS_PER_CHAPTER} ta vazifa bo'lishi kerak",
                c.id
            ));
        }
        let mut local = HashSet::new();
        for id in c
            .blocks
            .iter()
            .map(Block::id)
            .chain(c.tasks.iter().map(|t| t.id.as_str()))
        {
            if !local.insert(id) {
                problems.push(format!("{}: `{id}` takrorlangan", c.id));
            }
        }
        for b in &c.blocks {
            if let Block::Religious {
                id, source, text, ..
            } = b
            {
                if source.trim().is_empty() {
                    problems.push(format!("{}/{id}: diniy blokda manba majburiy", c.id));
                }
                if text.trim().is_empty() {
                    problems.push(format!("{}/{id}: diniy matn bo'sh", c.id));
                }
            }
        }
        if c.blocks.is_empty() {
            problems.push(format!("{}: bloklar yo'q", c.id));
        }
    }
    problems
}

#[cfg(test)]
mod tests {
    use super::*;

    fn chapter_json(extra_block: &str) -> String {
        format!(
            r#"{{"id":"x","law":1,"order":1,"title":"T","placeholder":true,
            "blocks":[{{"kind":"TEXT","id":"b1","text":"matn"}}{extra_block}],
            "page_prompt":"savol",
            "tasks":[{{"id":"t1","title":"a","trigger":{{"type":"MANUAL"}}}},
                     {{"id":"t2","title":"b","trigger":{{"type":"INCOME_RECORDED","min":2}}}},
                     {{"id":"t3","title":"c","trigger":{{"type":"AUDIT_COMPLETED"}}}}]}}"#
        )
    }

    fn religious(status: &str, source: &str) -> String {
        format!(
            r#",{{"kind":"RELIGIOUS","id":"r1","text":"oyat","source":"{source}","review_status":"{status}"}}"#
        )
    }

    fn load(json: &str) -> Result<Catalog, ContentError> {
        Catalog::load([("x.json", json)])
    }

    #[test]
    fn bundled_content_is_valid_and_has_five_chapters() {
        let c = Catalog::bundled().unwrap();
        assert_eq!(c.chapters().len(), 5);
        let laws: Vec<u8> = c.chapters().iter().map(|c| c.law).collect();
        assert_eq!(laws, [1, 2, 3, 4, 5]);
        assert!(c
            .chapters()
            .iter()
            .all(|ch| ch.tasks.len() == 3 && ch.placeholder));
    }

    /// Qabul mezoni: PENDING diniy blok release'da ko'rinmaydi (butun o'rnatilgan kontent bo'yicha).
    #[test]
    fn release_mode_never_shows_pending_religious_text_in_bundled_content() {
        let c = Catalog::bundled().unwrap();
        let mut pending_seen = 0;
        for ch in c.chapters() {
            for b in &ch.blocks {
                if let Block::Religious {
                    id,
                    review_status: ReviewStatus::Pending,
                    ..
                } = b
                {
                    pending_seen += 1;
                    let shown = Catalog::visible_blocks(ch, ReleaseMode::Release);
                    assert!(
                        shown.iter().all(|v| &v.id != id),
                        "{id} release'da ko'rindi"
                    );
                    let dev = Catalog::visible_blocks(ch, ReleaseMode::Dev);
                    assert!(dev.iter().any(|v| &v.id == id && v.unreviewed));
                }
            }
        }
        assert!(pending_seen > 0, "test ma'nosiz: PENDING blok yo'q");
        for ch in c.chapters() {
            assert!(Catalog::visible_blocks(ch, ReleaseMode::Release)
                .iter()
                .all(|v| !v.unreviewed));
        }
    }

    #[test]
    fn approved_religious_text_is_shown_with_source_in_release() {
        let c = load(&chapter_json(&religious("APPROVED", "Manba 1:2"))).unwrap();
        let shown = Catalog::visible_blocks(&c.chapters()[0], ReleaseMode::Release);
        assert_eq!(shown.len(), 2);
        assert_eq!(shown[1].source.as_deref(), Some("Manba 1:2"));
        assert!(!shown[1].unreviewed);
    }

    #[test]
    fn religious_block_requires_source() {
        assert!(matches!(
            load(&chapter_json(&religious("APPROVED", " "))),
            Err(ContentError::Invalid(_))
        ));
    }

    #[test]
    fn rejects_bad_content() {
        assert!(matches!(load("{"), Err(ContentError::Json { .. })));
        // Noma'lum review_status.
        assert!(matches!(
            load(&chapter_json(&religious("MAYBE", "m"))),
            Err(ContentError::Json { .. })
        ));
        // 2 ta vazifa.
        let mut v: serde_json::Value = serde_json::from_str(&chapter_json("")).unwrap();
        v["tasks"].as_array_mut().unwrap().pop();
        assert!(matches!(
            load(&v.to_string()),
            Err(ContentError::Invalid(_))
        ));
        // Takrorlangan vazifa ID.
        let mut v: serde_json::Value = serde_json::from_str(&chapter_json("")).unwrap();
        v["tasks"][1]["id"] = "t1".into();
        assert!(matches!(
            load(&v.to_string()),
            Err(ContentError::Invalid(_))
        ));
        // Bob tartibi takrorlangan.
        let a = chapter_json("");
        let b = chapter_json("").replace(r#""id":"x""#, r#""id":"y""#);
        assert!(matches!(
            Catalog::load([("a", a.as_str()), ("b", b.as_str())]),
            Err(ContentError::Invalid(_))
        ));
    }

    #[test]
    fn navigation_helpers() {
        let c = Catalog::bundled().unwrap();
        assert_eq!(c.first().unwrap().id, "ch01");
        assert_eq!(c.next_after("ch01").unwrap().id, "ch02");
        assert!(c.next_after("ch05").is_none());
        assert!(c.next_after("nope").is_none());
        assert_eq!(c.chapter("ch03").unwrap().law, 3);
    }
}
