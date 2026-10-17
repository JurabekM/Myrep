//! tamga-mcp-proxy — istalgan stdio MCP serverni o'rab, `tools/call` chaqiruvlarini TAMGA siyosati
//! bilan **bajarilishidan oldin** tekshiradi va jurnalga yozadi.
//!
//! ```text
//! tamga-mcp-proxy [--name <server>] [--session <id>] -- <buyruq> [argumentlar...]
//! ```
//!
//! MCP mijozi (Claude Code, Claude Desktop, Cursor...) serverni shu buyruq orqali ishga tushiradi.
//! Proxy JSON-RPC qatorlarini ikki tomonga **aynan** uzatadi; faqat `tools/call` so'rovi `tamgad`
//! qaroriga yuboriladi. Rad etilsa so'rov serverga yetmaydi — mijozga MCP `isError` natijasi
//! qaytariladi (model sababni ko'radi). Server javobi `tool.post` bo'lib yoziladi va sessiya
//! taint'ini o'rgatadi. Bir nechta server bir sessiyani bo'lishsa (`--session`), taint ular orasida
//! ham ishlaydi: biri o'qigan sirni boshqasi yubora olmaydi.

mod relay;

use std::process::{ExitCode, Stdio};

fn usage() -> ExitCode {
    eprintln!(
        "foydalanish: tamga-mcp-proxy [--name <server>] [--session <id>] -- <buyruq> [argumentlar...]"
    );
    ExitCode::from(2)
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let Some(split) = args.iter().position(|a| a == "--") else {
        return usage();
    };
    let (opts, cmd) = (&args[..split], &args[split + 1..]);
    let Some((program, program_args)) = cmd.split_first() else {
        return usage();
    };
    let mut name = None;
    let mut session = std::env::var("TAMGA_SESSION").ok();
    let mut it = opts.iter();
    while let Some(o) = it.next() {
        match o.as_str() {
            "--name" => name = it.next().cloned(),
            "--session" => session = it.next().cloned(),
            other => {
                eprintln!("tamga-mcp-proxy: noma'lum bayroq {other}");
                return usage();
            }
        }
    }
    let name = name.unwrap_or_else(|| {
        std::path::Path::new(program)
            .file_stem()
            .map_or_else(|| "server".into(), |s| s.to_string_lossy().into_owned())
    });
    let session = session.unwrap_or_else(|| {
        let ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis();
        format!("mcp-{name}-{ms}-{}", std::process::id())
    });

    let child = spawn(program, program_args);
    let child = match child {
        Ok(c) => c,
        Err(e) => {
            eprintln!("tamga-mcp-proxy: `{program}` ishga tushmadi: {e}");
            return ExitCode::from(1);
        }
    };
    relay::run(relay::Config::new(name, session), child)
}

/// Serverni ishga tushiradi. Windows'da `npx`, `uvx` kabi `.cmd` skriptlari to'g'ridan-to'g'ri
/// topilmaydi — topilmasa `cmd /c` orqali qayta uriniladi.
fn spawn(program: &str, args: &[String]) -> std::io::Result<std::process::Child> {
    let attempt = |p: &str, a: &[String]| {
        std::process::Command::new(p)
            .args(a)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
    };
    match attempt(program, args) {
        Err(e) if cfg!(windows) && e.kind() == std::io::ErrorKind::NotFound => {
            let mut a = vec!["/c".to_owned(), program.to_owned()];
            a.extend_from_slice(args);
            attempt("cmd", &a)
        }
        r => r,
    }
}
