//! HTTP(S) server tsikli. TLS: rustls (ring provider), sertifikat va kalit PEM fayllaridan.

use std::future::Future;
use std::net::SocketAddr;
use std::path::Path;
use std::sync::Arc;
use std::time::Duration;

use axum::extract::ConnectInfo;
use axum::Router;
use hyper_util::rt::{TokioExecutor, TokioIo};
use hyper_util::server::conn::auto::Builder;
use hyper_util::service::TowerToHyperService;
use rustls::pki_types::pem::PemObject;
use rustls::pki_types::{CertificateDer, PrivateKeyDer};
use tokio::net::TcpListener;
use tokio_rustls::TlsAcceptor;

/// TLS server sozlamasini PEM fayllardan yuklaydi.
pub fn load_tls(
    cert: &Path,
    key: &Path,
    client_ca: Option<&Path>,
) -> Result<Arc<rustls::ServerConfig>, String> {
    let certs = CertificateDer::pem_file_iter(cert)
        .map_err(|e| format!("{}: {e}", cert.display()))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| format!("{}: {e}", cert.display()))?;
    let key = PrivateKeyDer::from_pem_file(key).map_err(|e| format!("{}: {e}", key.display()))?;
    let provider = Arc::new(rustls::crypto::ring::default_provider());
    let builder = rustls::ServerConfig::builder_with_provider(provider.clone())
        .with_protocol_versions(&[&rustls::version::TLS13, &rustls::version::TLS12])
        .map_err(|e| e.to_string())?;
    let builder = match client_ca {
        // Mijoz sertifikati ixtiyoriy: hamyonlar sertifikatsiz (PQ Link), operator/terminal —
        // `[auth] require_mtls` bo'lsa handler darajasida majburiy.
        Some(ca) => {
            let mut roots = rustls::RootCertStore::empty();
            for c in
                CertificateDer::pem_file_iter(ca).map_err(|e| format!("{}: {e}", ca.display()))?
            {
                roots
                    .add(c.map_err(|e| format!("{}: {e}", ca.display()))?)
                    .map_err(|e| format!("{}: {e}", ca.display()))?;
            }
            let verifier = rustls::server::WebPkiClientVerifier::builder_with_provider(
                Arc::new(roots),
                provider,
            )
            .allow_unauthenticated()
            .build()
            .map_err(|e| e.to_string())?;
            builder.with_client_cert_verifier(verifier)
        }
        None => builder.with_no_client_auth(),
    };
    let mut cfg = builder
        .with_single_cert(certs, key)
        .map_err(|e| e.to_string())?;
    cfg.alpn_protocols = vec![b"http/1.1".to_vec()];
    Ok(Arc::new(cfg))
}

/// Ulanish qabul qilish sozlamalari.
#[derive(Clone, Default)]
pub struct Accept {
    pub tls: Option<Arc<rustls::ServerConfig>>,
    /// Bekor qilingan mijoz sertifikatlari (SHA-256).
    pub revoked: Arc<std::collections::HashSet<[u8; 32]>>,
    /// PROXY protocol v1 (`[http] proxy_protocol`): shu tarmoqlardan kelgan ulanish sarlavha bilan
    /// boshlanishi shart, boshqalari to'g'ridan-to'g'ri (masalan ichki sog'liq tekshiruvi).
    pub proxy_from: Option<Arc<Vec<crate::clientip::Cidr>>>,
}

/// TLS handshake shu vaqtda tugamasa ulanish yopiladi (sekin mijoz ulanish slotini band qilmasin).
const TLS_HANDSHAKE_TIMEOUT: Duration = Duration::from_secs(10);
/// To'xtatishda ochiq so'rovlarni kutish (Docker `stop_grace_period` dan kichik).
const DRAIN_TIMEOUT: Duration = Duration::from_secs(8);

/// Serverni ishga tushiradi. `shutdown` tugaganda yangi ulanishlar qabul qilinmaydi, ochiq
/// ulanishlar joriy so'rovni tugatib yopiladi (graceful, [`DRAIN_TIMEOUT`] gacha) — load balancer
/// ortidagi instansiya to'xtatilganda so'rovlar uzilmaydi.
pub async fn serve(
    listener: TcpListener,
    app: Router,
    opts: Accept,
    shutdown: impl Future<Output = ()> + Send + 'static,
) -> std::io::Result<()> {
    if opts.tls.is_none() && opts.proxy_from.is_none() {
        return axum::serve(
            listener,
            app.into_make_service_with_connect_info::<SocketAddr>(),
        )
        .with_graceful_shutdown(shutdown)
        .await;
    }
    let acceptor = opts.tls.map(TlsAcceptor::from);
    let (stop_tx, stop_rx) = tokio::sync::watch::channel(false);
    let mut conns = tokio::task::JoinSet::new();
    tokio::pin!(shutdown);
    loop {
        let (mut tcp, mut peer) = tokio::select! {
            r = listener.accept() => match r {
                Ok(x) => x,
                // Masalan fayl deskriptorlari tugadi (EMFILE): server to'xtamaydi, biroz kutadi.
                Err(e) => {
                    tracing::warn!(error = %e, "ulanishni qabul qilib bo'lmadi");
                    tokio::time::sleep(Duration::from_millis(50)).await;
                    continue;
                }
            },
            () = &mut shutdown => break,
        };
        while conns.try_join_next().is_some() {}
        let acceptor = acceptor.clone();
        let revoked = opts.revoked.clone();
        let proxy_from = opts.proxy_from.clone();
        let stop = stop_rx.clone();
        // Mijoz manzili (IP chegarasi) va mTLS sertifikat CN'i so'rov kengaytmalariga qo'yiladi.
        let app = app.clone();
        conns.spawn(async move {
            if proxy_from.is_some_and(|n| n.iter().any(|c| c.contains(peer.ip()))) {
                match crate::proxyproto::read_v1(&mut tcp).await {
                    Ok(Some(client)) => peer = client,
                    // `UNKNOWN` — proksining o'z tekshiruvi: manzil proksiniki qoladi.
                    Ok(None) => {}
                    Err(e) => {
                        crate::metrics::proxy_rejected();
                        tracing::warn!(%peer, error = %e, "PROXY protocol sarlavhasi yaroqsiz");
                        return;
                    }
                }
            }
            let Some(acceptor) = acceptor else {
                serve_conn(TokioIo::new(tcp), app, peer, None, stop).await;
                return;
            };
            let tls = match tokio::time::timeout(TLS_HANDSHAKE_TIMEOUT, acceptor.accept(tcp)).await
            {
                Ok(Ok(s)) => s,
                Ok(Err(e)) => {
                    tracing::debug!(%peer, error = %e, "TLS handshake xatosi");
                    return;
                }
                Err(_) => {
                    tracing::debug!(%peer, "TLS handshake vaqti tugadi");
                    return;
                }
            };
            // Bekor qilingan sertifikat — mijoz sertifikatsiz hisoblanadi (operator/terminal: 403).
            let cn = tls
                .get_ref()
                .1
                .peer_certificates()
                .and_then(|c| c.first())
                .and_then(|c| {
                    let fp = crate::auth::cert_fingerprint(c.as_ref());
                    if revoked.contains(&fp) {
                        tracing::warn!(%peer, cert = %hex::encode(&fp[..8]), "mTLS: bekor qilingan sertifikat");
                        None
                    } else {
                        crate::auth::cert_cn(c.as_ref())
                    }
                });
            serve_conn(TokioIo::new(tls), app, peer, cn, stop).await;
        });
    }
    drop(listener);
    let _ = stop_tx.send(true);
    let open = conns.len();
    let drain = async { while conns.join_next().await.is_some() {} };
    if tokio::time::timeout(DRAIN_TIMEOUT, drain).await.is_err() {
        tracing::warn!(
            open,
            "to'xtatish: ochiq ulanishlar kutish vaqtida tugamadi — uziladi"
        );
        conns.abort_all();
    }
    Ok(())
}

async fn serve_conn<I>(
    io: TokioIo<I>,
    app: Router,
    peer: SocketAddr,
    cn: Option<String>,
    mut stop: tokio::sync::watch::Receiver<bool>,
) where
    I: tokio::io::AsyncRead + tokio::io::AsyncWrite + Unpin + Send + 'static,
{
    let svc = TowerToHyperService::new(tower::ServiceExt::map_request(
        app,
        move |mut r: axum::http::Request<hyper::body::Incoming>| {
            r.extensions_mut().insert(ConnectInfo(peer));
            r.extensions_mut().insert(crate::auth::PeerCert(cn.clone()));
            r
        },
    ));
    let builder = Builder::new(TokioExecutor::new());
    let conn = builder.serve_connection(io, svc);
    tokio::pin!(conn);
    let r = tokio::select! {
        r = conn.as_mut() => r,
        () = async { drop(stop.wait_for(|s| *s).await) } => {
            // Joriy so'rov tugaydi, keep-alive ulanish yopiladi.
            conn.as_mut().graceful_shutdown();
            conn.await
        }
    };
    if let Err(e) = r {
        tracing::debug!(%peer, error = %e, "ulanish xatosi");
    }
}
