//! `mpay-server init` — sandbox katalogini tayyorlaydi (`.mpay/`, git'ga tushmaydi):
//! dev-urug', ML-DSA-65 blob, sandbox attestatsiya CA, ixtiyoriy TLS sertifikati, API kalitlari
//! va `mpay.toml`. **Faqat sandbox.** Production'da kalitlar HSM'da, konfiguratsiya qo'lda.

use std::net::SocketAddr;
use std::path::{Path, PathBuf};

use base64::Engine;
use mpay_crypto::keystore::{ensure_standard_keys, KeyLabel, MemoryKeyStore};
use mpay_crypto::rng;
use mpay_pqlink::sandbox::SandboxAttestationCa;
use mpay_pqlink::MlDsaSeedBlob;
use zeroize::Zeroizing;

use crate::auth::hash_key;

/// `init` parametrlari.
#[derive(Debug, Clone)]
pub struct InitOptions {
    pub dir: PathBuf,
    pub listen: SocketAddr,
    pub tls: bool,
    pub force: bool,
}

/// `init` natijasi (kalitlar faqat bir marta ko'rsatiladi va `dev-credentials.env` ga yoziladi).
pub struct InitOutput {
    pub config_path: PathBuf,
    pub operator_key: Zeroizing<String>,
    pub terminal_key: Zeroizing<String>,
    pub server_fingerprint: String,
}

impl std::fmt::Debug for InitOutput {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("InitOutput")
            .field("config_path", &self.config_path)
            .finish_non_exhaustive()
    }
}

pub const CONFIG_FILE: &str = "mpay.toml";
pub const SEED_FILE: &str = "dev-master-seed.hex";
pub const MLDSA_FILE: &str = "pqlink-mldsa65.blob";
pub const CA_CERT_FILE: &str = "sandbox-attestation-root.der";
pub const CA_KEY_FILE: &str = "sandbox-attestation-ca.key.pem";
pub const TLS_CERT_FILE: &str = "tls-cert.pem";
pub const TLS_KEY_FILE: &str = "tls-key.pem";
pub const CREDENTIALS_FILE: &str = "dev-credentials.env";

fn write(dir: &Path, name: &str, data: &[u8]) -> Result<(), String> {
    let p = dir.join(name);
    std::fs::write(&p, data).map_err(|e| format!("{}: {e}", p.display()))
}

fn api_key() -> Result<Zeroizing<String>, String> {
    let raw = rng::secret_array::<32>().map_err(|e| e.to_string())?;
    Ok(Zeroizing::new(
        base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(&raw[..]),
    ))
}

/// Sandbox katalogini yaratadi.
pub fn run(opts: &InitOptions) -> Result<InitOutput, String> {
    let dir = &opts.dir;
    let cfg_path = dir.join(CONFIG_FILE);
    if cfg_path.exists() && !opts.force {
        return Err(format!(
            "{} allaqachon mavjud (--force bilan qayta yarating)",
            cfg_path.display()
        ));
    }
    std::fs::create_dir_all(dir).map_err(|e| format!("{}: {e}", dir.display()))?;

    let seed = rng::secret_array::<32>().map_err(|e| e.to_string())?;
    write(
        dir,
        SEED_FILE,
        Zeroizing::new(hex::encode(&seed[..])).as_bytes(),
    )?;
    let ks = MemoryKeyStore::from_seed(*seed);
    ensure_standard_keys(&ks).map_err(|e| e.to_string())?;
    let blob =
        MlDsaSeedBlob::generate(&ks, &KeyLabel::new(KeyLabel::KEK)).map_err(|e| e.to_string())?;
    write(dir, MLDSA_FILE, &blob.to_bytes())?;
    let signer = mpay_pqlink::KeyStoreServerSigner::new(
        std::sync::Arc::new(ks),
        KeyLabel::new(KeyLabel::SERVER_ED25519),
        blob,
    )
    .map_err(|e| e.to_string())?;
    let fp = hex::encode(mpay_pqlink::ServerSigner::identity(&signer).fingerprint());

    let ca = SandboxAttestationCa::generate().map_err(|e| e.to_string())?;
    write(dir, CA_CERT_FILE, ca.root_der())?;
    write(dir, CA_KEY_FILE, ca.key_pem().as_bytes())?;

    let (tls_cert, tls_key) = if opts.tls {
        let key = rcgen::KeyPair::generate().map_err(|e| e.to_string())?;
        let params = rcgen::CertificateParams::new(vec![
            "localhost".to_owned(),
            opts.listen.ip().to_string(),
        ])
        .map_err(|e| e.to_string())?;
        let cert = params.self_signed(&key).map_err(|e| e.to_string())?;
        write(dir, TLS_CERT_FILE, cert.pem().as_bytes())?;
        write(
            dir,
            TLS_KEY_FILE,
            Zeroizing::new(key.serialize_pem()).as_bytes(),
        )?;
        (
            format!("tls_cert = \"{TLS_CERT_FILE}\"\n"),
            format!("tls_key = \"{TLS_KEY_FILE}\"\n"),
        )
    } else {
        (String::new(), String::new())
    };

    let op = api_key()?;
    let term = api_key()?;
    let creds = Zeroizing::new(format!(
        "# M-Pay sandbox API kalitlari — FAQAT SANDBOX, git'ga tushmaydi.\nMPAY_OPERATOR_KEY={}\nMPAY_TERMINAL_KEY={}\n",
        op.as_str(),
        term.as_str()
    ));
    write(dir, CREDENTIALS_FILE, creds.as_bytes())?;

    let config = format!(
        r#"# M-Pay Pay Sandbox konfiguratsiyasi (`mpay-server init` yaratdi).
# Nisbiy yo'llar shu fayl joylashgan papkaga nisbatan.
sandbox = true

[http]
listen = "{listen}"
{tls_cert}{tls_key}
[database]
path = "mpay.db"

[keystore]
backend = "memory"
seed_file = "{SEED_FILE}"

[pqlink]
mldsa_blob = "{MLDSA_FILE}"
attestation_roots = ["{CA_CERT_FILE}"]
min_security_level = "STRONG_BOX"
session_ttl_secs = 900

[vault]
token_bin = "990077"
token_validity_months = 36
max_tokens_per_device = 10
otp_ttl_secs = 300
otp_max_attempts = 3

[vault.luk]
max_uses = 10
ttl_secs = 86400
batch_size = 5

[shield_stub]
review_amount_minor = 5000000000

[sandbox_api]
expose_otp = true

[[auth.keys]]
id = "operator-1"
role = "operator"
sha256 = "{op_hash}"

[[auth.keys]]
id = "terminal-1"
role = "terminal"
sha256 = "{term_hash}"
"#,
        listen = opts.listen,
        op_hash = hash_key(&op),
        term_hash = hash_key(&term),
    );
    write(dir, CONFIG_FILE, config.as_bytes())?;
    Ok(InitOutput {
        config_path: cfg_path,
        operator_key: op,
        terminal_key: term,
        server_fingerprint: fp,
    })
}
