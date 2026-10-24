//! `mpay-load` — `mpay-server` (alohida jarayon) uchun yuk generatori.
//!
//! `prepare`: `mpay-server init` papkasidagi `mpay.toml` ga N ta test hisob (FPAN `990012…`)
//! qo'shadi va LUK foydalanish limitini oshiradi (faqat yuk sinovi konfiguratsiyasi).
//! `run`: N ta kartani PQ Link orqali tokenlashtiradi (YELLOW bo'lsa sandbox OTP), so'ng
//! `--duration` soniya davomida C ta parallel ishchi bilan haqiqiy tap (soft-karta ARQC) →
//! `POST /v1/authorizations` yuboradi (keep-alive). Natija: kechikish foizliklari, o'tkazuvchanlik,
//! javob kodlari. Loglarga PAN yozilmaydi.
#![forbid(unsafe_code)]
// CLI: natija stdout/stderr ga.
#![allow(clippy::print_stdout, clippy::print_stderr)]

use std::collections::BTreeMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

use clap::{Parser, Subcommand};
use mpay_common::api::{AuthorizationRequest, AuthorizationResponse, ProvisionResponse};
use mpay_common::ports::SecurityLevel;
use mpay_pqlink::sandbox::SandboxAttestationCa;
use mpay_terminal_sim::apdu::Loopback;
use mpay_terminal_sim::card::{CardPolicy, CardProfile, SoftCard};
use mpay_terminal_sim::http::ServerClient;
use mpay_terminal_sim::terminal::{tap, TxnParams};
use mpay_terminal_sim::wallet::SoftWallet;
use mpay_terminal_sim::WalletError;

#[derive(Parser)]
#[command(name = "mpay-load", about = "mpay-server yuk sinovi (sandbox)")]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// `mpay.toml` ga yuk sinovi hisoblarini qo'shadi.
    Prepare {
        #[arg(long)]
        dir: PathBuf,
        #[arg(long, default_value_t = 200)]
        cards: u32,
    },
    /// Provisioning + avtorizatsiya yuklamasi.
    Run {
        #[arg(long)]
        dir: PathBuf,
        #[arg(long, default_value = "http://127.0.0.1:8080")]
        server: String,
        #[arg(long, default_value_t = 200)]
        cards: u32,
        /// Parallel provisioning va avtorizatsiya ishchilari.
        #[arg(long, default_value_t = 32)]
        concurrency: usize,
        /// Avtorizatsiya bosqichi davomiyligi, soniya.
        #[arg(long, default_value_t = 60)]
        duration: u64,
        /// Tap summasi, tiyin (standart 12 500,00 UZS — CDCVM chegarasidan past).
        #[arg(long, default_value_t = 1_250_000)]
        amount: u64,
        /// Natija JSON fayli.
        #[arg(long)]
        out: Option<PathBuf>,
    },
}

/// Yuk sinovi FPAN'i: `990012 77 <7 raqam>` + Luhn (fiktiv diapazon).
fn load_fpan(i: u32) -> String {
    mpay_common::Pan::from_prefix(&format!("99001277{i:07}"))
        .map(|p| p.expose_digits().to_owned())
        .unwrap_or_default()
}

fn prepare(dir: &std::path::Path, cards: u32) -> Result<(), String> {
    let path = dir.join("mpay.toml");
    let mut cfg = std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
    if cfg.contains("# mpay-load") {
        return Err("mpay.toml allaqachon tayyorlangan".into());
    }
    // Bir kartada uzoq yuklama: LUK limiti va partiyasi oshiriladi (FAQAT yuk sinovi).
    cfg = cfg.replace("max_uses = 10\n", "max_uses = 1000000\n");
    // Barcha soxta qurilmalar bitta IP'dan (127.0.0.1) — IP chegarasi yuk sinovida ko'tariladi.
    // Handshake parallelligi chegarasi (503 BUSY) o'zgarmaydi: generator Retry-After bilan qayta urinadi.
    cfg = cfg.replace(
        "ip_handshake_per_minute = 300 ",
        "ip_handshake_per_minute = 10000000 ",
    );
    cfg = cfg.replace(
        "ip_handshake_burst = 60\n",
        "ip_handshake_burst = 1000000\n",
    );
    cfg.push_str("\n# mpay-load: yuk sinovi hisoblari (fiktiv FPAN)\n");
    for i in 0..cards {
        cfg.push_str(&format!(
            "\n[[issuer.accounts]]\npan = \"{}\"\nbalance_minor = 900000000000000\nlabel = \"yuk sinovi #{i}\"\n",
            load_fpan(i)
        ));
    }
    std::fs::write(&path, cfg).map_err(|e| e.to_string())?;
    println!(
        "{} ta yuk sinovi hisobi qo'shildi: {}",
        cards,
        path.display()
    );
    Ok(())
}

fn credential(dir: &std::path::Path, name: &str) -> Result<String, String> {
    let env =
        std::fs::read_to_string(dir.join("dev-credentials.env")).map_err(|e| e.to_string())?;
    env.lines()
        .find_map(|l| l.strip_prefix(&format!("{name}=")))
        .map(str::to_owned)
        .ok_or_else(|| format!("{name} topilmadi"))
}

fn pct(sorted: &[u32], p: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let i = ((sorted.len() as f64 - 1.0) * p).round() as usize;
    f64::from(sorted[i]) / 1000.0
}

#[derive(Default)]
struct Stats {
    lat_us: Vec<u32>,
    codes: BTreeMap<String, u64>,
    errors: u64,
}

impl Stats {
    fn merge(&mut self, o: Stats) {
        self.lat_us.extend(o.lat_us);
        for (k, v) in o.codes {
            *self.codes.entry(k).or_default() += v;
        }
        self.errors += o.errors;
    }

    fn summary(&mut self, secs: f64) -> serde_json::Value {
        self.lat_us.sort_unstable();
        let n = self.lat_us.len();
        serde_json::json!({
            "count": n,
            "errors": self.errors,
            "seconds": (secs * 100.0).round() / 100.0,
            "throughput_per_s": ((n as f64 / secs) * 10.0).round() / 10.0,
            "p50_ms": pct(&self.lat_us, 0.50),
            "p95_ms": pct(&self.lat_us, 0.95),
            "p99_ms": pct(&self.lat_us, 0.99),
            "max_ms": pct(&self.lat_us, 1.0),
            "codes": self.codes,
        })
    }
}

/// Bitta kartani tokenlashtiradi (har biri alohida qurilma — haqiqiy hamyon kabi).
async fn provision_one(
    client: ServerClient,
    ca: Arc<SandboxAttestationCa>,
    operator: Arc<String>,
    i: u32,
) -> Result<(SoftCard, String), String> {
    let device = ca
        .issue_device(SecurityLevel::StrongBox, format!("load-{i}").as_bytes())
        .map_err(|e| e.to_string())?;
    let (identity, _) = client.identity().await.map_err(|e| e.to_string())?;
    let mut w = SoftWallet::new(client.clone(), identity, device);
    // Server band (503) yoki chegara (429) — real hamyon kabi kutib, qayta urinadi.
    let mut attempt: u64 = 0;
    loop {
        match w.connect().await {
            Ok(_) => break,
            Err(WalletError::Api {
                status: 503 | 429, ..
            }) if attempt < 30 => {
                attempt += 1;
                tokio::time::sleep(Duration::from_millis(100 * attempt.min(5))).await;
            }
            Err(e) => return Err(e.to_string()),
        }
    }
    let (profile, decision) = match w
        .provision(&load_fpan(i), "3112")
        .await
        .map_err(|e| e.to_string())?
    {
        ProvisionResponse::Active { profile, idv } => (profile, format!("{:?}", idv.decision)),
        ProvisionResponse::PendingIdv {
            token_id,
            challenge_id,
            idv,
            ..
        } => {
            let otp: serde_json::Value = client
                .get_json(
                    &format!("/v1/sandbox/otp/{challenge_id}"),
                    Some(operator.as_str()),
                )
                .await
                .map_err(|e| e.to_string())?;
            let otp = otp["otp"].as_str().ok_or("otp")?.to_owned();
            let p = w
                .verify_otp(&token_id, &challenge_id, &otp)
                .await
                .map_err(|e| e.to_string())?;
            (p, format!("{:?}+OTP", idv.decision))
        }
        ProvisionResponse::Declined { idv } => return Err(format!("rad: {:?}", idv.decision)),
    };
    let card = SoftCard::new(CardProfile::from_dto(&profile)?, CardPolicy::default());
    Ok((card, decision))
}

#[allow(clippy::too_many_arguments)]
async fn run(
    dir: PathBuf,
    server: String,
    cards: u32,
    concurrency: usize,
    duration: u64,
    amount: u64,
    out: Option<PathBuf>,
) -> Result<(), String> {
    let operator = Arc::new(credential(&dir, "MPAY_OPERATOR_KEY")?);
    let terminal = Arc::new(credential(&dir, "MPAY_TERMINAL_KEY")?);
    let key = std::fs::read_to_string(dir.join("sandbox-attestation-ca.key.pem"))
        .map_err(|e| e.to_string())?;
    let der = std::fs::read(dir.join("sandbox-attestation-root.der")).map_err(|e| e.to_string())?;
    let ca = Arc::new(SandboxAttestationCa::from_parts(&key, der).map_err(|e| e.to_string())?);
    let client = ServerClient::new(&server, None).map_err(|e| e.to_string())?;

    // 1) Provisioning: concurrency ta parallel hamyon.
    println!("Provisioning: {cards} karta, {concurrency} parallel…");
    let sem = Arc::new(tokio::sync::Semaphore::new(concurrency));
    let t0 = Instant::now();
    let mut set = tokio::task::JoinSet::new();
    for i in 0..cards {
        let (client, ca, op, sem) = (client.clone(), ca.clone(), operator.clone(), sem.clone());
        set.spawn(async move {
            let _p = sem.acquire_owned().await;
            let s = Instant::now();
            let r = provision_one(client, ca, op, i).await;
            (r, s.elapsed())
        });
    }
    let mut prov = Stats::default();
    let mut ready = Vec::new();
    while let Some(j) = set.join_next().await {
        let (r, el) = j.map_err(|e| e.to_string())?;
        match r {
            Ok((card, decision)) => {
                prov.lat_us
                    .push(el.as_micros().min(u128::from(u32::MAX)) as u32);
                *prov.codes.entry(decision).or_default() += 1;
                ready.push(card);
            }
            Err(e) => {
                prov.errors += 1;
                *prov.codes.entry(format!("xato: {e}")).or_default() += 1;
            }
        }
    }
    let prov_summary = prov.summary(t0.elapsed().as_secs_f64());
    println!(
        "{}",
        serde_json::to_string_pretty(&prov_summary).unwrap_or_default()
    );
    if ready.is_empty() {
        return Err("birorta karta tayyor emas".into());
    }

    // 2) Avtorizatsiya: har ishchi o'z kartalari to'plamiga ega (qulfsiz).
    let workers = concurrency.min(ready.len());
    let mut buckets: Vec<Vec<SoftCard>> = (0..workers).map(|_| Vec::new()).collect();
    for (i, c) in ready.into_iter().enumerate() {
        buckets[i % workers].push(c);
    }
    println!("Avtorizatsiya: {workers} ishchi, {duration} s…");
    let stan = Arc::new(AtomicU32::new(1));
    let deadline = Instant::now() + Duration::from_secs(duration);
    let t1 = Instant::now();
    let mut set = tokio::task::JoinSet::new();
    for (w, mut cards) in buckets.into_iter().enumerate() {
        let (client, terminal, stan) = (client.clone(), terminal.clone(), stan.clone());
        set.spawn(async move {
            let mut st = Stats::default();
            let merchant = format!("LOADSHOP{w:07}");
            let mut k = 0usize;
            while Instant::now() < deadline {
                let n = cards.len();
                let card = &mut cards[k % n];
                k += 1;
                let icc = match tap(&mut Loopback::new(card), &TxnParams::purchase(amount)) {
                    Ok(t) => t.icc_hex(),
                    Err(_) => {
                        st.errors += 1;
                        *st.codes.entry("tap xatosi".into()).or_default() += 1;
                        continue;
                    }
                };
                let req = AuthorizationRequest {
                    terminal_id: format!("LOAD{:04}", w % 10_000),
                    merchant_id: merchant.clone(),
                    stan: stan.fetch_add(1, Ordering::Relaxed) % 999_999 + 1,
                    icc_data: icc,
                };
                let s = Instant::now();
                let r: Result<AuthorizationResponse, _> = client
                    .post_json("/v1/authorizations", Some(terminal.as_str()), &req)
                    .await;
                let el = s.elapsed();
                match r {
                    Ok(a) => {
                        st.lat_us
                            .push(el.as_micros().min(u128::from(u32::MAX)) as u32);
                        *st.codes
                            .entry(format!("{} {}", a.response_code, a.reason))
                            .or_default() += 1;
                    }
                    Err(e) => {
                        st.errors += 1;
                        *st.codes.entry(format!("http: {e}")).or_default() += 1;
                    }
                }
            }
            st
        });
    }
    let mut auth = Stats::default();
    while let Some(j) = set.join_next().await {
        auth.merge(j.map_err(|e| e.to_string())?);
    }
    let auth_summary = auth.summary(t1.elapsed().as_secs_f64());
    println!(
        "{}",
        serde_json::to_string_pretty(&auth_summary).unwrap_or_default()
    );

    let report = serde_json::json!({
        "cards": cards,
        "concurrency": concurrency,
        "amount_minor": amount,
        "provisioning": prov_summary,
        "authorization": auth_summary,
    });
    if let Some(p) = out {
        std::fs::write(&p, serde_json::to_vec_pretty(&report).unwrap_or_default())
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();
    let r = match cli.cmd {
        Cmd::Prepare { dir, cards } => prepare(&dir, cards),
        Cmd::Run {
            dir,
            server,
            cards,
            concurrency,
            duration,
            amount,
            out,
        } => run(dir, server, cards, concurrency, duration, amount, out).await,
    };
    if let Err(e) = r {
        eprintln!("xato: {e}");
        std::process::exit(1);
    }
}
