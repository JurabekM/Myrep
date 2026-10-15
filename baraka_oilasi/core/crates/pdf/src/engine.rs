use std::collections::HashMap;

use chrono::{Datelike, NaiveDate};
use typst::diag::{FileError, FileResult, Severity};
use typst::foundations::{Bytes, Datetime, Smart};
use typst::syntax::{FileId, RootedPath, Source, VirtualPath, VirtualRoot};
use typst::text::{Font, FontBook};
use typst::utils::LazyHash;
use typst::{Library, LibraryExt, World};
use typst_layout::PagedDocument;
use typst_pdf::{PdfOptions, Timestamp};

const FONTS: [&[u8]; 4] = [
    include_bytes!("../../../../shared/fonts/NotoSans-Regular.ttf"),
    include_bytes!("../../../../shared/fonts/NotoSans-Bold.ttf"),
    include_bytes!("../../../../shared/fonts/NotoSerif-Regular.ttf"),
    include_bytes!("../../../../shared/fonts/NotoSerif-Bold.ttf"),
];

const COMMON: &str = include_str!("../../../../shared/pdf/common.typ");

/// Render xatosi. `details` — faqat ishlab chiquvchi uchun (log'ga yozilmaydi).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PdfError {
    pub code: &'static str,
    pub details: Vec<String>,
}

impl std::fmt::Display for PdfError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code)
    }
}

impl std::error::Error for PdfError {}

/// Natija: PDF baytlari va (testlar uchun) typst hujjati.
pub struct Rendered {
    pub pdf: Vec<u8>,
    pub document: PagedDocument,
    /// Kompilyatsiya ogohlantirishlari (masalan, topilmagan shrift). Bo'sh bo'lishi kerak.
    pub warnings: Vec<String>,
}

/// Bir marta yaratiladi (shriftlar va standart kutubxona), ko'p marta ishlatiladi.
pub struct PdfEngine {
    library: LazyHash<Library>,
    book: LazyHash<FontBook>,
    fonts: Vec<Font>,
}

impl Default for PdfEngine {
    fn default() -> Self {
        Self::new()
    }
}

fn file_id(path: &str) -> Result<FileId, PdfError> {
    let vpath = VirtualPath::new(path).map_err(|_| PdfError {
        code: "PDF_BAD_PATH",
        details: vec![path.to_string()],
    })?;
    Ok(RootedPath::new(VirtualRoot::Project, vpath).intern())
}

struct DocWorld<'a> {
    engine: &'a PdfEngine,
    main: FileId,
    sources: HashMap<FileId, Source>,
    files: HashMap<FileId, Bytes>,
    today: NaiveDate,
}

impl World for DocWorld<'_> {
    fn library(&self) -> &LazyHash<Library> {
        &self.engine.library
    }

    fn book(&self) -> &LazyHash<FontBook> {
        &self.engine.book
    }

    fn main(&self) -> FileId {
        self.main
    }

    fn source(&self, id: FileId) -> FileResult<Source> {
        self.sources
            .get(&id)
            .cloned()
            .ok_or(FileError::AccessDenied)
    }

    fn file(&self, id: FileId) -> FileResult<Bytes> {
        if let Some(b) = self.files.get(&id) {
            return Ok(b.clone());
        }
        self.sources
            .get(&id)
            .map(|s| Bytes::new(s.text().as_bytes().to_vec()))
            .ok_or(FileError::AccessDenied)
    }

    fn font(&self, index: usize) -> Option<Font> {
        self.engine.fonts.get(index).cloned()
    }

    fn today(&self, _offset: Option<chrono_offset::Duration>) -> Option<Datetime> {
        Datetime::from_ymd(
            self.today.year(),
            u8::try_from(self.today.month()).ok()?,
            u8::try_from(self.today.day()).ok()?,
        )
    }
}

// typst `World::today` turi uchun qisqa nom.
mod chrono_offset {
    pub use typst::foundations::Duration;
}

impl PdfEngine {
    pub fn new() -> Self {
        let fonts: Vec<Font> = FONTS
            .iter()
            .flat_map(|data| Font::iter(Bytes::new(data.to_vec())))
            .collect();
        Self {
            library: LazyHash::new(Library::default()),
            book: LazyHash::new(FontBook::from_fonts(&fonts)),
            fonts,
        }
    }

    /// Shablonni `data` bilan render qiladi. `ident` — hujjatning barqaror identifikatori
    /// (masalan, kelishuv ID'si), `today` — hujjat sanasi (Clock'dan).
    pub fn render(
        &self,
        template: &str,
        data: &serde_json::Value,
        extra_files: &[(&str, Vec<u8>)],
        ident: &str,
        today: NaiveDate,
    ) -> Result<Rendered, PdfError> {
        let main = file_id("main.typ")?;
        let mut sources = HashMap::new();
        sources.insert(main, Source::new(main, template.to_string()));
        let common = file_id("common.typ")?;
        sources.insert(common, Source::new(common, COMMON.to_string()));
        let mut files = HashMap::new();
        let json = serde_json::to_vec(data).map_err(|e| PdfError {
            code: "PDF_BAD_DATA",
            details: vec![e.to_string()],
        })?;
        files.insert(file_id("data.json")?, Bytes::new(json));
        for (name, bytes) in extra_files {
            files.insert(file_id(name)?, Bytes::new(bytes.clone()));
        }
        let world = DocWorld {
            engine: self,
            main,
            sources,
            files,
            today,
        };

        let warned = typst::compile::<PagedDocument>(&world);
        let warnings: Vec<String> = warned
            .warnings
            .iter()
            .filter(|w| w.severity == Severity::Warning)
            .map(|w| w.message.to_string())
            .collect();
        let document = warned.output.map_err(|errs| PdfError {
            code: "PDF_COMPILE",
            details: errs.iter().map(|e| e.message.to_string()).collect(),
        })?;
        let timestamp = Datetime::from_ymd_hms(
            today.year(),
            u8::try_from(today.month()).unwrap_or(1),
            u8::try_from(today.day()).unwrap_or(1),
            0,
            0,
            0,
        )
        .map(Timestamp::new_utc);
        let options = PdfOptions {
            ident: Smart::Custom(ident.to_string()),
            creator: Smart::Custom(Some("Baraka".to_string())),
            timestamp,
            ..PdfOptions::default()
        };
        let pdf = typst_pdf::pdf(&document, &options).map_err(|errs| PdfError {
            code: "PDF_EXPORT",
            details: errs.iter().map(|e| e.message.to_string()).collect(),
        })?;
        Ok(Rendered {
            pdf,
            document,
            warnings,
        })
    }
}
