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

pub fn generate(root: &Path) -> Result<(), String> {
    let path = root.join("shared/design-tokens/tokens.json");
    let text = std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
    let t: Value = serde_json::from_str(&text).map_err(|e| e.to_string())?;
    let obj = |v: &Value, k: &str| {
        v.get(k)
            .and_then(Value::as_object)
            .cloned()
            .ok_or(format!("tokens: '{k}' yo'q"))
    };
    let colors = obj(&t, "color")?;
    let light = colors
        .get("light")
        .and_then(Value::as_object)
        .ok_or("tokens: color.light yo'q")?;
    let dark = colors
        .get("dark")
        .and_then(Value::as_object)
        .ok_or("tokens: color.dark yo'q")?;

    // CSS (desktop).
    // `--bk-*` — qiymatlar (light/dark), `@theme inline` — Tailwind v4 utilitalari (`bg-paper`, `text-ink`).
    let mut css = String::from("/* @generated cargo xtask tokens — qo'lda tahrirlamang. Manba: shared/design-tokens/tokens.json */\n:root {\n");
    for (k, v) in light {
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
    css.push_str(
        "}\n\n@media (prefers-color-scheme: dark) {\n  :root:not([data-theme=\"light\"]) {\n",
    );
    for (k, v) in dark {
        let _ = writeln!(
            css,
            "    --bk-{}: {};",
            kebab(k),
            v.as_str().unwrap_or_default()
        );
    }
    css.push_str("  }\n}\n\n:root[data-theme=\"dark\"] {\n");
    for (k, v) in dark {
        let _ = writeln!(
            css,
            "  --bk-{}: {};",
            kebab(k),
            v.as_str().unwrap_or_default()
        );
    }
    css.push_str("}\n\n@theme inline {\n");
    for k in light.keys() {
        let _ = writeln!(css, "  --color-{0}: var(--bk-{0});", kebab(k));
    }
    for k in obj(&t, "radius")?.keys() {
        let _ = writeln!(css, "  --radius-{0}: var(--bk-radius-{0});", kebab(k));
    }
    css.push_str("  --font-sans: var(--bk-font-family), system-ui, sans-serif;\n  --font-serif: var(--bk-font-family-serif), Georgia, serif;\n}\n");
    write_if_changed(&root.join("apps/desktop/ui/src/styles/tokens.css"), &css)?;

    // Dart (Android).
    let mut dart = String::from("// @generated cargo xtask tokens — qo'lda tahrirlamang. Manba: shared/design-tokens/tokens.json\n// ignore_for_file: public_member_api_docs\nimport 'dart:ui';\n\n");
    for (name, palette) in [("BarakaLightColors", light), ("BarakaDarkColors", dark)] {
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
