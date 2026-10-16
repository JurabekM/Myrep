use std::fmt::Write as _;
use std::path::Path;

use serde_json::Value;

use crate::write_if_changed;

fn kebab(s: &str) -> String {
    let mut out = String::new();
    for c in s.chars() {
        if c.is_uppercase() {
            out.push('-');
            out.extend(c.to_lowercase());
        } else {
            out.push(c);
        }
    }
    out
}

fn argb(hex: &str) -> String {
    format!("0xFF{}", hex.trim_start_matches('#').to_uppercase())
}

/// WCAG 2.x nisbiy yorqinlik (sRGB). Faqat build vositasi — pul hisobi emas.
fn luminance(hex: &str) -> Result<f64, String> {
    let h = hex.trim_start_matches('#');
    if h.len() != 6 {
        return Err(format!("tokens: noto'g'ri rang {hex}"));
    }
    let mut ch = [0.0_f64; 3];
    for (i, c) in ch.iter_mut().enumerate() {
        let v = u8::from_str_radix(&h[i * 2..i * 2 + 2], 16)
            .map_err(|_| format!("tokens: noto'g'ri rang {hex}"))?;
        let s = f64::from(v) / 255.0;
        *c = if s <= 0.04045 {
            s / 12.92
        } else {
            ((s + 0.055) / 1.055).powf(2.4)
        };
    }
    Ok(0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2])
}

pub fn contrast_ratio(a: &str, b: &str) -> Result<f64, String> {
    let (la, lb) = (luminance(a)?, luminance(b)?);
    let (hi, lo) = if la > lb { (la, lb) } else { (lb, la) };
    Ok((hi + 0.05) / (lo + 0.05))
}

/// `contrast.pairs` ni har bir mavzu uchun tekshiradi (10.4: «kontrast generatsiyadan oldin
/// hisoblanadi»). Barcha xatolar birdan qaytariladi.
fn check_contrast(t: &Value) -> Result<(), String> {
    let pairs = t
        .pointer("/contrast/pairs")
        .and_then(Value::as_array)
        .ok_or("tokens: contrast.pairs yo'q")?;
    let themes = t
        .get("color")
        .and_then(Value::as_object)
        .ok_or("tokens: 'color' yo'q")?;
    let mut errors = Vec::new();
    for (theme, palette) in themes {
        let color = |k: &str| {
            palette
                .get(k)
                .and_then(Value::as_str)
                .ok_or(format!("tokens: color.{theme}.{k} yo'q"))
        };
        for p in pairs {
            let fg = p.get("fg").and_then(Value::as_str).unwrap_or_default();
            let min = p.get("min").and_then(Value::as_f64).unwrap_or(4.5);
            for bg in p.get("bg").and_then(Value::as_array).into_iter().flatten() {
                let bg = bg.as_str().unwrap_or_default();
                let r = contrast_ratio(color(fg)?, color(bg)?)?;
                if r < min {
                    errors.push(format!("{theme}: {fg} / {bg} = {r:.2}:1 < {min}:1"));
                }
            }
        }
    }
    if errors.is_empty() {
        Ok(())
    } else {
        Err(format!(
            "kontrast WCAG AA dan past:\n  {}",
            errors.join("\n  ")
        ))
    }
}

pub fn generate(root: &Path) -> Result<(), String> {
    let path = root.join("shared/design-tokens/tokens.json");
    let text = std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
    let t: Value = serde_json::from_str(&text).map_err(|e| e.to_string())?;
    check_contrast(&t)?;
    let obj = |v: &Value, k: &str| {
        v.get(k)
            .and_then(Value::as_object)
            .cloned()
            .ok_or(format!("tokens: '{k}' yo'q"))
    };
    let colors = obj(&t, "color")?;
    // Standart mavzu (foydalanuvchi qarori: Claude Code dark theme uslubi). Ikkinchisi — `data-theme` bilan.
    let default_theme = t
        .get("defaultTheme")
        .and_then(Value::as_str)
        .unwrap_or("dark");
    let other_theme = if default_theme == "dark" {
        "light"
    } else {
        "dark"
    };
    let palette = |name: &str| {
        colors
            .get(name)
            .and_then(Value::as_object)
            .cloned()
            .ok_or(format!("tokens: color.{name} yo'q"))
    };
    let main = palette(default_theme)?;
    let alt = palette(other_theme)?;

    // `--bk-*` — qiymatlar, `@theme inline` — Tailwind v4 utilitalari (`bg-paper`, `text-ink`).
    let mut css = String::from("/* @generated cargo xtask tokens — qo'lda tahrirlamang. Manba: shared/design-tokens/tokens.json */\n:root {\n");
    let _ = writeln!(css, "  color-scheme: {default_theme};");
    for (k, v) in &main {
        let _ = writeln!(
            css,
            "  --bk-{}: {};",
            kebab(k),
            v.as_str().unwrap_or_default()
        );
    }
    for group in ["radius", "space"] {
        for (k, v) in obj(&t, group)? {
            let _ = writeln!(css, "  --bk-{group}-{}: {}px;", kebab(&k), v);
        }
    }
    for (k, v) in obj(&t, "font")? {
        match v {
            Value::String(s) => {
                let _ = writeln!(css, "  --bk-font-{}: \"{s}\";", kebab(&k));
            }
            other => {
                let _ = writeln!(css, "  --bk-font-{}: {other}px;", kebab(&k));
            }
        }
    }
    let _ = writeln!(
        css,
        "}}\n\n:root[data-theme=\"{other_theme}\"] {{\n  color-scheme: {other_theme};"
    );
    for (k, v) in &alt {
        let _ = writeln!(
            css,
            "  --bk-{}: {};",
            kebab(k),
            v.as_str().unwrap_or_default()
        );
    }
    css.push_str("}\n\n@theme inline {\n");
    for k in main.keys() {
        let _ = writeln!(css, "  --color-{0}: var(--bk-{0});", kebab(k));
    }
    for k in obj(&t, "radius")?.keys() {
        let _ = writeln!(css, "  --radius-{0}: var(--bk-radius-{0});", kebab(k));
    }
    css.push_str("  --font-sans: var(--bk-font-family), system-ui, sans-serif;\n  --font-serif: var(--bk-font-family-serif), Georgia, serif;\n}\n");
    write_if_changed(&root.join("apps/desktop/ui/src/styles/tokens.css"), &css)?;

    // Dart (Android).
    let mut dart = String::from("// @generated cargo xtask tokens — qo'lda tahrirlamang. Manba: shared/design-tokens/tokens.json\n// ignore_for_file: public_member_api_docs\nimport 'dart:ui';\n\n");
    let light = palette("light")?;
    let dark = palette("dark")?;
    let _ = writeln!(dart, "/// Standart mavzu: `{default_theme}` (Claude Code dark theme uslubi).\nconst bool barakaDefaultDark = {};\n", default_theme == "dark");
    for (name, palette) in [("BarakaLightColors", &light), ("BarakaDarkColors", &dark)] {
        let _ = writeln!(dart, "abstract final class {name} {{");
        for (k, v) in palette {
            let _ = writeln!(
                dart,
                "  static const Color {k} = Color({});",
                argb(v.as_str().unwrap_or_default())
            );
        }
        dart.push_str("}\n\n");
    }
    dart.push_str("abstract final class BarakaDimens {\n");
    for group in ["radius", "space"] {
        for (k, v) in obj(&t, group)? {
            let mut name = group.to_string();
            name.extend(k.chars().next().map(|c| c.to_ascii_uppercase()));
            name.push_str(&k[1..]);
            let _ = writeln!(dart, "  static const double {name} = {v};");
        }
    }
    dart.push_str("}\n");
    write_if_changed(
        &root.join("apps/android/lib/app/theme/tokens.g.dart"),
        &dart,
    )?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn wcag_reference_ratios() {
        let r = |a, b| (contrast_ratio(a, b).unwrap() * 100.0).round() / 100.0;
        assert!((r("#000000", "#FFFFFF") - 21.0).abs() < f64::EPSILON);
        assert!((r("#FFFFFF", "#FFFFFF") - 1.0).abs() < f64::EPSILON);
        // Claude Code dark: matn fon ustida.
        assert!((r("#FAF9F5", "#262624") - 14.39).abs() < 0.001);
        assert!((r("#1F1E1D", "#D97757") - 5.33).abs() < 0.001);
    }

    #[test]
    fn low_contrast_pair_is_rejected() {
        let t: Value = serde_json::json!({
            "color": {"dark": {"ink": "#4A4945", "paper": "#262624"}},
            "contrast": {"pairs": [{"fg": "ink", "bg": ["paper"], "min": 4.5}]}
        });
        let err = check_contrast(&t).unwrap_err();
        assert!(err.contains("dark: ink / paper = 1.68:1"), "{err}");
    }
}
