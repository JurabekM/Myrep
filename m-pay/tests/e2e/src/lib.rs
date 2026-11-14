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
        let _ = logs();
        let dir = tempfile::tempdir().unwrap();
        let out = init::run(&InitOptions {
            dir: dir.path().to_path_buf(),
            listen: "127.0.0.1:0".parse().unwrap(),
            tls: false,
            force: false,
            keystore,
        })
        .unwrap();
        let mut cfg = Config::load(&out.config_path).unwrap();
        // M3/M4 testlari deterministik stub'ga tayanadi; M5 testlari `engine` ni o'zi yoqadi.
        cfg.shield.engine = mpay_server::config::ShieldEngine::Stub;
        tweak(&mut cfg);
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
        }
    }

    pub fn addr(&self) -> SocketAddr {
        self.server.addr
    }

    pub fn base_url(&self) -> String {
        format!("http://{}", self.addr())
    }

    pub fn client(&self) -> ServerClient {
        ServerClient::new(&self.base_url(), None).unwrap()
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

    pub fn device(&self, level: SecurityLevel) -> SoftDeviceKey {
        self.ca.issue_device(level, b"e2e-enroll").unwrap()
    }

    /// Ulangan soft-wallet (StrongBox qurilma).
    pub async fn wallet(&self) -> SoftWallet {
        let mut w = SoftWallet::new(
            self.client(),
            self.pinned_identity().await,
            self.device(SecurityLevel::StrongBox),
        );
        w.connect().await.unwrap();
        w
    }

    /// DB fayllari (asosiy + WAL) baytlari.
    pub fn db_bytes(&self) -> Vec<u8> {
        let mut raw = std::fs::read(self.db_path()).unwrap_or_default();
        for ext in ["mpay.db-wal", "mpay.db-shm"] {
            if let Ok(b) = std::fs::read(self.dir.path().join(ext)) {
                raw.extend_from_slice(&b);
            }
        }
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
