//! `mpay-server` — M-Pay monolit binari: barcha modullarni yig'adi va HTTP API'ni beradi.
//!
//! Kutubxona sifatida ham ochiq — e2e testlar serverni jarayon ichida, haqiqiy TCP portda
//! ishga tushiradi.
#![forbid(unsafe_code)]

pub mod acquirer;
pub mod auth;
pub mod clientip;
pub mod config;
pub mod dedup;
pub mod enroll;
pub mod error;
pub mod init;
pub mod otp;
pub mod ratelimit;
pub mod revocations;
pub mod routes;
pub mod serve;
pub mod sessions;
pub mod shield_client;
pub mod shield_role;
pub mod state;

use std::sync::Arc;

use tokio::net::TcpListener;

/// Crate versiyasi.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Ishga tushgan server (testlar va CLI uchun).
pub struct RunningServer {
    pub addr: std::net::SocketAddr,
    pub state: Arc<state::AppState>,
    shutdown: Option<tokio::sync::oneshot::Sender<()>>,
    pub handle: tokio::task::JoinHandle<std::io::Result<()>>,
}

impl std::fmt::Debug for RunningServer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("RunningServer")
            .field("addr", &self.addr)
            .finish_non_exhaustive()
    }
}

impl RunningServer {
    /// Yangi ulanishlarni to'xtatadi.
    pub fn shutdown(&mut self) {
        if let Some(tx) = self.shutdown.take() {
            let _ = tx.send(());
        }
    }
}

/// Konfiguratsiyadan serverni ishga tushiradi. `listen` porti 0 bo'lsa OS port tanlaydi.
pub async fn start(cfg: &config::Config) -> Result<RunningServer, String> {
    let state = Arc::new(state::build(cfg).await.map_err(|e| e.to_string())?);
    let tls = match (&cfg.http.tls_cert, &cfg.http.tls_key) {
        (Some(c), Some(k)) => Some(serve::load_tls(
            &cfg.resolve(c),
            &cfg.resolve(k),
            cfg.http
                .client_ca
                .as_ref()
                .map(|p| cfg.resolve(p))
                .as_deref(),
        )?),
        _ => {
            tracing::warn!("TLS o'chiq — oddiy HTTP (faqat sandbox)");
            None
        }
    };
    let listener = TcpListener::bind(cfg.http.listen)
        .await
        .map_err(|e| e.to_string())?;
    let addr = listener.local_addr().map_err(|e| e.to_string())?;
    let app = routes::router(state.clone());
    let (tx, rx) = tokio::sync::oneshot::channel::<()>();
    let revoked = Arc::new(
        cfg.auth
            .revoked_client_certs
            .iter()
            .filter_map(|h| {
                let mut b = [0u8; 32];
                hex::decode_to_slice(h, &mut b).ok().map(|()| b)
            })
            .collect::<std::collections::HashSet<_>>(),
    );
    let handle = tokio::spawn(serve::serve(listener, app, tls, revoked, async move {
        let _ = rx.await;
    }));
    tracing::info!(%addr, "mpay-server tinglayapti");
    Ok(RunningServer {
        addr,
        state,
        shutdown: Some(tx),
        handle,
    })
}
