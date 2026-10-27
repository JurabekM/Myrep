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
        /// TLS sertifikatiga qo'shimcha nom (SAN), takrorlanadi: `--tls-san lb --tls-san api-1`.
        #[arg(long = "tls-san")]
        tls_san: Vec<String>,
    },
    /// Serverni ishga tushiradi.
    Serve {
        #[arg(long, env = "MPAY_CONFIG", default_value = ".mpay/mpay.toml")]
        config: PathBuf,
    },
    /// Shield rolini ishga tushiradi (2-faza P2.4, ADR-0019): belgilar ombori yagona instansiyada,
    /// API instansiyalari `[shield] mode = "remote"` bilan murojaat qiladi. Faqat ichki API.
    Shield {
        #[arg(long, env = "MPAY_CONFIG", default_value = ".mpay/shield.toml")]
        config: PathBuf,
    },
    /// Bir martalik tayyorgarlik (2-faza P2.5): DB migratsiyalari va KeyStore/HSM kalitlari
    /// (`ensure_key`) — so'ng chiqadi. Ko'p instansiyada API'lar ishga tushishidan oldin bir marta,
    /// aks holda bir vaqtda yuklangan instansiyalar HSM'da bir xil yorliqli ikki kalit yaratishi mumkin.
    Bootstrap {
        #[arg(long, env = "MPAY_CONFIG", default_value = ".mpay/mpay.toml")]
        config: PathBuf,
    },
    /// Solishtirish (ADR-0024): acquirer jurnali ↔ emitent qaydnomasi. Tafovut bo'lsa — chiqish kodi 1
    /// (cron/navbatchi uchun).
    Recon {
        #[arg(long, env = "MPAY_CONFIG", default_value = ".mpay/mpay.toml")]
        config: PathBuf,
        /// Kun `YYYY-MM-DD` — sxema vaqti (UTC+5); standart — bugun.
        #[arg(long)]
        date: Option<String>,
        /// To'liq hisobot (JSON) fayli.
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Kunlik kliring va hisob-kitob (ADR-0025): paket → emitent → pozitsiyalar. Qayta ishga
    /// tushirish xavfsiz. Emitent yozuvlarni rad etsa — chiqish kodi 1.
    Clearing {
        #[arg(long, env = "MPAY_CONFIG", default_value = ".mpay/mpay.toml")]
        config: PathBuf,
        /// Kun `YYYY-MM-DD` — sxema vaqti (UTC+5); standart — kecha.
        #[arg(long)]
        date: Option<String>,
        /// Shu papkaga: kliring fayli, emitent tasdig'i, to'lovlar CSV va hisobot JSON.
        #[arg(long)]
        out_dir: Option<PathBuf>,
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
    /// Kalit almashtirish (P1.6): keyingi PQ Link identifikatorini yaratadi (Ed25519 — KeyStore'da,
    /// ML-DSA-65 — KEK bilan o'ralgan blob) va `[pqlink.next]` qatorlarini chiqaradi.
    IdentityNext {
        #[arg(long, env = "MPAY_CONFIG", default_value = ".mpay/mpay.toml")]
        config: PathBuf,
        /// Versiya raqami: yorliq `mpay.srv-ed25519.v<N>`, blob `pqlink-mldsa65.v<N>.blob`.
        #[arg(long)]
        version: u32,
    },
    /// Oflayn ildiz kaliti (ADR-0014): faqat imzolash stansiyasida yarating va saqlang.
    RootKeygen {
        #[arg(long)]
        out: PathBuf,
    },
    /// Bekor qilingan server identifikatorlari ro'yxatini ildiz kaliti bilan imzolaydi.
    Revoke {
        #[arg(long)]
        root_key: PathBuf,
        /// Ro'yxat versiyasi — har safar oldingisidan katta bo'lishi shart.
        #[arg(long)]
        version: u64,
        /// Bekor qilinadigan barmoq izi (hex); bir necha marta.
        #[arg(long = "fp")]
        fps: Vec<String>,
        #[arg(long, default_value = "revocations.json")]
        out: PathBuf,
    },
    /// mTLS mijoz sertifikati barmoq izi (SHA-256, hex) — `[auth] revoked_client_certs` uchun.
    CertFingerprint {
        #[arg(long)]
        cert: PathBuf,
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
            tls_san,
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
                tls_names: tls_san,
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
            shutdown_signal().await?;
            tracing::info!(
                "to'xtatilmoqda: yangi ulanishlar qabul qilinmaydi, ochiq so'rovlar tugatiladi"
            );
            srv.shutdown();
            let _ = srv.handle.await;
            Ok(())
        }
        Cmd::Shield { config } => {
            let cfg = Config::load(&config).map_err(|e| e.to_string())?;
            let mut srv = mpay_server::shield_role::start(&cfg).await?;
            shutdown_signal().await?;
            tracing::info!("to'xtatilmoqda");
            srv.shutdown();
            let _ = (&mut srv.handle).await;
            Ok(())
        }
        Cmd::Bootstrap { config } => {
            let cfg = Config::load(&config).map_err(|e| e.to_string())?;
            let st = mpay_server::state::build(&cfg)
                .await
                .map_err(|e| e.to_string())?;
            println!(
                "tayyor: migratsiyalar va kalitlar (keystore = {}, PQ Link barmoq izi {})",
                st.keystore.backend_name(),
                hex::encode(st.pqlink.identity().fingerprint())
            );
            Ok(())
        }
        Cmd::AuditVerify { config } => {
            let cfg = Config::load(&config).map_err(|e| e.to_string())?;
            let st = mpay_server::state::build_offline(&cfg)
                .await
                .map_err(|e| e.to_string())?;
            let r = st.vault.verify_audit().await.map_err(|e| e.to_string())?;
            println!(
                "audit zanjiri to'g'ri: {} yozuv, bosh xesh {}",
                r.entries, r.head_hash
            );
            Ok(())
        }
        Cmd::Clearing {
            config,
            date,
            out_dir,
        } => {
            let cfg = Config::load(&config).map_err(|e| e.to_string())?;
            let st = mpay_server::state::build_offline(&cfg)
                .await
                .map_err(|e| e.to_string())?;
            let date = date.unwrap_or_else(|| mpay_server::clearing::yesterday(st.clock.now()));
            mpay_server::recon::business_day(&date)?;
            let r = mpay_server::clearing::run(&st, &date)
                .await
                .map_err(|e| e.to_string())?;
            if let Some(dir) = &out_dir {
                std::fs::create_dir_all(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
                let write = |name: String, body: &[u8]| {
                    let p = dir.join(name);
                    std::fs::write(&p, body).map_err(|e| format!("{}: {e}", p.display()))
                };
                if let Some((file, ack)) = mpay_server::clearing::files(st.vault.db(), &date)
                    .await
                    .map_err(|e| e.to_string())?
                {
                    write(format!("{}.clr", r.batch_id), file.as_bytes())?;
                    if let Some(ack) = ack {
                        write(format!("{}.ack", r.batch_id), ack.as_bytes())?;
                    }
                }
                write(
                    format!("{}-payouts.csv", r.batch_id),
                    mpay_server::clearing::payouts_csv(&r).as_bytes(),
                )?;
                write(
                    format!("{}-settlement.json", r.batch_id),
                    &serde_json::to_vec_pretty(&r).map_err(|e| e.to_string())?,
                )?;
            }
            println!(
                "Paket {} ({}): {} — {} yozuv, qabul {}, rad {}",
                r.batch_id,
                r.business_date,
                r.state,
                r.records,
                r.accepted.unwrap_or(0),
                r.rejected.unwrap_or(0)
            );
            for p in &r.positions {
                println!(
                    "  {:<8} {:<15} {} — {} ta, yalpi {}, komissiya {}, sof {}",
                    p.party,
                    p.party_id,
                    p.currency,
                    p.count,
                    p.gross_minor,
                    p.fee_minor,
                    p.net_minor
                );
            }
            for i in &r.rejected_items {
                println!(
                    "  RAD: #{} terminal {} STAN {} RRN {} {} {} — {:?} {:?}",
                    i.seq,
                    i.terminal_id,
                    i.stan,
                    i.rrn,
                    i.dpan_masked,
                    i.amount_minor,
                    i.code,
                    i.reason
                );
            }
            if r.rejected_items.is_empty() {
                Ok(())
            } else {
                Err(format!(
                    "emitent {} ta yozuvni rad etdi",
                    r.rejected_items.len()
                ))
            }
        }
        Cmd::Recon { config, date, out } => {
            let cfg = Config::load(&config).map_err(|e| e.to_string())?;
            let st = mpay_server::state::build_offline(&cfg)
                .await
                .map_err(|e| e.to_string())?;
            let (from, to) =
                mpay_server::recon::period(date.as_deref(), None, None, st.clock.now())?;
            let r = mpay_server::recon::run(&st, from, to)
                .await
                .map_err(|e| e.to_string())?;
            if let Some(out) = &out {
                std::fs::write(
                    out,
                    serde_json::to_vec_pretty(&r).map_err(|e| e.to_string())?,
                )
                .map_err(|e| format!("{}: {e}", out.display()))?;
            }
            println!(
                "Davr [{from}, {to}): acquirer {} yozuv, emitent {}, mos {}",
                r.acquirer_records, r.issuer_records, r.matched
            );
            for t in &r.approved {
                println!(
                    "  tasdiqlangan ({}): {} ta, {} (minor)",
                    t.currency, t.count, t.amount_minor
                );
            }
            for i in r.discrepancies.iter().chain(&r.notes) {
                println!(
                    "  {:?}: terminal {} STAN {} RRN {} {} acquirer {:?}/{:?} emitent {:?}/{:?} reversal {:?}",
                    i.kind,
                    i.terminal_id,
                    i.stan,
                    i.rrn,
                    i.dpan_masked.as_deref().unwrap_or("-"),
                    i.acquirer_code,
                    i.acquirer_amount_minor,
                    i.issuer_code,
                    i.issuer_amount_minor,
                    i.reversal
                );
            }
            if r.is_clean() {
                println!("Tafovut yo'q ({} izoh)", r.notes.len());
                Ok(())
            } else {
                Err(format!("{} ta tafovut", r.discrepancies.len()))
            }
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
        Cmd::IdentityNext { config, version } => {
            use mpay_crypto::keystore::{KeyKind, KeyLabel};
            if version < 2 {
                return Err("--version 2 yoki undan katta".into());
            }
            let cfg = Config::load(&config).map_err(|e| e.to_string())?;
            let ks = mpay_server::state::open_keystore(&cfg).map_err(|e| e.to_string())?;
            let label = format!("mpay.srv-ed25519.v{version}");
            let blob_name = format!("pqlink-mldsa65.v{version}.blob");
            let blob_path = cfg.base_dir.join(&blob_name);
            if blob_path.exists() {
                return Err(format!("{} allaqachon mavjud", blob_path.display()));
            }
            ks.ensure_key(&KeyLabel::new(label.as_str()), KeyKind::Ed25519)
                .map_err(|e| e.to_string())?;
            let blob =
                mpay_pqlink::MlDsaSeedBlob::generate(ks.as_ref(), &KeyLabel::new(KeyLabel::KEK))
                    .map_err(|e| e.to_string())?;
            std::fs::write(&blob_path, blob.to_bytes())
                .map_err(|e| format!("{}: {e}", blob_path.display()))?;
            let signer =
                mpay_pqlink::KeyStoreServerSigner::new(ks, KeyLabel::new(label.as_str()), blob)
                    .map_err(|e| e.to_string())?;
            let fp = hex::encode(mpay_pqlink::ServerSigner::identity(&signer).fingerprint());
            println!("Keyingi identifikator: fingerprint {fp}");
            println!(
                "1) mpay.toml ga qo'shing va qayta ishga tushiring (qurilmalar tasdiqni oladi):\n"
            );
            println!("[pqlink.next]\nmldsa_blob = \"{blob_name}\"\ned25519_label = \"{label}\"\n");
            println!("2) O'tish: [pqlink] mldsa_blob/ed25519_label ni shu qiymatlarga almashtiring, [pqlink.next] ni o'chiring.");
            Ok(())
        }
        Cmd::RootKeygen { out } => {
            if out.exists() {
                return Err(format!("{} allaqachon mavjud", out.display()));
            }
            let root = mpay_pqlink::revocation::RootKey::generate().map_err(|e| e.to_string())?;
            let (e, m) = root.seeds();
            let json = zeroize::Zeroizing::new(
                serde_json::json!({
                    "format": "mpay-root-key/1",
                    "ed25519_seed": hex::encode(&e[..]),
                    "mldsa65_seed": hex::encode(&m[..]),
                })
                .to_string(),
            );
            std::fs::write(&out, json.as_bytes()).map_err(|e| format!("{}: {e}", out.display()))?;
            let fp = hex::encode(root.identity().map_err(|e| e.to_string())?.fingerprint());
            println!(
                "Ildiz kaliti: {} (MAXFIY — oflayn saqlang, serverga qo'ymang)",
                out.display()
            );
            println!("root_fingerprint: {fp}");
            Ok(())
        }
        Cmd::Revoke {
            root_key,
            version,
            fps,
            out,
        } => {
            let raw = zeroize::Zeroizing::new(
                std::fs::read_to_string(&root_key)
                    .map_err(|e| format!("{}: {e}", root_key.display()))?,
            );
            let j: serde_json::Value = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
            let seed = |k: &str| -> Result<zeroize::Zeroizing<[u8; 32]>, String> {
                let mut b = zeroize::Zeroizing::new([0u8; 32]);
                hex::decode_to_slice(j[k].as_str().unwrap_or_default(), &mut b[..])
                    .map_err(|_| format!("{k}: 64 hex"))?;
                Ok(b)
            };
            let root = mpay_pqlink::revocation::RootKey::from_seeds(
                &*seed("ed25519_seed")?,
                &*seed("mldsa65_seed")?,
            );
            let list = fps
                .iter()
                .map(|f| {
                    let mut b = [0u8; 32];
                    hex::decode_to_slice(f, &mut b)
                        .map(|()| b)
                        .map_err(|_| format!("--fp 64 hex: {f}"))
                })
                .collect::<Result<Vec<_>, _>>()?;
            let signed = root
                .sign_revocations(version, &list)
                .map_err(|e| e.to_string())?;
            let dto = mpay_server::revocations::to_dto(&signed);
            std::fs::write(
                &out,
                serde_json::to_vec_pretty(&dto).map_err(|e| e.to_string())?,
            )
            .map_err(|e| format!("{}: {e}", out.display()))?;
            println!(
                "Imzolandi: {} (versiya {}, {} ta). Serverda: [pqlink] revocations = \"{}\"",
                out.display(),
                signed.version,
                signed.revoked.len(),
                out.file_name()
                    .map(|f| f.to_string_lossy())
                    .unwrap_or_default()
            );
            Ok(())
        }
        Cmd::CertFingerprint { cert } => {
            println!("{}", mpay_server::auth::cert_fingerprint_pem(&cert)?);
            Ok(())
        }
        Cmd::Identity { config } => {
            let cfg = Config::load(&config).map_err(|e| e.to_string())?;
            let st = mpay_server::state::build_offline(&cfg)
                .await
                .map_err(|e| e.to_string())?;
            let id = st.pqlink.identity();
            println!("fingerprint: {}", hex::encode(id.fingerprint()));
            println!("ed25519:     {}", hex::encode(id.ed25519));
            // Hamyon build'i uchun TLS pini (`-Pmpay.tlsPin=`), TLS yoqilgan bo'lsa.
            if let Some(cert) = &cfg.http.tls_cert {
                use rustls::pki_types::pem::PemObject;
                use sha2::Digest;
                let der = rustls::pki_types::CertificateDer::from_pem_file(cfg.resolve(cert))
                    .map_err(|e| e.to_string())?;
                println!(
                    "tls_pin:     {}",
                    hex::encode(sha2::Sha256::digest(der.as_ref()))
                );
            }
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

/// Ctrl+C yoki (Unix) SIGTERM — `docker stop` SIGTERM yuboradi.
async fn shutdown_signal() -> Result<(), String> {
    #[cfg(unix)]
    {
        let mut term = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .map_err(|e| e.to_string())?;
        tokio::select! {
            r = tokio::signal::ctrl_c() => r.map_err(|e| e.to_string()),
            _ = term.recv() => Ok(()),
        }
    }
    #[cfg(not(unix))]
    {
        tokio::signal::ctrl_c().await.map_err(|e| e.to_string())
    }
}
