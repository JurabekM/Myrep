//! `cargo xtask <buyruq>` — generatsiya va tekshiruvlar (BARAKA_OILASI 3.1, 10, 12, 13).
//!
//! * `i18n` — `shared/i18n` dan Flutter ARB va i18next JSON; `uz-Cyrl` avtomatik transliteratsiya;
//! * `i18n --lint` — kalitlar, plaseholderlar va taqiqlangan iboralar tekshiruvi;
//! * `tokens` — `shared/design-tokens/tokens.json` dan CSS va Dart;
//! * `vectors` — oltin vektorlarni mustaqil oracle bilan tekshirish;
//! * `codegen` — Android: FRB (`flutter_rust_bridge_codegen`) va Pigeon (Flutter SDK kerak);
//! * `all` — barcha generatsiyalar (CI keyin `git diff --exit-code` qiladi).
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};

mod i18n;
mod tokens;
mod translit;

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..")
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let root = root();
    let result = match args.first().map(String::as_str) {
        Some("i18n") if args.iter().any(|a| a == "--lint") => i18n::lint(&root),
        Some("i18n") => i18n::generate(&root),
        Some("tokens") => tokens::generate(&root),
        Some("vectors") => vectors(&root),
        Some("codegen") => codegen(&root),
        Some("all") => i18n::generate(&root)
            .and_then(|()| tokens::generate(&root))
            .and_then(|()| i18n::lint(&root)),
        _ => Err(
            "ishlatish: cargo xtask <i18n [--lint] | tokens | vectors | codegen | all>".to_string(),
        ),
    };
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("xtask: {e}");
            ExitCode::FAILURE
        }
    }
}

fn vectors(root: &Path) -> Result<(), String> {
    let status = Command::new("python3")
        .args([
            "-I",
            "spec/oracle/oracle.py",
            "--check",
            "spec/test-vectors",
        ])
        .current_dir(root)
        .status()
        .map_err(|e| format!("python3 ishga tushmadi: {e}"))?;
    if status.success() {
        Ok(())
    } else {
        Err("oracle tekshiruvi muvaffaqiyatsiz".to_string())
    }
}

/// Android bindings: Rust API → Dart (FRB) va Kotlin ↔ Dart (Pigeon). Generatsiya qilingan
/// fayllar commit qilinadi; CI `git diff --exit-code` bilan tekshiradi.
fn codegen(root: &Path) -> Result<(), String> {
    let android = root.join("apps/android");
    // FRB eski `frb_generated.rs` ni ham kompilyatsiya qiladi (cargo expand): avval o'chiriladi.
    let generated = root.join("core/bindings/flutter/src/frb_generated.rs");
    if generated.exists() {
        std::fs::remove_file(&generated).map_err(|e| format!("{}: {e}", generated.display()))?;
    }
    run(&android, "flutter_rust_bridge_codegen", &["generate"])?;
    run(
        &android,
        "dart",
        &["run", "pigeon", "--input", "pigeons/platform.dart"],
    )?;
    // Loyiha formatlash qoidasi (`analysis_options.yaml`, 120 belgi): `dart format lib` bilan
    // generatsiya natijasi farq qilmasin.
    run(
        &android,
        "dart",
        &["format", "lib/bindings", "lib/platform/platform_api.g.dart"],
    )?;
    run(root, "cargo", &["fmt", "-p", "baraka-bindings-flutter"])
}

fn run(dir: &Path, program: &str, args: &[&str]) -> Result<(), String> {
    let status = Command::new(program)
        .args(args)
        .current_dir(dir)
        .status()
        .map_err(|e| format!("{program} ishga tushmadi: {e}"))?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("{program} {} muvaffaqiyatsiz", args.join(" ")))
    }
}

pub(crate) fn write_if_changed(path: &Path, content: &str) -> Result<(), String> {
    if std::fs::read_to_string(path).ok().as_deref() == Some(content) {
        return Ok(());
    }
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    }
    std::fs::write(path, content).map_err(|e| format!("{}: {e}", path.display()))?;
    println!("yozildi: {}", path.display());
    Ok(())
}
