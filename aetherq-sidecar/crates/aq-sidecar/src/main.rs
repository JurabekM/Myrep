//! aq-sidecar — AETHER-Q proksi (mahalliy oddiy TCP ↔ post-kvant tunel).
//!
//! Buyruqlar:
//!   aq-sidecar keygen   --out FILE                       identity yaratadi (FILE + FILE.pub)
//!   aq-sidecar pubkey   --identity FILE                  ochiq kalit (hex)
//!   aq-sidecar serve    --listen ADDR --upstream ADDR --identity FILE
//!                       [--allow FILE] [--require-client-auth] [--no-resume] [--ticket-ttl N] [--pow D]
//!   aq-sidecar connect  --listen ADDR --peer ADDR --server-pub FILE|HEX
//!                       [--identity FILE] [--resume]
//!
//! Tunel mantig'i `aq_sidecar::runtime` da (GUI `aq-studio` ham shuni ishlatadi); bu fayl faqat CLI
//! argumentlari va log qatorlari.

use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::sync::Arc;

use aq_core::identity::{load_allowlist, load_public_key, to_hex};
use aq_core::{Identity, PROTOCOL_VERSION};
use aq_sidecar::runtime::{short_fp, ConnectOptions, Event, ServeOptions, Sink, Tunnel};

fn usage() -> ExitCode {
    eprintln!(
        "aq-sidecar {} (AETHER-Q {:#06x})\n\n\
         buyruqlar:\n\
         \x20 keygen   --out FILE\n\
         \x20 pubkey   --identity FILE\n\
         \x20 serve    --listen ADDR --upstream ADDR --identity FILE [--allow FILE] [--require-client-auth]\n\
         \x20          [--no-resume] [--ticket-ttl N] [--pow D]\n\
         \x20 connect  --listen ADDR --peer ADDR --server-pub FILE|HEX [--identity FILE] [--resume]",
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

/// Umumiy log qatorlari (ikkala rejim).
fn log_common(e: &Event) {
    match e {
        Event::RecordError { error } => eprintln!("aq-sidecar: record xatosi: {error}"),
        Event::AcceptError { error } => eprintln!("aq-sidecar: accept: {error}"),
        _ => {}
    }
}

/// Server log'i (oldingi CLI bilan bir xil qatorlar — interop va yuk sinovi skriptlari ularni o'qiydi).
fn serve_sink() -> Sink {
    Arc::new(|e: Event| match &e {
        Event::Accepted { peer, client_pk: Some(pk), .. } => eprintln!("aq-sidecar: ulandi {peer} klient={}", short_fp(pk)),
        Event::Accepted { peer, client_pk: None, .. } => {
            eprintln!("aq-sidecar: ulandi {peer} (klient autentifikatsiyasiz)")
        }
        Event::HandshakeFailed { peer, error, .. } => eprintln!("aq-sidecar: handshake rad etildi ({peer}): {error}"),
        Event::DialFailed { target, error, .. } => eprintln!("aq-sidecar: upstream {target} ga ulanmadi: {error}"),
        other => log_common(other),
    })
}

/// Klient log'i.
fn connect_sink() -> Sink {
    Arc::new(|e: Event| match &e {
        Event::Opened { peer, resumed, .. } => {
            eprintln!("aq-sidecar: tunel ochildi → {peer}{}", if *resumed { " (resumption)" } else { "" })
        }
        Event::HandshakeFailed { peer, error, .. } => eprintln!("aq-sidecar: handshake muvaffaqiyatsiz ({peer}): {error}"),
        Event::DialFailed { target, error, .. } => eprintln!("aq-sidecar: peer {target} ga ulanmadi: {error}"),
        other => log_common(other),
    })
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
    let pow: u8 = a.get("pow").and_then(|v| v.parse().ok()).unwrap_or(0);
    let opts = ServeOptions {
        listen: listen.to_string(),
        upstream: upstream.to_string(),
        identity: id.clone(),
        require_client_auth: require,
        allowed,
        resumption: !a.has("no-resume"),
        ticket_ttl: a.get("ticket-ttl").and_then(|v| v.parse().ok()).unwrap_or(3600),
        pow,
    };
    let resumption = opts.resumption;
    let tunnel = match Tunnel::serve(opts, serve_sink()) {
        Ok(t) => t,
        Err(e) => return err(e),
    };
    eprintln!(
        "aq-sidecar: serve {listen} → upstream {upstream} (server={}, resumption={resumption}, pow={})",
        short_fp(&id.pk),
        if pow == 0 { "o'chiq".to_string() } else { pow.to_string() }
    );
    tunnel.wait();
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
    // Default: resumption O'CHIQ — NST kutish serverda ticket bo'lishini talab qiladi (Python referens server
    // ticket'siz NST yubormaydi). Yoqish: --resume (server tomonida resumption yoqilgan bo'lishi kerak).
    let resume = a.has("resume");
    let fp = short_fp(&server_pub);
    let opts =
        ConnectOptions { listen: listen.to_string(), peer: peer.to_string(), server_pub, identity, resume };
    let tunnel = match Tunnel::connect(opts, connect_sink()) {
        Ok(t) => t,
        Err(e) => return err(e),
    };
    eprintln!("aq-sidecar: connect {listen} → peer {peer} (server={fp}, resumption={resume})");
    tunnel.wait();
    ExitCode::SUCCESS
}
