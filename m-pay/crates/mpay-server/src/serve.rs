//! HTTP(S) server tsikli. TLS: rustls (ring provider), sertifikat va kalit PEM fayllaridan.

use std::future::Future;
use std::net::SocketAddr;
use std::path::Path;
use std::sync::Arc;

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

/// Serverni ishga tushiradi; `shutdown` tugaganda yangi ulanishlar qabul qilinmaydi.
pub async fn serve(
    listener: TcpListener,
    app: Router,
    tls: Option<Arc<rustls::ServerConfig>>,
    revoked: Arc<std::collections::HashSet<[u8; 32]>>,
    shutdown: impl Future<Output = ()> + Send + 'static,
) -> std::io::Result<()> {
    let Some(tls) = tls else {
        return axum::serve(
            listener,
            app.into_make_service_with_connect_info::<SocketAddr>(),
        )
        .with_graceful_shutdown(shutdown)
        .await;
    };
    let acceptor = TlsAcceptor::from(tls);
    tokio::pin!(shutdown);
    loop {
        let (tcp, peer) = tokio::select! {
            r = listener.accept() => r?,
            () = &mut shutdown => return Ok(()),
        };
        let acceptor = acceptor.clone();
        let revoked = revoked.clone();
        // Mijoz manzili (IP chegarasi) va mTLS sertifikat CN'i so'rov kengaytmalariga qo'yiladi.
        let app = app.clone();
        tokio::spawn(async move {
            let tls = match acceptor.accept(tcp).await {
                Ok(s) => s,
                Err(e) => {
                    tracing::debug!(%peer, error = %e, "TLS handshake xatosi");
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
            let svc = TowerToHyperService::new(tower::ServiceExt::map_request(
                app,
                move |mut r: axum::http::Request<hyper::body::Incoming>| {
                    r.extensions_mut().insert(ConnectInfo(peer));
                    r.extensions_mut().insert(crate::auth::PeerCert(cn.clone()));
                    r
                },
            ));
            if let Err(e) = Builder::new(TokioExecutor::new())
                .serve_connection(TokioIo::new(tls), svc)
                .await
            {
                tracing::debug!(%peer, error = %e, "ulanish xatosi");
            }
        });
    }
}
