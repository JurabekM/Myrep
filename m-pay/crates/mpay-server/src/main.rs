//! `mpay-server` CLI.
#![forbid(unsafe_code)]
#![allow(clippy::print_stdout)]

use std::net::SocketAddr;
use std::path::PathBuf;
use std::process::ExitCode;

use clap::{Parser, Subcommand};
use mpay_server::config::Config;
use tracing_subscriber::EnvFilter;

#[derive(Parser)]
#[command(name = "mpay-server", version, about = "M-Pay Pay Sandbox serveri")]
struct Cli {
    /// Loglarni JSON formatida chiqarish.
    #[arg(long, global = true)]
    log_json: bool,
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Sandbox katalogini yaratadi: kalitlar, CA, API kalitlari, mpay.toml.
    Init {
        #[arg(long, default_value = ".mpay")]
        dir: PathBuf,
        #[arg(long, default_value = "127.0.0.1:8080")]
        listen: SocketAddr,
        /// O'z-o'zini imzolagan TLS sertifikati yaratish.
        #[arg(long)]
        tls: bool,
        #[arg(long)]
        force: bool,
        /// `memory` yoki `pkcs11`.
        #[arg(long, default_value = "memory")]
        keystore: String,
    },
    /// Serverni ishga tushiradi.
    Serve {
        #[arg(long, env = "MPAY_CONFIG", default_value = ".mpay/mpay.toml")]
        config: PathBuf,
    },
    /// Audit log xesh-zanjirini tekshiradi.
    AuditVerify {
        #[arg(long, env = "MPAY_CONFIG", default_value = ".mpay/mpay.toml")]
        config: PathBuf,
    },
    /// Android `terminal-app` uchun paket (JSON): server pini, mTLS sertifikati va terminal kaliti.
    /// Faqat `init --tls` sandbox'i uchun; faylda sirlar bor.
    TerminalBundle {
        #[arg(long, env = "MPAY_CONFIG", default_value = ".mpay/mpay.toml")]
        config: PathBuf,
        /// Terminal API kaliti ID'si (mTLS sertifikati CN'i).
        #[arg(long, default_value = "terminal-1")]
        id: String,
        /// Terminal ulanadigan manzil, masalan `https://192.168.1.10:8443`.
        #[arg(long)]
        url: String,
        #[arg(long, default_value = "terminal-bundle.json")]
        out: PathBuf,
    },
    /// PQ Link server identifikatorini chiqaradi (qurilmalarda pinlash uchun).
    Identity {
        #[arg(long, env = "MPAY_CONFIG", default_value = ".mpay/mpay.toml")]
        config: PathBuf,
    },
}

fn init_logging(json: bool) {
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));
    let b = tracing_subscriber::fmt()
        .with_writer(std::io::stderr)
        .with_env_filter(filter)
        .with_target(false)
        .with_ansi(std::io::IsTerminal::is_terminal(&std::io::stderr()));
    if json {
        b.json().init();
    } else {
        b.init();
    }
}

async fn run(cli: Cli) -> Result<(), String> {
    match cli.cmd {
        Cmd::Init {
            dir,
            listen,
            tls,
            force,
            keystore,
        } => {
            let keystore = match keystore.as_str() {
                "memory" => mpay_server::config::KeyStoreBackend::Memory,
                "pkcs11" => mpay_server::config::KeyStoreBackend::Pkcs11,
                _ => return Err("--keystore: memory yoki pkcs11".into()),
            };
            let out = mpay_server::init::run(&mpay_server::init::InitOptions {
                dir,
                listen,
                tls,
                force,
                keystore,
            })?;
            println!("Sandbox tayyor: {}", out.config_path.display());
            println!("PQ Link server barmoq izi: {}", out.server_fingerprint);
            println!(
                "API kalitlari (faqat bir marta ko'rsatiladi, dev-credentials.env ga ham yozildi):"
            );
            println!("  operator: {}", out.operator_key.as_str());
            println!("  terminal: {}", out.terminal_key.as_str());
            Ok(())
        }
        Cmd::Serve { config } => {
            let cfg = Config::load(&config).map_err(|e| e.to_string())?;
            let mut srv = mpay_server::start(&cfg).await?;
            tokio::signal::ctrl_c().await.map_err(|e| e.to_string())?;
            tracing::info!("to'xtatilmoqda");
            srv.shutdown();
            let _ = srv.handle.await;
            Ok(())
        }
        Cmd::AuditVerify { config } => {
            let cfg = Config::load(&config).map_err(|e| e.to_string())?;
            let st = mpay_server::state::build(&cfg)
                .await
                .map_err(|e| e.to_string())?;
            let r = st.vault.verify_audit().await.map_err(|e| e.to_string())?;
            println!(
                "audit zanjiri to'g'ri: {} yozuv, bosh xesh {}",
                r.entries, r.head_hash
            );
            Ok(())
        }
        Cmd::TerminalBundle {
            config,
            id,
            url,
            out,
        } => {
            let cfg = Config::load(&config).map_err(|e| e.to_string())?;
            let json = mpay_server::init::terminal_bundle(&cfg.base_dir, &id, &url)?;
            std::fs::write(&out, json.as_bytes()).map_err(|e| format!("{}: {e}", out.display()))?;
            println!(
                "Terminal paketi: {} (SIRLAR BOR — import qilingach o'chiring)",
                out.display()
            );
            Ok(())
        }
        Cmd::Identity { config } => {
            let cfg = Config::load(&config).map_err(|e| e.to_string())?;
            let st = mpay_server::state::build(&cfg)
                .await
                .map_err(|e| e.to_string())?;
            let id = st.pqlink.identity();
            println!("fingerprint: {}", hex::encode(id.fingerprint()));
            println!("ed25519:     {}", hex::encode(id.ed25519));
            Ok(())
        }
    }
}

#[tokio::main]
async fn main() -> ExitCode {
    let cli = Cli::parse();
    init_logging(cli.log_json);
    match run(cli).await {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            tracing::error!("{e}");
            ExitCode::FAILURE
        }
    }
}
