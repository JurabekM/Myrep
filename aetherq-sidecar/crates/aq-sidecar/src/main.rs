//! aq-sidecar — AETHER-Q proksi (mahalliy oddiy TCP ↔ post-kvant tunel).
//!
//! Buyruqlar:
//!   aq-sidecar keygen   --out FILE                       identity yaratadi (FILE + FILE.pub)
//!   aq-sidecar pubkey   --identity FILE                  ochiq kalit (hex)
//!   aq-sidecar serve    --listen ADDR --upstream ADDR --identity FILE
//!                       [--allow FILE] [--require-client-auth]
//!   aq-sidecar connect  --listen ADDR --peer ADDR --server-pub FILE|HEX
//!                       [--identity FILE]

mod proxy;

use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::sync::Arc;
use std::thread;

use aq_core::dos::PuzzleAuthority;
use aq_core::identity::{load_allowlist, load_public_key, to_hex};
use aq_core::net::SessionCache;
use aq_core::ticket::TicketAuthority;
use aq_core::{Identity, PROTOCOL_VERSION};

fn usage() -> ExitCode {
    eprintln!(
        "aq-sidecar {} (AETHER-Q {:#06x})\n\n\
         buyruqlar:\n\
         \x20 keygen   --out FILE\n\
         \x20 pubkey   --identity FILE\n\
         \x20 serve    --listen ADDR --upstream ADDR --identity FILE [--allow FILE] [--require-client-auth]\n\
         \x20 connect  --listen ADDR --peer ADDR --server-pub FILE|HEX [--identity FILE]",
        env!("CARGO_PKG_VERSION"),
        PROTOCOL_VERSION
    );
    ExitCode::from(2)
}

/// `--key VALUE` juftliklarini ajratadi; bayroqlar (`--flag`) qiymatsiz.
struct Args {
    cmd: String,
    kv: Vec<(String, String)>,
    flags: Vec<String>,
}

impl Args {
    fn parse(argv: &[String]) -> Option<Self> {
        let cmd = argv.first()?.clone();
        let mut kv = Vec::new();
        let mut flags = Vec::new();
        let mut i = 1;
        while i < argv.len() {
            let a = &argv[i];
            if !a.starts_with("--") {
                return None;
            }
            let key = a.trim_start_matches("--").to_string();
            if key == "require-client-auth" || key == "no-resume" || key == "resume" {
                flags.push(key);
                i += 1;
            } else {
                let v = argv.get(i + 1)?.clone();
                kv.push((key, v));
                i += 2;
            }
        }
        Some(Self { cmd, kv, flags })
    }

    fn get(&self, k: &str) -> Option<&str> {
        self.kv.iter().find(|(a, _)| a == k).map(|(_, v)| v.as_str())
    }

    fn has(&self, f: &str) -> bool {
        self.flags.iter().any(|x| x == f)
    }
}

fn err(msg: impl std::fmt::Display) -> ExitCode {
    eprintln!("aq-sidecar: {msg}");
    ExitCode::FAILURE
}

fn main() -> ExitCode {
    let argv: Vec<String> = std::env::args().skip(1).collect();
    if argv.is_empty() || argv[0] == "--help" || argv[0] == "-h" {
        return usage();
    }
    if argv[0] == "version" {
        println!("aq-sidecar {} (AETHER-Q {:#06x})", env!("CARGO_PKG_VERSION"), PROTOCOL_VERSION);
        return ExitCode::SUCCESS;
    }
    let Some(args) = Args::parse(&argv) else {
        return usage();
    };
    match args.cmd.as_str() {
        "keygen" => cmd_keygen(&args),
        "pubkey" => cmd_pubkey(&args),
        "serve" => cmd_serve(&args),
        "connect" => cmd_connect(&args),
        _ => usage(),
    }
}

fn load_identity(path: &str) -> Result<Identity, String> {
    Identity::load(Path::new(path)).map_err(|e| format!("identity {path}: {e}"))
}

fn cmd_keygen(a: &Args) -> ExitCode {
    let Some(out) = a.get("out") else {
        return usage();
    };
    let id = match Identity::generate() {
        Ok(i) => i,
        Err(e) => return err(e),
    };
    let path = PathBuf::from(out);
    if let Err(e) = id.save(&path) {
        return err(format!("saqlab bo'lmadi: {e}"));
    }
    let pub_path = PathBuf::from(format!("{out}.pub"));
    if let Err(e) = id.save_public(&pub_path) {
        return err(format!("ochiq kalit saqlanmadi: {e}"));
    }
    println!("{}", to_hex(&id.pk));
    eprintln!("aq-sidecar: identity yozildi: {out} (maxfiy), {out}.pub (ochiq)");
    ExitCode::SUCCESS
}

fn cmd_pubkey(a: &Args) -> ExitCode {
    let Some(path) = a.get("identity") else {
        return usage();
    };
    match load_identity(path) {
        Ok(id) => {
            println!("{}", to_hex(&id.pk));
            ExitCode::SUCCESS
        }
        Err(e) => err(e),
    }
}

fn cmd_serve(a: &Args) -> ExitCode {
    let (Some(listen), Some(upstream), Some(idp)) = (a.get("listen"), a.get("upstream"), a.get("identity")) else {
        return usage();
    };
    let id = match load_identity(idp) {
        Ok(i) => i,
        Err(e) => return err(e),
    };
    let allowed = match a.get("allow") {
        Some(p) => match load_allowlist(Path::new(p)) {
            Ok(v) => Some(v),
            Err(e) => return err(format!("allowlist {p}: {e}")),
        },
        None => None,
    };
    let require = a.has("require-client-auth");
    if require && allowed.is_none() {
        eprintln!("aq-sidecar: ogohlantirish: --require-client-auth allowlist'siz (har qanday to'g'ri imzo qabul)");
    }
    let listener = match TcpListener::bind(listen) {
        Ok(l) => l,
        Err(e) => return err(format!("{listen}: {e}")),
    };
    // Resumption ticket kaliti va PoW puzzle — jarayon bo'yicha BIR MARTA (barcha ulanishlar uchun).
    let ticket_ttl: u64 = a.get("ticket-ttl").and_then(|v| v.parse().ok()).unwrap_or(3600);
    let tickets = if a.has("no-resume") {
        None
    } else {
        match TicketAuthority::random(ticket_ttl) {
            Ok(t) => Some(Arc::new(t)),
            Err(e) => return err(format!("ticket kaliti: {e}")),
        }
    };
    let pow: u8 = a.get("pow").and_then(|v| v.parse().ok()).unwrap_or(0);
    let puzzle = if pow == 0 {
        None
    } else {
        match PuzzleAuthority::random(pow, 30) {
            Ok(p) => Some(Arc::new(p)),
            Err(e) => return err(format!("puzzle: {e}")),
        }
    };
    eprintln!(
        "aq-sidecar: serve {listen} → upstream {upstream} (server={}, resumption={}, pow={})",
        proxy::fingerprint(&id.pk),
        tickets.is_some(),
        if pow == 0 { "o'chiq".to_string() } else { pow.to_string() }
    );
    for conn in listener.incoming() {
        match conn {
            Ok(stream) => {
                let cfg = proxy::server_cfg(id.clone(), require, allowed.clone(), tickets.clone(), puzzle.clone());
                let up = upstream.to_string();
                thread::spawn(move || proxy::serve_connection(stream, cfg, &up));
            }
            Err(e) => eprintln!("aq-sidecar: accept: {e}"),
        }
    }
    ExitCode::SUCCESS
}

fn cmd_connect(a: &Args) -> ExitCode {
    let (Some(listen), Some(peer), Some(spk)) = (a.get("listen"), a.get("peer"), a.get("server-pub")) else {
        return usage();
    };
    let server_pub = if Path::new(spk).exists() {
        match load_public_key(Path::new(spk)) {
            Ok(v) => v,
            Err(e) => return err(format!("server-pub {spk}: {e}")),
        }
    } else {
        match aq_core::identity::from_hex(spk) {
            Some(v) => v,
            None => return err("server-pub: fayl yoki hex emas"),
        }
    };
    let identity = match a.get("identity") {
        Some(p) => match load_identity(p) {
            Ok(i) => Some(i),
            Err(e) => return err(e),
        },
        None => None,
    };
    let listener = match TcpListener::bind(listen) {
        Ok(l) => l,
        Err(e) => return err(format!("{listen}: {e}")),
    };
    // Ticket keshi jarayon bo'yicha umumiy: ikkinchi ulanish resumption bilan ketadi.
    // Default: O'CHIQ — NST kutish serverda ticket bo'lishini talab qiladi (Python referens server
    // ticket'siz NST yubormaydi). Yoqish: --resume (server tomonida resumption yoqilgan bo'lishi kerak).
    let resume_enabled = a.has("resume");
    let cache = Arc::new(SessionCache::new());
    eprintln!(
        "aq-sidecar: connect {listen} → peer {peer} (server={}, resumption={})",
        proxy::fingerprint(&server_pub),
        resume_enabled
    );
    for conn in listener.incoming() {
        match conn {
            Ok(stream) => {
                let cfg = proxy::client_cfg(server_pub.clone(), identity.clone());
                let p = peer.to_string();
                let cache_arg = if resume_enabled {
                    Some((cache.clone(), proxy::cache_key(&p, &server_pub)))
                } else {
                    None
                };
                thread::spawn(move || proxy::connect_connection(stream, cfg, &p, cache_arg));
            }
            Err(e) => eprintln!("aq-sidecar: accept: {e}"),
        }
    }
    ExitCode::SUCCESS
}
