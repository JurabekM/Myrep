//! `mpay-smsgw` CLI: virtual SMS shlyuzini ishga tushiradi (faqat sinov va demo).
#![forbid(unsafe_code)]

use std::net::SocketAddr;

use clap::Parser;

#[derive(Parser)]
#[command(name = "mpay-smsgw", about = "M-Pay virtual SMS shlyuzi (sinov uchun)")]
struct Cli {
    /// Tinglash manzili.
    #[arg(long, default_value = "127.0.0.1:47700")]
    listen: SocketAddr,
    /// Bearer token saqlanadigan muhit o'zgaruvchisi (`mpay-server` dagi `otp.webhook.token_env` bilan bir xil).
    #[arg(long, default_value = "MPAY_SMS_TOKEN")]
    token_env: String,
    /// Tokensiz ishlash (faqat lokal sinov).
    #[arg(long)]
    no_auth: bool,
}

#[tokio::main]
async fn main() -> Result<(), String> {
    tracing_subscriber::fmt()
        .with_env_filter(std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into()))
        .init();
    let cli = Cli::parse();
    let token = if cli.no_auth {
        None
    } else {
        Some(std::env::var(&cli.token_env).map_err(|_| {
            format!(
                "{} muhit o'zgaruvchisi yo'q (yoki --no-auth)",
                cli.token_env
            )
        })?)
    };
    let gw = mpay_smsgw::spawn(cli.listen, mpay_smsgw::Gateway::new(token))
        .await
        .map_err(|e| format!("{}: {e}", cli.listen))?;
    tracing::info!(addr = %gw.addr, "smsgw: tinglayapti (POST /send, GET /messages)");
    tokio::signal::ctrl_c().await.map_err(|e| e.to_string())?;
    Ok(())
}
