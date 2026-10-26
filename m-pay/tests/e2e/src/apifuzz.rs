//! HTTP API fuzz harness (3-faza tayyorgarligi): `mpay-server` router'i jarayon ichida, tarmoqsiz.
//!
//! Bitta kirish (baytlar) → bitta HTTP so'rov:
//! * **ochiq rejim** — ixtiyoriy marshrut, metod, API kaliti (yo'q / operator / terminal / soxta),
//!   `Content-Type` va tana (handshake, operator va terminal endpointlari, muhrlanmagan yozuvlar);
//! * **muhrlangan rejim** — ixtiyoriy tana **haqiqiy PQ Link sessiyasi** bilan muhrlanadi va qurilma
//!   endpointiga yuboriladi: JSON tahlili va handler mantig'i (provisioning, OTP, LUK, rekey, sandbox)
//!   kriptografiya to'sig'idan o'tib sinanadi.
//!
//! Invariantlar (buzilsa — panic, fuzzer uni topadi):
//! * server panic qilmaydi va `500` qaytarmaydi (`502` faqat `/v1/authorizations` — emitent formati,
//!   `503` — ataylab: navbat/bog'liqlik);
//! * muhrlanmagan xato javobi — `{"error": {"code", "message"}}`;
//! * muhrlangan javob ochiladi va `{"ok": …}` konverti bo'ladi.
//!
//! Foydalanuvchilar: `fuzz/fuzz_targets/http_api.rs` (libFuzzer) va `tests/api_robustness.rs` (proptest).

use std::net::SocketAddr;
use std::sync::{Arc, Mutex};

use axum::body::Body;
use axum::extract::ConnectInfo;
use axum::http::{header, Method, Request, StatusCode};
use axum::Router;
use mpay_common::ports::SecurityLevel;
use mpay_pqlink::sandbox::SandboxAttestationCa;
use mpay_pqlink::{ClientHandshake, ClientSession, ServerIdentity};
use mpay_server::config::{Config, ShieldEngine};
use mpay_server::init::{self, InitOptions};
use tower::ServiceExt;

const PQLINK_CT: &str = "application/x-mpay-pqlink";

/// Ochiq rejim marshrutlari (`{id}` — tanlangan identifikator bilan almashtiriladi).
const PLAIN: &[(&str, &str)] = &[
    ("GET", "/healthz"),
    ("GET", "/v1/pqlink/identity"),
    ("POST", "/v1/pqlink/enroll"),
    ("GET", "/v1/pqlink/revocations"),
    ("POST", "/v1/pqlink/hello"),
    ("POST", "/v1/pqlink/finish"),
    ("POST", "/v1/tokens"),
    ("GET", "/v1/tokens/{id}"),
    ("DELETE", "/v1/tokens/{id}"),
    ("POST", "/v1/tokens/{id}/suspend"),
    ("POST", "/v1/tokens/{id}/resume"),
    ("POST", "/v1/tokens/{id}/luks"),
    ("GET", "/v1/audit/verify"),
    ("GET", "/v1/sandbox/otp/{id}"),
    ("GET", "/v1/sandbox/accounts"),
    ("POST", "/v1/sandbox/integrity-token"),
    ("POST", "/v1/authorizations"),
    ("GET", "/v1/terminal/ping"),
    ("PUT", "/v1/tokens"),
    ("GET", "/{id}"),
];

/// Muhrlangan rejim marshrutlari.
const SEALED: &[&str] = &[
    "/v1/tokens",
    "/v1/tokens/{id}/idv/verify",
    "/v1/tokens/{id}/idv/resend",
    "/v1/tokens/{id}/luks",
    "/v1/devices/rekey",
    "/v1/sandbox/integrity-token/device",
];

/// Jarayon ichidagi server va bitta qurilma sessiyasi.
pub struct ApiHarness {
    rt: tokio::runtime::Runtime,
    app: Router,
    identity: ServerIdentity,
    ca: SandboxAttestationCa,
    operator_key: String,
    terminal_key: String,
    token_id: String,
    session: Mutex<Option<ClientSession>>,
    _dir: tempfile::TempDir,
}

impl std::fmt::Debug for ApiHarness {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("ApiHarness")
    }
}

/// Bitta kirish natijasi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Outcome {
    /// Kirish juda qisqa.
    Skipped,
    /// Muhrlanmagan javob (HTTP status).
    Plain(u16),
    /// Muhrlangan konvert: bo'sh — `ok`, aks holda xato kodi.
    Sealed(String),
}

#[derive(Debug)]
struct Resp {
    status: StatusCode,
    content_type: String,
    body: Vec<u8>,
}

impl ApiHarness {
    /// Sandbox (`init`), chegaralar o'chiq, Shield stub; bitta ACTIVE token (identifikatorlar uchun).
    pub fn new() -> Self {
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("tokio");
        let dir = tempfile::tempdir().expect("tempdir");
        let out = init::run(&InitOptions {
            dir: dir.path().to_path_buf(),
            listen: "127.0.0.1:0".parse().expect("addr"),
            tls: false,
            force: false,
            keystore: mpay_server::config::KeyStoreBackend::Memory,
            tls_names: Vec::new(),
        })
        .expect("init");
        let mut cfg = Config::load(&out.config_path).expect("config");
        cfg.rate_limit.enabled = false;
        cfg.shield.engine = ShieldEngine::Stub;
        cfg.integrity.required = false;
        cfg.database.synchronous = mpay_db::Durability::Normal;
        let state = rt.block_on(mpay_server::state::build(&cfg)).expect("state");
        let identity = state.pqlink.identity().clone();
        let app = mpay_server::routes::router(Arc::new(state));
        let ca = SandboxAttestationCa::from_parts(
            &std::fs::read_to_string(dir.path().join(init::CA_KEY_FILE)).expect("ca key"),
            std::fs::read(dir.path().join(init::CA_CERT_FILE)).expect("ca"),
        )
        .expect("ca");
        let mut h = Self {
            rt,
            app,
            identity,
            ca,
            operator_key: out.operator_key.to_string(),
            terminal_key: out.terminal_key.to_string(),
            token_id: String::new(),
            session: Mutex::new(None),
            _dir: dir,
        };
        // Identifikatorli marshrutlar uchun haqiqiy token (GREEN test kartasi).
        let pan = crate::test_fpan(10, 9001);
        let r = h.sealed_call(
            "/v1/tokens",
            serde_json::json!({ "pan": pan, "expiry": "3112" })
                .to_string()
                .as_bytes(),
        );
        let v: serde_json::Value = serde_json::from_slice(&r.expect("provisioning")).expect("json");
        h.token_id = v["data"]["token_id"].as_str().expect("token_id").to_owned();
        h
    }

    fn send(&self, req: Request<Body>) -> Resp {
        self.rt.block_on(async {
            let mut req = req;
            req.extensions_mut()
                .insert(ConnectInfo(SocketAddr::from(([203, 0, 113, 7], 40_000))));
            req.extensions_mut()
                .insert(mpay_server::auth::PeerCert(None));
            let r = self.app.clone().oneshot(req).await.expect("infallible");
            let status = r.status();
            let content_type = r
                .headers()
                .get(header::CONTENT_TYPE)
                .and_then(|v| v.to_str().ok())
                .unwrap_or("")
                .to_owned();
            let body = axum::body::to_bytes(r.into_body(), 4 * 1024 * 1024)
                .await
                .expect("tana")
                .to_vec();
            Resp {
                status,
                content_type,
                body,
            }
        })
    }

    fn plain(
        &self,
        method: &str,
        path: &str,
        bearer: Option<&str>,
        ct: Option<&str>,
        body: Vec<u8>,
    ) -> Resp {
        let mut b = Request::builder()
            .method(Method::from_bytes(method.as_bytes()).expect("metod"))
            .uri(path);
        if let Some(k) = bearer {
            b = b.header(header::AUTHORIZATION, format!("Bearer {k}"));
        }
        if let Some(c) = ct {
            b = b.header(header::CONTENT_TYPE, c);
        }
        self.send(b.body(Body::from(body)).expect("so'rov"))
    }

    /// Yangi qurilma va PQ Link sessiyasi (ro'yxatdan o'tish nonce'i bilan).
    fn connect(&self) -> Option<ClientSession> {
        let r = self.plain(
            "POST",
            "/v1/pqlink/enroll",
            None,
            Some("application/json"),
            b"{}".to_vec(),
        );
        let v: serde_json::Value = serde_json::from_slice(&r.body).ok()?;
        let nonce = hex::decode(v["nonce"].as_str()?).ok()?;
        let device = self
            .ca
            .issue_device(SecurityLevel::StrongBox, &nonce)
            .ok()?;
        let (hs, ch) = ClientHandshake::start(self.identity.clone()).ok()?;
        let sh = self.plain("POST", "/v1/pqlink/hello", None, Some(PQLINK_CT), ch);
        let (pending, cf) = hs.on_server_hello(&sh.body, &device).ok()?;
        let sa = self.plain("POST", "/v1/pqlink/finish", None, Some(PQLINK_CT), cf);
        pending.on_accept(&sa.body).ok()
    }

    /// Muhrlangan so'rov: ochilgan konvert (JSON baytlari) yoki muhrlanmagan xato.
    fn sealed_call(&self, path: &str, plaintext: &[u8]) -> Result<Vec<u8>, Resp> {
        let mut guard = self.session.lock().unwrap_or_else(|p| p.into_inner());
        if guard.is_none() {
            *guard = self.connect();
        }
        let s = guard.as_mut().expect("PQ Link sessiyasi o'rnatilmadi");
        let record = s.seal(plaintext).expect("seal");
        let r = self.plain("POST", path, None, Some(PQLINK_CT), record);
        if !r.content_type.starts_with(PQLINK_CT) {
            // Sessiya yaroqsiz (masalan rekey'dan keyin) — keyingi so'rovda qayta ulanadi.
            *guard = None;
            return Err(r);
        }
        let pt = s
            .open(&r.body)
            .unwrap_or_else(|e| panic!("muhrlangan javob ochilmadi: {e}"));
        Ok(pt.to_vec())
    }

    /// Bitta kirish → bitta so'rov va invariantlar. Natija — harness qamrovini tekshirish uchun.
    pub fn run(&self, data: &[u8]) -> Outcome {
        let [mode, route, auth, ct, idsel, rest @ ..] = data else {
            return Outcome::Skipped;
        };
        let id = match idsel % 4 {
            0 => self.token_id.clone(),
            1 => "tok_00000000000000000000000000000000".to_owned(),
            2 => "chl_00000000000000000000000000000000".to_owned(),
            // Kirishdan: URI'ga sig'adigan belgilar.
            _ => rest
                .iter()
                .take(48)
                .map(|b| char::from(b'a' + b % 26))
                .collect(),
        };
        if mode % 2 == 0 {
            let (method, path) = PLAIN[usize::from(*route) % PLAIN.len()];
            let path = path.replace("{id}", &id);
            let bearer = match auth % 4 {
                0 => None,
                1 => Some(self.operator_key.as_str()),
                2 => Some(self.terminal_key.as_str()),
                _ => Some("mpay_garbage_key_0000"),
            };
            let ctype = match ct % 4 {
                0 => None,
                1 => Some("application/json"),
                2 => Some(PQLINK_CT),
                _ => Some("text/plain"),
            };
            let r = self.plain(method, &path, bearer, ctype, rest.to_vec());
            self.check_plain(method, &path, &r);
            Outcome::Plain(r.status.as_u16())
        } else {
            let path = SEALED[usize::from(*route) % SEALED.len()].replace("{id}", &id);
            match self.sealed_call(&path, rest) {
                Ok(pt) => {
                    let v: serde_json::Value = serde_json::from_slice(&pt)
                        .unwrap_or_else(|_| panic!("{path}: muhrlangan javob JSON emas"));
                    assert!(v["ok"].is_boolean(), "{path}: konvert yo'q: {v}");
                    let mut code = String::new();
                    if v["ok"] == false {
                        code = v["error"]["code"].as_str().unwrap_or("").to_owned();
                        let code = code.as_str();
                        assert!(!code.is_empty(), "{path}: xato kodi yo'q: {v}");
                        assert!(
                            !matches!(
                                code,
                                "INTERNAL" | "DB_ERROR" | "CRYPTO_ERROR" | "PQLINK_INTERNAL"
                            ),
                            "{path}: ichki xato {code}: {v}"
                        );
                    }
                    Outcome::Sealed(code)
                }
                Err(r) => {
                    self.check_plain("POST", &path, &r);
                    Outcome::Plain(r.status.as_u16())
                }
            }
        }
    }

    fn check_plain(&self, method: &str, path: &str, r: &Resp) {
        let s = r.status.as_u16();
        let allowed_5xx = matches!(s, 503) || (s == 502 && path == "/v1/authorizations");
        assert!(
            s < 500 || allowed_5xx,
            "{method} {path}: HTTP {s}: {}",
            String::from_utf8_lossy(&r.body)
        );
        if !r.status.is_success() && r.content_type.starts_with("application/json") {
            let v: serde_json::Value = serde_json::from_slice(&r.body)
                .unwrap_or_else(|_| panic!("{method} {path}: xato tanasi JSON emas"));
            assert!(
                v["error"]["code"].is_string(),
                "{method} {path}: xato shartnomasi buzilgan: {v}"
            );
        }
    }
}

impl Default for ApiHarness {
    fn default() -> Self {
        Self::new()
    }
}
