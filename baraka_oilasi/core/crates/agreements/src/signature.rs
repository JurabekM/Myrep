//! Shu qurilmada chizilgan imzo (uy/SPEC 2F.3). Imzo — normallashtirilgan chiziqlar
//! (0..=1000 × 0..=400 maydon). SVG faqat raqamlardan yig'iladi, shuning uchun foydalanuvchi
//! matni PDF yoki SVG ichiga tushmaydi.
use std::fmt::Write;

use serde::{Deserialize, Serialize};

pub const PAD_WIDTH: u16 = 1000;
pub const PAD_HEIGHT: u16 = 400;
pub const MAX_POINTS: usize = 4000;
pub const MAX_STROKES: usize = 200;

/// Bitta uzluksiz chiziq: `[x, y]` nuqtalar.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
pub struct Stroke(pub Vec<[u16; 2]>);

/// Imzo chiziqlarini tekshiradi: kamida bitta chiziqda ikki nuqta, chegaradan chiqmaydi.
pub fn validate_signature(strokes: &[Stroke]) -> Result<(), &'static str> {
    if strokes.len() > MAX_STROKES {
        return Err("SIGNATURE_TOO_LARGE");
    }
    let mut total = 0_usize;
    for s in strokes {
        total += s.0.len();
        if s.0.iter().any(|[x, y]| *x > PAD_WIDTH || *y > PAD_HEIGHT) {
            return Err("SIGNATURE_OUT_OF_BOUNDS");
        }
    }
    if total > MAX_POINTS {
        return Err("SIGNATURE_TOO_LARGE");
    }
    if !strokes.iter().any(|s| s.0.len() >= 2) {
        return Err("SIGNATURE_EMPTY");
    }
    Ok(())
}

/// Imzoni SVG ko'rinishida (PDF va ekran uchun). Bitta nuqtali chiziqlar tashlab yuboriladi.
pub fn signature_svg(strokes: &[Stroke]) -> String {
    let mut out = format!(
        r##"<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PAD_WIDTH} {PAD_HEIGHT}"><g fill="none" stroke="#1f1e1d" stroke-width="16" stroke-linecap="round" stroke-linejoin="round">"##
    );
    for s in strokes.iter().filter(|s| s.0.len() >= 2) {
        out.push_str(r#"<polyline points=""#);
        for (i, [x, y]) in s.0.iter().enumerate() {
            let sep = if i == 0 { "" } else { " " };
            let _ = write!(out, "{sep}{x},{y}");
        }
        out.push_str(r#""/>"#);
    }
    out.push_str("</g></svg>");
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rules() {
        assert_eq!(validate_signature(&[]), Err("SIGNATURE_EMPTY"));
        assert_eq!(
            validate_signature(&[Stroke(vec![[1, 1]])]),
            Err("SIGNATURE_EMPTY")
        );
        assert_eq!(
            validate_signature(&[Stroke(vec![[1, 1], [1001, 2]])]),
            Err("SIGNATURE_OUT_OF_BOUNDS")
        );
        assert_eq!(
            validate_signature(&[Stroke(vec![[0, 0]; MAX_POINTS + 1])]),
            Err("SIGNATURE_TOO_LARGE")
        );
        assert!(validate_signature(&[Stroke(vec![[0, 0], [1000, 400]])]).is_ok());
    }

    #[test]
    fn svg_has_only_numbers() {
        let svg = signature_svg(&[Stroke(vec![[10, 20], [30, 40]]), Stroke(vec![[5, 5]])]);
        assert!(svg.contains(r#"<polyline points="10,20 30,40"/>"#));
        assert_eq!(svg.matches("<polyline").count(), 1);
    }
}
