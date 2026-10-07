use std::sync::OnceLock;

use typst::{
    diag::{FileError, FileResult},
    foundations::{Bytes, Datetime, Duration},
    syntax::{FileId, RootedPath, Source, VirtualPath, VirtualRoot},
    text::{Font, FontBook},
    utils::LazyHash,
    Library, LibraryExt, World,
};
use typst_layout::PagedDocument;
use typst_pdf::PdfOptions;

/// Ilovaga o'rnatilgan shriftlar (OFL/Bitstream Vera litsenziyasi, `fonts/LICENSE-DejaVu.txt`).
pub const EMBEDDED_FONTS: [&[u8]; 2] = [
    include_bytes!("../fonts/DejaVuSans.ttf"),
    include_bytes!("../fonts/DejaVuSans-Bold.ttf"),
];

#[derive(Debug, thiserror::Error)]
pub enum PdfError {
    #[error("PDF shabloni kompilyatsiya bo'lmadi: {0}")]
    Compile(String),
    #[error("PDF eksport xatosi: {0}")]
    Export(String),
}

struct Fonts {
    book: LazyHash<FontBook>,
    fonts: Vec<Font>,
}

fn fonts() -> &'static Fonts {
    static CELL: OnceLock<Fonts> = OnceLock::new();
    CELL.get_or_init(|| {
        let fonts: Vec<Font> = EMBEDDED_FONTS
            .iter()
            .flat_map(|data| Font::iter(Bytes::new(*data)))
            .collect();
        Fonts {
            book: LazyHash::new(FontBook::from_fonts(&fonts)),
            fonts,
        }
    })
}

/// Bitta manba fayldan iborat dunyo: tashqi fayl, paket va tarmoq yo'q.
struct OneFileWorld {
    library: LazyHash<Library>,
    source: Source,
    /// Qo'shimcha ikkilik fayllar (imzo rasmlari): nom (`/` siz) → bayt.
    files: Vec<(String, Bytes)>,
}

impl World for OneFileWorld {
    fn library(&self) -> &LazyHash<Library> {
        &self.library
    }

    fn book(&self) -> &LazyHash<FontBook> {
        &fonts().book
    }

    fn main(&self) -> FileId {
        self.source.id()
    }

    fn source(&self, id: FileId) -> FileResult<Source> {
        if id == self.source.id() {
            Ok(self.source.clone())
        } else {
            Err(FileError::NotFound(id.vpath().get_with_slash().into()))
        }
    }

    fn file(&self, id: FileId) -> FileResult<Bytes> {
        let path = id.vpath().get_with_slash();
        let name = path.trim_start_matches('/');
        self.files
            .iter()
            .find(|(n, _)| n == name)
            .map(|(_, b)| b.clone())
            .ok_or_else(|| FileError::NotFound(path.into()))
    }

    fn font(&self, index: usize) -> Option<Font> {
        fonts().fonts.get(index).cloned()
    }

    fn today(&self, _offset: Option<Duration>) -> Option<Datetime> {
        // Sana shablonga tashqaridan beriladi: natija deterministik bo'lishi uchun.
        None
    }
}

/// typst manbasini PDF baytlariga o'giradi.
///
/// # Errors
/// Shablon xatosi yoki eksport xatosi.
pub fn render_pdf(markup: &str) -> Result<Vec<u8>, PdfError> {
    render_pdf_with_files(markup, &[])
}

/// Xuddi [`render_pdf`], lekin shablon `files` dagi rasmlarni (masalan, `sig-lender.png`) ishlata oladi.
///
/// # Errors
/// Shablon xatosi yoki eksport xatosi.
pub fn render_pdf_with_files(markup: &str, files: &[(&str, Vec<u8>)]) -> Result<Vec<u8>, PdfError> {
    let vpath = VirtualPath::new("main.typ").map_err(|e| PdfError::Compile(e.to_string()))?;
    let id = FileId::new(RootedPath::new(VirtualRoot::Project, vpath));
    let world = OneFileWorld {
        library: LazyHash::new(Library::default()),
        source: Source::new(id, markup.to_owned()),
        files: files
            .iter()
            .map(|(n, b)| ((*n).to_owned(), Bytes::new(b.clone())))
            .collect(),
    };
    let compiled = typst::compile::<PagedDocument>(&world);
    let document = compiled.output.map_err(|errors| {
        PdfError::Compile(
            errors
                .iter()
                .map(|e| e.message.to_string())
                .collect::<Vec<_>>()
                .join("; "),
        )
    })?;
    typst_pdf::pdf(&document, &PdfOptions::default()).map_err(|errors| {
        PdfError::Export(
            errors
                .iter()
                .map(|e| e.message.to_string())
                .collect::<Vec<_>>()
                .join("; "),
        )
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    /// O'zbek lotin alifbosidagi barcha belgilar (ʻ U+02BB, ʼ U+02BC va o', g' yozuvi uchun) o'rnatilgan
    /// shriftda bor: tizim shriftlariga tayanilmaydi.
    #[test]
    fn embedded_font_covers_uzbek_latin_and_cyrillic() {
        let text = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz\u{2bb}\u{2bc}'\u{2019}\u{2116}0123456789 .,;:!?()-\u{2014}%/";
        let ru = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя";
        for f in &fonts().fonts {
            for c in text.chars().chain(ru.chars()) {
                assert!(
                    f.info().coverage.contains(u32::from(c)),
                    "{c:?} (U+{:04X}) shriftda yo'q",
                    u32::from(c)
                );
            }
        }
    }

    #[test]
    fn renders_a_pdf() {
        let bytes =
            render_pdf("#set text(font: \"DejaVu Sans\")\n= Salom\nO\u{2bb}zbekiston").unwrap();
        assert!(bytes.starts_with(b"%PDF-"));
        assert!(bytes.len() > 1_000);
    }

    #[test]
    fn reports_template_errors_instead_of_panicking() {
        assert!(matches!(
            render_pdf("#nonexistent-function()"),
            Err(PdfError::Compile(_))
        ));
    }
}
