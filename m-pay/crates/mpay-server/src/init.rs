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
use crate::config::KeyStoreBackend;

/// `init` parametrlari.
#[derive(Debug, Clone)]
pub struct InitOptions {
    pub dir: PathBuf,
    pub listen: SocketAddr,
    pub tls: bool,
    pub force: bool,
    /// `memory` (dev-urug') yoki `pkcs11` (`MPAY_PKCS11_*` muhit o'zgaruvchilari, `pkcs11` feature).
    pub keystore: KeyStoreBackend,
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
/// mTLS mijoz sertifikatlari CA'si (sandbox; production'da bankning PKI'si).
pub const CLIENT_CA_FILE: &str = "mtls-client-ca.pem";
/// Standart API kalitlari ID'lari — mTLS sertifikati CN'i shularga teng.
pub const OPERATOR_ID: &str = "operator-1";
pub const TERMINAL_ID: &str = "terminal-1";

/// Mijoz sertifikati fayllari: `<id>.crt.pem`, `<id>.key.pem`.
pub fn client_cert_files(id: &str) -> (String, String) {
    (format!("{id}.crt.pem"), format!("{id}.key.pem"))
}

/// mTLS: mijoz CA'si va operator/terminal sertifikatlari (CN = API kaliti ID, EKU clientAuth).
fn issue_client_certs(dir: &Path) -> Result<(), String> {
    use rcgen::{
        BasicConstraints, CertificateParams, DnType, ExtendedKeyUsagePurpose, IsCa, Issuer,
        KeyPair, KeyUsagePurpose,
    };
    let err = |e: rcgen::Error| e.to_string();
    let ca_key = KeyPair::generate().map_err(err)?;
    let mut ca = CertificateParams::new(Vec::<String>::new()).map_err(err)?;
    ca.distinguished_name
        .push(DnType::CommonName, "M-Pay Sandbox mTLS Client CA");
    ca.is_ca = IsCa::Ca(BasicConstraints::Constrained(0));
    ca.key_usages = vec![KeyUsagePurpose::KeyCertSign, KeyUsagePurpose::CrlSign];
    let ca_cert = ca.self_signed(&ca_key).map_err(err)?;
    write(dir, CLIENT_CA_FILE, ca_cert.pem().as_bytes())?;
    // CA kaliti saqlanmaydi: sandbox'da yangi mijoz kerak bo'lsa `init --force`.
    let issuer = Issuer::new(ca, ca_key);
    for id in [OPERATOR_ID, TERMINAL_ID] {
        let key = KeyPair::generate().map_err(err)?;
        let mut p = CertificateParams::new(Vec::<String>::new()).map_err(err)?;
        p.distinguished_name.push(DnType::CommonName, id);
        p.key_usages = vec![KeyUsagePurpose::DigitalSignature];
        p.extended_key_usages = vec![ExtendedKeyUsagePurpose::ClientAuth];
        let cert = p.signed_by(&key, &issuer).map_err(err)?;
        let (crt, k) = client_cert_files(id);
        write(dir, &crt, cert.pem().as_bytes())?;
        write(dir, &k, Zeroizing::new(key.serialize_pem()).as_bytes())?;
    }
    Ok(())
}

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

/// Namoyish uchun test hisoblar: `(stsenariy prefiksi, balans tiyinda, yorliq)`.
pub const DEMO_ACCOUNTS: &[(&str, i64, &str)] = &[
    ("990012100001001", 500_000_000, "GREEN, 5 000 000 UZS"),
    (
        "990012200002002",
        1_000_000,
        "GREEN, 10 000 UZS (51 namoyishi)",
    ),
    ("990012850003003", 200_000_000, "demo hisob (200 000 UZS)"),
    ("990012950004004", 100_000_000, "demo hisob (100 000 UZS)"),
    ("990013100005005", 100_000_000, "offline emitent (91)"),
];

fn demo_accounts() -> Result<String, String> {
    let mut out = String::new();
    for (prefix, balance, label) in DEMO_ACCOUNTS {
        let pan = mpay_common::Pan::from_prefix(prefix).map_err(|e| e.to_string())?;
        out.push_str(&format!(
            "\n[[issuer.accounts]]\npan = \"{}\"\nbalance_minor = {balance}\nlabel = \"{label}\"\n",
            pan.expose_digits()
        ));
    }
    Ok(out)
}

#[cfg(feature = "pkcs11")]
fn open_pkcs11() -> Result<std::sync::Arc<dyn mpay_crypto::KeyStore>, String> {
    use mpay_crypto::keystore::{Pkcs11Config, Pkcs11KeyStore};
    let c = Pkcs11Config::from_env().map_err(|e| e.to_string())?;
    Ok(std::sync::Arc::new(
        Pkcs11KeyStore::open(&c).map_err(|e| e.to_string())?,
    ))
}

#[cfg(not(feature = "pkcs11"))]
fn open_pkcs11() -> Result<std::sync::Arc<dyn mpay_crypto::KeyStore>, String> {
    Err("mpay-server `pkcs11` feature'siz yig'ilgan".into())
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

    let ks: std::sync::Arc<dyn mpay_crypto::KeyStore> = match opts.keystore {
        KeyStoreBackend::Memory => {
            let seed = rng::secret_array::<32>().map_err(|e| e.to_string())?;
            write(
                dir,
                SEED_FILE,
                Zeroizing::new(hex::encode(&seed[..])).as_bytes(),
            )?;
            std::sync::Arc::new(MemoryKeyStore::from_seed(*seed))
        }
        KeyStoreBackend::Pkcs11 => open_pkcs11()?,
    };
    ensure_standard_keys(ks.as_ref()).map_err(|e| e.to_string())?;
    // ML-DSA-65 urug'i shu KeyStore'ning KEK'i bilan o'raladi (HSM'da — HSM KEK).
    let blob = MlDsaSeedBlob::generate(ks.as_ref(), &KeyLabel::new(KeyLabel::KEK))
        .map_err(|e| e.to_string())?;
    write(dir, MLDSA_FILE, &blob.to_bytes())?;
    let signer =
        mpay_pqlink::KeyStoreServerSigner::new(ks, KeyLabel::new(KeyLabel::SERVER_ED25519), blob)
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
        issue_client_certs(dir)?;
        (
            format!("tls_cert = \"{TLS_CERT_FILE}\"\n"),
            format!("tls_key = \"{TLS_KEY_FILE}\"\nclient_ca = \"{CLIENT_CA_FILE}\"\n"),
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
# Teskari proksi ortida: ishonchli proksilar (CIDR) — mijoz IP'si X-Forwarded-For dan.
trusted_proxies = []
{tls_cert}{tls_key}
[database]
path = "mpay.db"

[keystore]
{keystore}

[pqlink]
mldsa_blob = "{MLDSA_FILE}"
attestation_roots = ["{CA_CERT_FILE}"]
min_security_level = "STRONG_BOX"
# Bootloader qulflangan va yuklash tekshirilgan (rootOfTrust) bo'lishi shart; emulyator sinovida false.
require_verified_boot = true
session_ttl_secs = 900
# Yangi qurilma attestatsiyasi server nonce'i bilan (POST /v1/pqlink/enroll); "off" — faqat sandbox/test.
enrollment = "required"
enrollment_nonce_ttl_secs = 300
# Davriy qayta attestatsiya: shuncha kundan keyin qurilma kalitni almashtiradi (0 — o'chiq).
reattest_after_days = 90

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

[shield]
# "engine" — qoidalar + graf/tezlik belgilari + ONNX ML; "stub" — deterministik test rejimi.
engine = "engine"

[shield_stub]
review_amount_minor = 5000000000

[sandbox_api]
expose_otp = true

# So'rovlar chegarasi (tahdid modeli D2). Oshganda 429 + Retry-After; handshake navbati to'la — 503.
# Mobil operatorlar CGNAT ortida ko'p foydalanuvchini bitta IP'ga yig'adi — IP chegarasi yumshoq,
# asosiy CPU himoyasi — bir vaqtdagi handshake'lar soni.
[rate_limit]
enabled = true
max_concurrent_handshakes = 0   # 0 — CPU soni × 2
ip_handshake_per_minute = 300   # /v1/pqlink/hello va /finish, IP bo'yicha
ip_handshake_burst = 60
api_key_per_second = 500        # operator/terminal kaliti bo'yicha
api_key_burst = 1000
device_per_minute = 60          # muhrlangan so'rovlar, qurilma bo'yicha
device_burst = 30

# Emitent emulyatori: test hisoblar (FPAN — fiktiv, docs/test-data.md).
[issuer]
offline_bins = ["990013"]
review_action = "approve"
{accounts}
[auth]
# TLS bilan: operator/terminal so'rovlari mTLS sertifikatini talab qiladi (CN = kalit id).
require_mtls = {require_mtls}

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
        require_mtls = opts.tls,
        op_hash = hash_key(&op),
        term_hash = hash_key(&term),
        accounts = demo_accounts()?,
        keystore = match opts.keystore {
            KeyStoreBackend::Memory => format!("backend = \"memory\"
seed_file = \"{SEED_FILE}\""),
            KeyStoreBackend::Pkcs11 => "# MPAY_PKCS11_LIB, MPAY_PKCS11_TOKEN_LABEL, MPAY_PKCS11_PIN muhit o'zgaruvchilaridan
backend = \"pkcs11\"".to_owned(),
        },
    );
    write(dir, CONFIG_FILE, config.as_bytes())?;
    Ok(InitOutput {
        config_path: cfg_path,
        operator_key: op,
        terminal_key: term,
        server_fingerprint: fp,
    })
}

/// Terminal paketi (JSON): server URL, server TLS sertifikati va uning SHA-256 pini, mTLS mijoz
/// sertifikati va kaliti, terminal API kaliti. **Sirlar bor** — faqat sandbox; terminal ilovasi
/// import qilgach kalitni Android Keystore'ga o'tkazadi va faylni o'chirish kerak.
pub fn terminal_bundle(
    dir: &Path,
    id: &str,
    server_url: &str,
) -> Result<Zeroizing<String>, String> {
    use rustls::pki_types::pem::PemObject;
    use sha2::{Digest, Sha256};
    let read = |name: &str| {
        let p = dir.join(name);
        std::fs::read_to_string(&p).map_err(|e| format!("{}: {e}", p.display()))
    };
    if !server_url.starts_with("https://") {
        return Err("terminal paketi faqat https:// manzil uchun (TLS + mTLS)".into());
    }
    let server_pem = read(TLS_CERT_FILE)?;
    let der = rustls::pki_types::CertificateDer::from_pem_slice(server_pem.as_bytes())
        .map_err(|e| format!("{TLS_CERT_FILE}: {e}"))?;
    let (crt, key) = client_cert_files(id);
    let client_pem = read(&crt)?;
    let client_key = Zeroizing::new(read(&key)?);
    let creds = Zeroizing::new(read(CREDENTIALS_FILE)?);
    let terminal_key = creds
        .lines()
        .find_map(|l| l.strip_prefix("MPAY_TERMINAL_KEY="))
        .map(|v| Zeroizing::new(v.trim().to_owned()))
        .ok_or("MPAY_TERMINAL_KEY topilmadi")?;
    let json = serde_json::json!({
        "format": "mpay-terminal-bundle/1",
        "server_url": server_url,
        "server_cert_pem": server_pem,
        "server_cert_sha256": hex::encode(Sha256::digest(der.as_ref())),
        "key_id": id,
        "client_cert_pem": client_pem,
        "client_key_pem": client_key.as_str(),
        "terminal_key": terminal_key.as_str(),
    });
    serde_json::to_string_pretty(&json)
        .map(Zeroizing::new)
        .map_err(|e| e.to_string())
}
