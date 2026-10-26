//! E2E test yordamchilari: vaqtinchalik sandbox (`mpay-server init`), serverni jarayon ichida
//! haqiqiy TCP portda ishga tushirish, soft-wallet va log ushlagichi.
#![forbid(unsafe_code)]
#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::io::Write;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::{Arc, Mutex, OnceLock};

use mpay_common::api::{AuthorizationRequest, AuthorizationResponse, ProvisionResponse};
use mpay_common::ports::SecurityLevel;
use mpay_pqlink::sandbox::{SandboxAttestationCa, SoftDeviceKey};
use mpay_pqlink::ServerIdentity;
use mpay_server::config::Config;
use mpay_server::init::{self, InitOptions};
use mpay_server::RunningServer;
use mpay_terminal_sim::apdu::Loopback;
use mpay_terminal_sim::card::{CardPolicy, CardProfile, SoftCard};
use mpay_terminal_sim::http::ServerClient;
use mpay_terminal_sim::terminal::{self, TapResult, TerminalError, TxnParams};
use mpay_terminal_sim::wallet::SoftWallet;
use mpay_terminal_sim::WalletError;

/// Barcha testlar loglarini yig'uvchi bufer (jarayon bo'yicha bitta global subscriber).
#[derive(Clone, Default)]
pub struct LogCapture(Arc<Mutex<Vec<u8>>>);

impl LogCapture {
    pub fn text(&self) -> String {
        String::from_utf8_lossy(&self.0.lock().unwrap()).into_owned()
    }
}

impl Write for LogCapture {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        self.0.lock().unwrap().extend_from_slice(buf);
        Ok(buf.len())
    }
    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}

/// Global log ushlagichi (debug darajasida — eng ko'p ma'lumot logga tushadigan holat).
pub fn logs() -> LogCapture {
    static CAP: OnceLock<LogCapture> = OnceLock::new();
    CAP.get_or_init(|| {
        let cap = LogCapture::default();
        let w = cap.clone();
        let _ = tracing_subscriber::fmt()
            .with_env_filter("debug,hyper=info,reqwest=info,sqlx=info,h2=info,rustls=info")
            .with_writer(move || w.clone())
            .with_ansi(false)
            .try_init();
        cap
    })
    .clone()
}

/// Ishga tushgan sandbox.
pub struct Sandbox {
    pub dir: tempfile::TempDir,
    pub cfg: Config,
    pub server: RunningServer,
    pub operator_key: String,
    pub terminal_key: String,
    pub fingerprint: String,
    pub ca: SandboxAttestationCa,
    /// TLS (+ mTLS) bilan ishga tushirilgan.
    pub tls: bool,
}

impl Sandbox {
    /// `init` + `start` (port 0).
    pub async fn start() -> Self {
        Self::start_with(|_| {}).await
    }

    /// Konfiguratsiyani o'zgartirib ishga tushiradi.
    pub async fn start_with(tweak: impl FnOnce(&mut Config)) -> Self {
        Self::start_backend(mpay_server::config::KeyStoreBackend::Memory, tweak).await
    }

    /// Berilgan KeyStore backend'i bilan.
    pub async fn start_backend(
        keystore: mpay_server::config::KeyStoreBackend,
        tweak: impl FnOnce(&mut Config),
    ) -> Self {
        Self::start_full(keystore, false, tweak).await
    }

    /// TLS va mTLS bilan (`init --tls`: mijoz CA'si, `operator-1`/`terminal-1` sertifikatlari,
    /// `require_mtls = true`).
    pub async fn start_tls(tweak: impl FnOnce(&mut Config)) -> Self {
        Self::start_full(mpay_server::config::KeyStoreBackend::Memory, true, tweak).await
    }

    async fn start_full(
        keystore: mpay_server::config::KeyStoreBackend,
        tls: bool,
        tweak: impl FnOnce(&mut Config),
    ) -> Self {
        let _ = logs();
        let dir = tempfile::tempdir().unwrap();
        let out = init::run(&InitOptions {
            dir: dir.path().to_path_buf(),
            listen: "127.0.0.1:0".parse().unwrap(),
            tls,
            force: false,
            keystore,
            tls_names: Vec::new(),
        })
        .unwrap();
        let mut cfg = Config::load(&out.config_path).unwrap();
        // M3/M4 testlari deterministik stub'ga tayanadi; M5 testlari `engine` ni o'zi yoqadi.
        cfg.shield.engine = mpay_server::config::ShieldEngine::Stub;
        // P2.6: `init` yaxlitlik tokenini majburiy qiladi; eski testlar qo'lda yaratgan hamyonlar
        // tokensiz qolishi uchun standart — ixtiyoriy. `wallet()` baribir mock token yuboradi
        // (tekshiruv yo'li ishlaydi); `p2_integrity` majburiy rejimni o'zi yoqadi.
        cfg.integrity.required = false;
        tweak(&mut cfg);
        // 2-faza P2.3: `MPAY_TEST_PG_URL` (PostgreSQL admin URL'i) bo'lsa — har sandbox o'z PG bazasida.
        if let Ok(admin) = std::env::var("MPAY_TEST_PG_URL") {
            cfg.database.url = Some(mpay_db::fresh_test_database(&admin).await.unwrap());
            cfg.database.path = None;
        }
        cfg.validate().unwrap();
        let server = mpay_server::start(&cfg).await.unwrap();
        let ca_key = std::fs::read_to_string(dir.path().join(init::CA_KEY_FILE)).unwrap();
        let ca_der = std::fs::read(dir.path().join(init::CA_CERT_FILE)).unwrap();
        let ca = SandboxAttestationCa::from_parts(&ca_key, ca_der).unwrap();
        Self {
            dir,
            cfg,
            server,
            operator_key: out.operator_key.to_string(),
            terminal_key: out.terminal_key.to_string(),
            fingerprint: out.server_fingerprint,
            ca,
            tls,
        }
    }

    pub fn addr(&self) -> SocketAddr {
        self.server.addr
    }

    pub fn base_url(&self) -> String {
        if self.tls {
            format!("https://localhost:{}", self.addr().port())
        } else {
            format!("http://{}", self.addr())
        }
    }

    pub fn client(&self) -> ServerClient {
        self.client_as(None)
    }

    /// `id` — mTLS sertifikati (`operator-1`, `terminal-1`); `None` — sertifikatsiz.
    pub fn client_as(&self, id: Option<&str>) -> ServerClient {
        if !self.tls {
            return ServerClient::new(&self.base_url(), None).unwrap();
        }
        let root = std::fs::read(self.dir.path().join(init::TLS_CERT_FILE)).unwrap();
        let ident = id.map(|id| {
            let (c, k) = init::client_cert_files(id);
            (
                std::fs::read(self.dir.path().join(c)).unwrap(),
                std::fs::read(self.dir.path().join(k)).unwrap(),
            )
        });
        ServerClient::with_identity(
            &self.base_url(),
            Some(&root),
            ident.as_ref().map(|(c, k)| (c.as_slice(), k.as_slice())),
        )
        .unwrap()
    }

    pub fn db_path(&self) -> PathBuf {
        self.dir.path().join("mpay.db")
    }

    /// Server identifikatorini oladi va `init` chiqargan barmoq izi bilan solishtiradi (pinlash).
    pub async fn pinned_identity(&self) -> ServerIdentity {
        let (id, fp) = self.client().identity().await.unwrap();
        assert_eq!(
            fp, self.fingerprint,
            "server identifikatori init natijasiga mos emas"
        );
        id
    }

    /// Ro'yxatdan o'tmagan qurilma (ixtiyoriy challenge) — rad etilish stsenariylari uchun.
    pub fn device(&self, level: SecurityLevel) -> SoftDeviceKey {
        self.ca.issue_device(level, b"e2e-unenrolled").unwrap()
    }

    /// Server nonce'i bilan yaratilgan qurilma (P1.7) — birinchi handshake'da ro'yxatga olinadi.
    pub async fn enrolled_device(&self, level: SecurityLevel) -> SoftDeviceKey {
        let nonce = self.client().enroll_nonce().await.unwrap();
        self.ca.issue_device(level, &nonce).unwrap()
    }

    /// Ulangan soft-wallet (StrongBox qurilma).
    pub async fn wallet(&self) -> SoftWallet {
        let mut w = SoftWallet::new(
            self.client(),
            self.pinned_identity().await,
            self.enrolled_device(SecurityLevel::StrongBox).await,
        );
        w.set_integrity(self.integrity_provider(mpay_integrity::mock::Preset::Strong));
        w.connect().await.unwrap();
        w
    }

    /// Sandbox mock yaxlitlik tokenlari manbai (`[integrity] mode = "mock"` bo'lsa).
    pub fn integrity_provider(
        &self,
        preset: mpay_integrity::mock::Preset,
    ) -> Option<mpay_terminal_sim::wallet::IntegrityProvider> {
        let issuer = std::sync::Arc::new(mpay_server::integrity::sandbox_issuer(&self.cfg).ok()??);
        Some(std::sync::Arc::new(move |hash: &str| {
            Some(issuer.issue(preset, hash, now_ms()))
        }))
    }

    /// DB fayllari (asosiy + WAL) baytlari.
    /// SQLite — fayl, WAL va SHM baytlari; PostgreSQL — barcha jadval qatorlarining matn ko'rinishi
    /// (`row::text`, BYTEA hex sifatida). Bo'sh bo'lmasligi tekshiriladi (aks holda "yo'q" tekshiruvlari
    /// jim o'tib ketardi).
    pub async fn db_bytes(&self) -> Vec<u8> {
        let pool = self.server.state.vault.pool();
        let raw = match self.server.state.vault.db().dialect() {
            mpay_db::Dialect::Sqlite => {
                let mut raw = std::fs::read(self.db_path()).unwrap_or_default();
                for ext in ["mpay.db-wal", "mpay.db-shm"] {
                    if let Ok(b) = std::fs::read(self.dir.path().join(ext)) {
                        raw.extend_from_slice(&b);
                    }
                }
                raw
            }
            mpay_db::Dialect::Postgres => {
                let tables: Vec<String> = sqlx::query_scalar(
                    "SELECT tablename::text FROM pg_tables WHERE schemaname = 'public'",
                )
                .fetch_all(pool)
                .await
                .unwrap();
                let mut raw = Vec::new();
                for t in tables {
                    let rows: Vec<String> = sqlx::query_scalar(sqlx::AssertSqlSafe(format!(
                        "SELECT x::text FROM {t} x"
                    )))
                    .fetch_all(pool)
                    .await
                    .unwrap();
                    for r in rows {
                        raw.extend_from_slice(r.as_bytes());
                    }
                }
                raw
            }
        };
        assert!(raw.len() > 1024, "DB tarkibi o'qilmadi");
        raw
    }
}

impl Sandbox {
    /// GREEN FPAN uchun token oladi va soft-kartani qaytaradi.
    pub async fn provision_card(
        &self,
        w: &mut SoftWallet,
        fpan: &str,
        policy: CardPolicy,
    ) -> SoftCard {
        match w.provision(fpan, "3112").await.unwrap() {
            ProvisionResponse::Active { profile, .. } => {
                SoftCard::new(CardProfile::from_dto(&profile).unwrap(), policy)
            }
            other => panic!("ACTIVE kutilgan: {other:?}"),
        }
    }

    /// Loopback tap.
    pub fn tap(card: &mut SoftCard, amount_minor: u64) -> Result<TapResult, TerminalError> {
        let mut lb = Loopback::new(card);
        terminal::tap(&mut lb, &TxnParams::purchase(amount_minor))
    }

    /// Terminal kaliti bilan `/v1/authorizations`.
    pub async fn authorize(
        &self,
        icc_hex: String,
        merchant: &str,
        stan: u32,
    ) -> Result<AuthorizationResponse, WalletError> {
        let req = AuthorizationRequest {
            terminal_id: "TERM0001".into(),
            merchant_id: merchant.into(),
            stan,
            icc_data: icc_hex,
        };
        self.client()
            .post_json("/v1/authorizations", Some(&self.terminal_key), &req)
            .await
    }

    /// Tap + avtorizatsiya.
    pub async fn pay(
        &self,
        card: &mut SoftCard,
        amount_minor: u64,
        merchant: &str,
        stan: u32,
    ) -> AuthorizationResponse {
        let tap = Self::tap(card, amount_minor).unwrap();
        self.authorize(tap.icc_hex(), merchant, stan).await.unwrap()
    }

    /// Sandbox hisob qoldig'i (maskalangan PAN'ning oxirgi 4 raqami bo'yicha).
    pub async fn balance(&self, fpan: &str) -> i64 {
        let accts: serde_json::Value = self
            .client()
            .get_json("/v1/sandbox/accounts", Some(&self.operator_key))
            .await
            .unwrap();
        accts
            .as_array()
            .unwrap()
            .iter()
            .find(|a| {
                a["pan_masked"].as_str().unwrap().ends_with(&fpan[12..])
                    && a["pan_masked"].as_str().unwrap().starts_with(&fpan[..6])
            })
            .map(|a| a["balance_minor"].as_i64().unwrap())
            .expect("hisob topilmadi")
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        self.server.shutdown();
    }
}

/// Stsenariy kodli test FPAN (`mpay_shield::stub` jadvaliga qarang).
pub fn test_fpan(scenario: u8, account: u32) -> String {
    let p = mpay_common::Pan::from_prefix(&format!("990012{scenario:02}{account:07}")).unwrap();
    p.expose_digits().to_owned()
}

/// `haystack` ichida `needle` bormi.
pub fn contains(haystack: &[u8], needle: &[u8]) -> bool {
    !needle.is_empty() && haystack.windows(needle.len()).any(|w| w == needle)
}

/// Joriy vaqt, millisekund (mock yaxlitlik tokenlari uchun).
pub fn now_ms() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}
