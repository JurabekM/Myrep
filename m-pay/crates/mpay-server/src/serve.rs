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
pub fn load_tls(cert: &Path, key: &Path) -> Result<Arc<rustls::ServerConfig>, String> {
    let certs = CertificateDer::pem_file_iter(cert)
        .map_err(|e| format!("{}: {e}", cert.display()))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| format!("{}: {e}", cert.display()))?;
    let key = PrivateKeyDer::from_pem_file(key).map_err(|e| format!("{}: {e}", key.display()))?;
    let provider = Arc::new(rustls::crypto::ring::default_provider());
    let mut cfg = rustls::ServerConfig::builder_with_provider(provider)
        .with_protocol_versions(&[&rustls::version::TLS13, &rustls::version::TLS12])
        .map_err(|e| e.to_string())?
        .with_no_client_auth()
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
        // Mijoz manzili — IP bo'yicha cheklash uchun (`ConnectInfo`, oddiy HTTP yo'li bilan bir xil).
        let svc = TowerToHyperService::new(tower::ServiceExt::map_request(
            app.clone(),
            move |mut r: axum::http::Request<hyper::body::Incoming>| {
                r.extensions_mut().insert(ConnectInfo(peer));
                r
            },
        ));
        tokio::spawn(async move {
            let tls = match acceptor.accept(tcp).await {
                Ok(s) => s,
                Err(e) => {
                    tracing::debug!(%peer, error = %e, "TLS handshake xatosi");
                    return;
                }
            };
            if let Err(e) = Builder::new(TokioExecutor::new())
                .serve_connection(TokioIo::new(tls), svc)
                .await
            {
                tracing::debug!(%peer, error = %e, "ulanish xatosi");
            }
        });
    }
}
