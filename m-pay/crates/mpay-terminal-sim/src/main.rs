//! `mpay-tsim` — dasturiy terminal va soft-wallet CLI (telefonsiz namoyish).
//!
//! ```text
//! mpay-tsim provision --pan 9900121000010014 --expiry 3112
//! mpay-tsim tap --amount 12500.00 --merchant SHOP0000000001
//! mpay-tsim replenish
//! mpay-tsim status
//! ```
#![forbid(unsafe_code)]
#![allow(clippy::print_stdout)]

use std::path::{Path, PathBuf};
use std::process::ExitCode;

use clap::{Parser, Subcommand};
use mpay_common::api::{
    AuthorizationRequest, AuthorizationResponse, ProvisionResponse, SandboxOtp,
};
use mpay_common::ports::SecurityLevel;
use mpay_common::TokenId;
use mpay_pqlink::sandbox::{SandboxAttestationCa, SoftDeviceKey};
use mpay_pqlink::DeviceSigner;
use mpay_terminal_sim::apdu::Loopback;
use mpay_terminal_sim::card::{CardPolicy, CardProfile, SoftCard};
use mpay_terminal_sim::http::ServerClient;
use mpay_terminal_sim::state::{next_terminal_stan, StoredToken, WalletState};
use mpay_terminal_sim::terminal::{self, TxnParams};
use mpay_terminal_sim::wallet::SoftWallet;
use mpay_terminal_sim::WalletError;
use zeroize::Zeroizing;

#[derive(Parser)]
#[command(
    name = "mpay-tsim",
    version,
    about = "M-Pay dasturiy terminal va soft-wallet (sandbox)"
)]
struct Cli {
    /// Server manzili.
    #[arg(
        long,
        global = true,
        env = "MPAY_SERVER",
        default_value = "http://127.0.0.1:8080"
    )]
    server: String,
    /// Sandbox katalogi (`mpay-server init` natijasi): CA, TLS sertifikati, API kalitlari.
    #[arg(long, global = true, env = "MPAY_SANDBOX_DIR", default_value = ".mpay")]
    sandbox: PathBuf,
    /// Soft-wallet holat fayli.
    #[arg(long, global = true, default_value = ".mpay/tsim-wallet.json")]
    wallet: PathBuf,
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Kartani tokenlashtiradi (YELLOW bo'lsa sandbox OTP avtomatik olinadi).
    Provision {
        #[arg(long)]
        pan: String,
        #[arg(long)]
        expiry: String,
    },
    /// Tap: loopback soft-karta → terminal → `/v1/authorizations`.
    Tap {
        /// Summa so'mda, masalan `12500.00`.
        #[arg(long)]
        amount: String,
        #[arg(long, default_value = "SHOP0000000001")]
        merchant: String,
        #[arg(long, default_value = "TERM0001")]
        terminal: String,
        #[arg(long)]
        token: Option<String>,
        /// Biometrik tasdiq (CDCVM) simulyatsiyasi.
        #[arg(long)]
        cdcvm: bool,
    },
    /// LUK'larni to'ldiradi.
    Replenish {
        #[arg(long)]
        token: Option<String>,
    },
    /// Hamyondagi tokenlar (maskalangan).
    Status,
}

fn creds(dir: &Path, key: &str) -> Result<Zeroizing<String>, WalletError> {
    let p = dir.join("dev-credentials.env");
    let txt = Zeroizing::new(
        std::fs::read_to_string(&p)
            .map_err(|e| WalletError::Config(format!("{}: {e}", p.display())))?,
    );
    txt.lines()
        .find_map(|l| {
            l.strip_prefix(&format!("{key}="))
                .map(|v| Zeroizing::new(v.trim().to_owned()))
        })
        .ok_or_else(|| WalletError::Config(format!("{key} topilmadi")))
}

/// Sandbox: Play Integrity o'rnida mock token — emulyatordagi demo ilova kabi operator endpointidan
/// (P2.6, ADR-0021). `[integrity] mode = "off"` bo'lsa (404) tokensiz.
async fn sandbox_integrity_token(cli: &Cli, w: &SoftWallet) -> Result<Option<String>, WalletError> {
    let op = creds(&cli.sandbox, "MPAY_OPERATOR_KEY")?;
    let req = mpay_common::api::SandboxIntegrityRequest {
        request_hash: w.integrity_request_hash()?,
        preset: None,
    };
    match client_as(cli, Some("operator-1"))?
        .post_json::<_, mpay_common::api::SandboxIntegrityResponse>(
            "/v1/sandbox/integrity-token",
            Some(&op),
            &req,
        )
        .await
    {
        Ok(r) => Ok(Some(r.integrity_token)),
        Err(WalletError::Api { status: 404, .. }) => Ok(None),
        Err(e) => Err(e),
    }
}

fn client(cli: &Cli) -> Result<ServerClient, WalletError> {
    client_as(cli, None)
}

/// `id` — API kaliti ID'si (`operator-1`, `terminal-1`): TLS'da sandbox katalogidagi
/// `<id>.crt.pem` / `<id>.key.pem` mTLS sertifikati sifatida ko'rsatiladi (bo'lsa).
fn client_as(cli: &Cli, id: Option<&str>) -> Result<ServerClient, WalletError> {
    if !cli.server.starts_with("https://") {
        return ServerClient::new(&cli.server, None);
    }
    let read = |name: &str| {
        std::fs::read(cli.sandbox.join(name))
            .map_err(|e| WalletError::Config(format!("{name}: {e}")))
    };
    let pem = read("tls-cert.pem")?;
    let identity = match id {
        Some(id) if cli.sandbox.join(format!("{id}.crt.pem")).exists() => Some((
            read(&format!("{id}.crt.pem"))?,
            Zeroizing::new(read(&format!("{id}.key.pem"))?),
        )),
        _ => None,
    };
    ServerClient::with_identity(
        &cli.server,
        Some(&pem),
        identity.as_ref().map(|(c, k)| (c.as_slice(), k.as_slice())),
    )
}

fn parse_amount(s: &str) -> Result<u64, WalletError> {
    let bad = || WalletError::Config("summa formati: 12500 yoki 12500.50".into());
    let (whole, frac) = s.split_once('.').unwrap_or((s, "0"));
    if frac.len() > 2 || whole.is_empty() {
        return Err(bad());
    }
    let w: u64 = whole.parse().map_err(|_| bad())?;
    let f: u64 = format!("{frac:0<2}").parse().map_err(|_| bad())?;
    w.checked_mul(100)
        .and_then(|v| v.checked_add(f))
        .ok_or_else(bad)
}

fn device_of(st: &WalletState) -> Result<SoftDeviceKey, WalletError> {
    let k = Zeroizing::new(
        hex::decode(st.device_key_pkcs8.as_str())
            .map_err(|_| WalletError::Decode("qurilma kaliti"))?,
    );
    let chain = st
        .device_chain
        .iter()
        .map(|c| hex::decode(c).map_err(|_| WalletError::Decode("zanjir")))
        .collect::<Result<_, _>>()?;
    Ok(SoftDeviceKey::from_parts(&k, chain)?)
}

/// Hamyonni yuklaydi yoki yangisini yaratadi (sandbox CA bilan StrongBox qurilma, TOFU pinlash).
async fn load_or_create(cli: &Cli, c: &ServerClient) -> Result<WalletState, WalletError> {
    if cli.wallet.exists() {
        return WalletState::load(&cli.wallet);
    }
    let key = std::fs::read_to_string(cli.sandbox.join("sandbox-attestation-ca.key.pem"))
        .map_err(|e| WalletError::Config(format!("sandbox CA kaliti: {e}")))?;
    let der = std::fs::read(cli.sandbox.join("sandbox-attestation-root.der"))
        .map_err(|e| WalletError::Config(format!("sandbox CA: {e}")))?;
    let ca = SandboxAttestationCa::from_parts(&key, der)?;
    // P1.7: yangi qurilma kaliti server nonce'i bilan (attestationChallenge) yaratiladi.
    let nonce = c.enroll_nonce().await?;
    let dev = ca.issue_device(SecurityLevel::StrongBox, &nonce)?;
    let (pk, chain) = dev.to_parts()?;
    let (_, fp) = c.identity().await?;
    println!("Yangi soft-wallet. Server pinlandi (TOFU): {fp}");
    Ok(WalletState {
        server_fingerprint: fp,
        device_key_pkcs8: Zeroizing::new(hex::encode(&pk[..])),
        device_chain: chain.iter().map(hex::encode).collect(),
        tokens: vec![],
    })
}

async fn connected_wallet(c: &ServerClient, st: &WalletState) -> Result<SoftWallet, WalletError> {
    let (id, fp) = c.identity().await?;
    if fp != st.server_fingerprint {
        return Err(WalletError::Config(format!(
            "server barmoq izi o'zgargan: {fp} ≠ pinlangan {}",
            st.server_fingerprint
        )));
    }
    let dev = device_of(st)?;
    let _ = dev.cert_chain();
    let mut w = SoftWallet::new(c.clone(), id, dev);
    let device = w.connect().await?;
    println!(
        "PQ Link sessiyasi o'rnatildi (X25519+ML-KEM-768, Ed25519+ML-DSA-65), qurilma {device}"
    );
    Ok(w)
}

fn token_arg(t: &Option<String>) -> Result<Option<TokenId>, WalletError> {
    t.as_deref()
        .map(|s| TokenId::parse(s).ok_or(WalletError::Config("token_id formati".into())))
        .transpose()
}

async fn run(cli: Cli) -> Result<(), WalletError> {
    let c = client(&cli)?;
    match &cli.cmd {
        Cmd::Provision { pan, expiry } => {
            let mut st = load_or_create(&cli, &c).await?;
            let mut w = connected_wallet(&c, &st).await?;
            let token = sandbox_integrity_token(&cli, &w).await?;
            let profile = match w.provision_with(pan, expiry, token).await? {
                ProvisionResponse::Active { profile, idv } => {
                    println!(
                        "ID&V: {:?} (skor {}) {:?}",
                        idv.decision, idv.score, idv.reasons
                    );
                    profile
                }
                ProvisionResponse::PendingIdv {
                    token_id,
                    challenge_id,
                    idv,
                    ..
                } => {
                    println!(
                        "ID&V: {:?} — OTP talab qilinadi (sandbox: operator endpointidan olinadi)",
                        idv.decision
                    );
                    let op = creds(&cli.sandbox, "MPAY_OPERATOR_KEY")?;
                    let otp: SandboxOtp = client_as(&cli, Some("operator-1"))?
                        .get_json(&format!("/v1/sandbox/otp/{challenge_id}"), Some(&op))
                        .await?;
                    w.verify_otp(&token_id, &challenge_id, &otp.otp).await?
                }
                ProvisionResponse::Declined { idv } => {
                    println!(
                        "RAD ETILDI: ID&V {:?} (skor {}) {:?}",
                        idv.decision, idv.score, idv.reasons
                    );
                    return Ok(());
                }
            };
            let card =
                CardProfile::from_dto(&profile).map_err(|e| WalletError::Config(e.into()))?;
            println!(
                "Token {} faol: DPAN {}, {} ta LUK",
                card.token_id,
                card.dpan.masked(),
                card.luks.len()
            );
            let mut stored = StoredToken::from_profile(&card);
            stored.cvm_limit_minor = profile.cvm_limit_minor;
            st.upsert(stored);
            st.save(&cli.wallet)?;
        }
        Cmd::Tap {
            amount,
            merchant,
            terminal: tid,
            token,
            cdcvm,
        } => {
            let mut st = WalletState::load(&cli.wallet)?;
            let stored = st.token(token_arg(token)?.as_ref())?.clone();
            // CVM chegarasi — bank siyosati (server bergan), bo'lmasa karta standarti.
            let mut policy = CardPolicy::default();
            if let Some(l) = stored.cvm_limit_minor {
                policy.cdcvm_limit_minor = l;
            }
            let mut card = SoftCard::new(stored.to_profile()?, policy);
            card.set_cdcvm_verified(*cdcvm);
            let amount = parse_amount(amount)?;
            let tap = {
                let mut lb = Loopback::new(&mut card);
                terminal::tap(&mut lb, &TxnParams::purchase(amount)).map_err(|e| {
                    if e.is_see_phone() {
                        WalletError::Card(format!(
                            "{e} — telefonda tasdiqlang (biometriya: --cdcvm)"
                        ))
                    } else {
                        WalletError::Card(e.to_string())
                    }
                })?
            };
            // ATC va LUK foydalanishi o'zgardi — natijadan qat'i nazar saqlaymiz.
            let mut updated = StoredToken::from_profile(card.profile());
            updated.cvm_limit_minor = stored.cvm_limit_minor;
            st.upsert(updated);
            st.save(&cli.wallet)?;
            let stan = next_terminal_stan(&cli.sandbox, tid)?;
            println!("Tap: {} ATC={}", tap.dpan_masked, tap.atc);
            let key = creds(&cli.sandbox, "MPAY_TERMINAL_KEY")?;
            let req = AuthorizationRequest {
                terminal_id: tid.clone(),
                merchant_id: merchant.clone(),
                stan,
                icc_data: tap.icc_hex(),
            };
            let r: AuthorizationResponse = client_as(&cli, Some("terminal-1"))?
                .post_json("/v1/authorizations", Some(&key), &req)
                .await?;
            let arpc_ok = r
                .issuer_auth_data
                .as_deref()
                .and_then(|h| hex::decode(h).ok())
                .map(|b| card.verify_issuer_auth(&b));
            println!(
                "{} — kod {} ({}), summa {}.{:02} UZS, RRN {}, risk {:?}, ARPC: {}",
                if r.approved {
                    "TASDIQLANDI"
                } else {
                    "RAD ETILDI"
                },
                r.response_code,
                r.reason,
                r.amount_minor / 100,
                r.amount_minor % 100,
                r.rrn,
                r.risk_score,
                match arpc_ok {
                    Some(true) => "to'g'ri",
                    Some(false) => "NOTO'G'RI",
                    None => "yo'q",
                }
            );
        }
        Cmd::Replenish { token } => {
            let mut st = WalletState::load(&cli.wallet)?;
            let mut stored = st.token(token_arg(token)?.as_ref())?.clone();
            let mut w = connected_wallet(&c, &st).await?;
            let r = w.replenish(&stored.token_id).await?;
            stored.add_luks(&r.luks);
            if r.cvm_limit_minor.is_some() {
                stored.cvm_limit_minor = r.cvm_limit_minor;
            }
            println!("{} ta yangi LUK", r.luks.len());
            st.upsert(stored);
            st.save(&cli.wallet)?;
        }
        Cmd::Status => {
            let st = WalletState::load(&cli.wallet)?;
            println!("Server: {}", st.server_fingerprint);
            let now = time::OffsetDateTime::now_utc().unix_timestamp();
            for t in &st.tokens {
                let p = t.to_profile()?;
                let usable = p
                    .luks
                    .iter()
                    .filter(|l| l.uses_left > 0 && l.expires_at > now)
                    .count();
                println!(
                    "  {} {} ATC={} LUK: {usable}/{} yaroqli",
                    t.token_id,
                    p.dpan.masked(),
                    t.atc,
                    p.luks.len()
                );
            }
        }
    }
    Ok(())
}

#[tokio::main]
async fn main() -> ExitCode {
    tracing_subscriber::fmt()
        .with_writer(std::io::stderr)
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(|_| "warn".into()),
        )
        .init();
    match run(Cli::parse()).await {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("xato: {e}");
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::parse_amount;

    #[test]
    fn amounts() {
        assert_eq!(parse_amount("12500").unwrap(), 1_250_000);
        assert_eq!(parse_amount("12500.5").unwrap(), 1_250_050);
        assert_eq!(parse_amount("0.01").unwrap(), 1);
        assert!(parse_amount("1.234").is_err());
        assert!(parse_amount("abc").is_err());
    }
}
