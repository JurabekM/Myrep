//! Oila kengashi bayonnomasi: typst shabloni va PDF renderer (DESKTOP_PROMPT.md 2 va 7-bo'lim).
//!
//! Shablon kodga joylangan. Foydalanuvchi matni (ismlar, kategoriya nomlari, summalar) typst'ga faqat
//! satr qiymati sifatida beriladi — markup sifatida talqin qilinmaydi (inyeksiya yo'q). Shriftlar ilova
//! ichiga joylangan (`typst-assets`): tizimdagi shriftga bog'liq emas.

use typst::diag::{FileError, FileResult};
use typst::foundations::Bytes;
use typst::foundations::Datetime;
use typst::layout::PagedDocument;
use typst::syntax::{FileId, Source, VirtualPath};
use typst::text::{Font, FontBook};
use typst::utils::LazyHash;
use typst::{Library, World};

/// Bayonnoma shrifti. Libertinus Serif ʻ (U+02BB) va ʼ (U+02BC) belgilarini o'z ichiga oladi (testlangan).
pub const FONT_FAMILY: &str = "Libertinus Serif";

/// Bayonnoma ma'lumotlari. Barcha matnlar tayyor (tarjima qilingan, formatlangan) holda beriladi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CouncilReport {
    /// Sarlavha.
    pub title: String,
    /// Davr matni (masalan, `01.10.2026 — 31.10.2026`).
    pub period: String,
    /// Yaratilgan sana (`DD.MM.YYYY`).
    pub generated_on: String,
    /// Xulosa qatorlari: nomi va formatlangan summa.
    pub summary: Vec<(String, String)>,
    /// Kategoriyalar: nomi va toifa nomi.
    pub categories: Vec<(String, String)>,
    /// Havas chegarasi holati matni.
    pub limit_status: String,
    /// Kattalar: nomi va rozilik (ha/yo'q) matni.
    pub adults: Vec<(String, String)>,
    /// Ta'limiy material belgisi (disklеymer).
    pub disclaimer: String,
}

/// PDF yaratish xatosi. Xabarda foydalanuvchi ma'lumoti bo'lmaydi.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum PdfError {
    /// Shablonni kompilyatsiya qilib bo'lmadi (ichki xato).
    #[error("bayonnoma shablonini kompilyatsiya qilib bo'lmadi")]
    Compile,
    /// PDF'ni yozib bo'lmadi (ichki xato).
    #[error("PDF yaratib bo'lmadi")]
    Render,
}

/// Bayonnomani PDF baytlariga aylantiradi.
pub fn render_council_report(report: &CouncilReport) -> Result<Vec<u8>, PdfError> {
    let world = ReportWorld::new(template(report));
    let warned = typst::compile::<PagedDocument>(&world);
    let document = warned.output.map_err(|_| PdfError::Compile)?;
    typst_pdf::pdf(&document, &typst_pdf::PdfOptions::default()).map_err(|_| PdfError::Render)
}

/// Ilova bilan birga keladigan shrift baytlari (testlar uchun ham).
pub fn font_data() -> impl Iterator<Item = &'static [u8]> {
    typst_assets::fonts()
}

/// Typst satr literali: qo'shtirnoq va backslash escape qilinadi. Natija — qiymat, markup emas.
fn lit(text: &str) -> String {
    let escaped = text.replace('\\', "\\\\").replace('"', "\\\"");
    format!("\"{escaped}\"")
}

/// Shablon: sarlavha, xulosa, kategoriyalar, havas chegarasi, kattalar roziligi va disklеymer.
fn template(report: &CouncilReport) -> String {
    let mut out = String::new();
    out.push_str("#set page(paper: \"a4\", margin: 2cm)\n");
    out.push_str(&format!(
        "#set text(font: \"{FONT_FAMILY}\", size: 11pt, lang: \"uz\")\n"
    ));
    out.push_str(&format!(
        "#align(center)[#text(size: 18pt, weight: \"bold\")[#({})]]\n",
        lit(&report.title)
    ));
    out.push_str(&format!(
        "#align(center)[#text(fill: luma(90))[#({})]]\n",
        lit(&report.period)
    ));
    out.push_str(&format!(
        "#align(center)[#text(fill: luma(90))[#({})]]\n",
        lit(&report.generated_on)
    ));
    out.push_str("#v(1.2em)\n");
    out.push_str(&section("Xulosa"));
    out.push_str(&pairs_table(&report.summary));
    out.push_str("#v(0.8em)\n");
    out.push_str(&section("Kategoriyalar va toifalar"));
    out.push_str(&pairs_table(&report.categories));
    out.push_str("#v(0.8em)\n");
    out.push_str(&section("Havas chegarasi"));
    out.push_str(&format!("#par[#({})]\n", lit(&report.limit_status)));
    out.push_str("#v(0.8em)\n");
    out.push_str(&section("Kattalar roziligi"));
    out.push_str(&pairs_table(&report.adults));
    out.push_str("#v(2em)\n");
    out.push_str(&format!(
        "#text(size: 9pt, fill: luma(110))[#({})]\n",
        lit(&report.disclaimer)
    ));
    out
}

fn section(title: &str) -> String {
    format!(
        "#text(size: 13pt, weight: \"bold\")[#({})]\n#v(0.4em)\n",
        lit(title)
    )
}

/// Ikki ustunli jadval: chapda — nomi, o'ngda — qiymat.
fn pairs_table(rows: &[(String, String)]) -> String {
    let mut out =
        String::from("#table(columns: (1fr, auto), stroke: none, inset: (x: 4pt, y: 5pt),\n");
    for (left, right) in rows {
        out.push_str(&format!("  [#({})], [#({})],\n", lit(left), lit(right)));
    }
    out.push_str(")\n");
    out
}

/// Typst uchun dunyo: bitta asosiy manba va ilova ichidagi shriftlar.
struct ReportWorld {
    library: LazyHash<Library>,
    book: LazyHash<FontBook>,
    fonts: Vec<Font>,
    main: Source,
}

impl ReportWorld {
    fn new(text: String) -> Self {
        let fonts: Vec<Font> = font_data()
            .flat_map(|data| Font::iter(Bytes::new(data.to_vec())))
            .collect();
        let book = FontBook::from_fonts(&fonts);
        let main = Source::new(FileId::new(None, VirtualPath::new("main.typ")), text);
        Self {
            library: LazyHash::new(Library::default()),
            book: LazyHash::new(book),
            fonts,
            main,
        }
    }
}

impl World for ReportWorld {
    fn library(&self) -> &LazyHash<Library> {
        &self.library
    }

    fn book(&self) -> &LazyHash<FontBook> {
        &self.book
    }

    fn main(&self) -> FileId {
        self.main.id()
    }

    fn source(&self, id: FileId) -> FileResult<Source> {
        if id == self.main.id() {
            Ok(self.main.clone())
        } else {
            Err(FileError::NotFound(id.vpath().as_rootless_path().into()))
        }
    }

    fn file(&self, id: FileId) -> FileResult<Bytes> {
        Err(FileError::NotFound(id.vpath().as_rootless_path().into()))
    }

    fn font(&self, index: usize) -> Option<Font> {
        self.fonts.get(index).cloned()
    }

    fn today(&self, _offset: Option<i64>) -> Option<Datetime> {
        None
    }
}
