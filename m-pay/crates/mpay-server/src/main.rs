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
