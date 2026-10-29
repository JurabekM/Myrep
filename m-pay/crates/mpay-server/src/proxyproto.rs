//! PROXY protocol v1 (2-faza P2.5): L4 (TCP) load balancer ortida mijozning haqiqiy manzili.
//!
//! nginx `stream` TLS'ni ochmasdan uzatadi — TLS va mTLS end-to-end qoladi (hamyon pini, terminal
//! sertifikati o'zgarmaydi), mijoz manzili esa ulanish boshidagi bitta qatorda keladi:
//! `PROXY TCP4 <manba> <manzil> <manba port> <port>\r\n`. Sarlavha **faqat** ishonchli proksidan
//! (`[http] trusted_proxies`) qabul qilinadi — aks holda mijoz o'z IP'sini soxtalashtirib, IP
//! chegarasini chetlab o'tardi.

use std::net::{IpAddr, SocketAddr};
use std::time::Duration;

use tokio::io::AsyncReadExt;
use tokio::net::TcpStream;

/// v1 sarlavhasining eng katta uzunligi (spetsifikatsiya: 107 bayt).
const MAX_V1: usize = 107;
/// Sarlavha shu vaqt ichida kelmasa ulanish yopiladi (sekin-loris).
const HEADER_TIMEOUT: Duration = Duration::from_secs(5);

/// Ulanish boshidan sarlavhani o'qiydi (bayt-bayt — keyingi TLS ma'lumoti iste'mol qilinmaydi).
/// `Some(addr)` — mijoz manzili; `None` — `PROXY UNKNOWN` (masalan proksi sog'liq tekshiruvi).
pub async fn read_v1(stream: &mut TcpStream) -> std::io::Result<Option<SocketAddr>> {
    let mut line = Vec::with_capacity(MAX_V1);
    let read = async {
        loop {
            let b = stream.read_u8().await?;
            line.push(b);
            if line.ends_with(b"\r\n") {
                return Ok::<(), std::io::Error>(());
            }
            if line.len() >= MAX_V1 {
                return Err(bad("PROXY sarlavhasi juda uzun"));
            }
        }
    };
    tokio::time::timeout(HEADER_TIMEOUT, read)
        .await
        .map_err(|_| bad("PROXY sarlavhasi kutish vaqti tugadi"))??;
    parse_v1(&line)
}

fn bad(m: &'static str) -> std::io::Error {
    std::io::Error::new(std::io::ErrorKind::InvalidData, m)
}

/// `PROXY …\r\n` qatorini tahlil qiladi.
pub fn parse_v1(line: &[u8]) -> std::io::Result<Option<SocketAddr>> {
    let s = std::str::from_utf8(line)
        .ok()
        .and_then(|s| s.strip_suffix("\r\n"))
        .ok_or_else(|| bad("PROXY sarlavhasi formati"))?;
    let mut it = s.split(' ');
    if it.next() != Some("PROXY") {
        return Err(bad("PROXY sarlavhasi kutilgan"));
    }
    match it.next() {
        Some("UNKNOWN") => Ok(None),
        Some(fam @ ("TCP4" | "TCP6")) => {
            let src: IpAddr = it
                .next()
                .and_then(|v| v.parse().ok())
                .ok_or_else(|| bad("PROXY manba manzili"))?;
            let _dst: IpAddr = it
                .next()
                .and_then(|v| v.parse().ok())
                .ok_or_else(|| bad("PROXY manzil"))?;
            let sport: u16 = it
                .next()
                .and_then(|v| v.parse().ok())
                .ok_or_else(|| bad("PROXY manba porti"))?;
            let _dport: u16 = it
                .next()
                .and_then(|v| v.parse().ok())
                .ok_or_else(|| bad("PROXY port"))?;
            if it.next().is_some() || (fam == "TCP4") != src.is_ipv4() {
                return Err(bad("PROXY sarlavhasi formati"));
            }
            Ok(Some(SocketAddr::new(src, sport)))
        }
        _ => Err(bad("PROXY oilasi noma'lum")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_v1() {
        assert_eq!(
            parse_v1(b"PROXY TCP4 203.0.113.7 10.0.0.2 51234 8443\r\n").unwrap(),
            Some("203.0.113.7:51234".parse().unwrap())
        );
        assert_eq!(
            parse_v1(b"PROXY TCP6 2001:db8::1 2001:db8::2 4000 443\r\n").unwrap(),
            Some("[2001:db8::1]:4000".parse().unwrap())
        );
        assert_eq!(parse_v1(b"PROXY UNKNOWN\r\n").unwrap(), None);
        for bad in [
            &b"PROXY TCP4 2001:db8::1 10.0.0.2 1 2\r\n"[..],
            b"PROXY TCP4 1.2.3.4 10.0.0.2 99999 2\r\n",
            b"PROXY TCP4 1.2.3.4 10.0.0.2 1 2 extra\r\n",
            b"GET / HTTP/1.1\r\n",
            b"PROXY TCP4 1.2.3.4 10.0.0.2 1 2",
        ] {
            assert!(parse_v1(bad).is_err(), "{bad:?}");
        }
    }

    #[tokio::test]
    async fn reads_header_and_leaves_payload() {
        use tokio::io::AsyncWriteExt;
        let l = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = l.local_addr().unwrap();
        let c = tokio::spawn(async move {
            let mut s = TcpStream::connect(addr).await.unwrap();
            s.write_all(b"PROXY TCP4 198.51.100.9 127.0.0.1 40000 443\r\n\x16\x03\x01")
                .await
                .unwrap();
        });
        let (mut s, _) = l.accept().await.unwrap();
        let a = read_v1(&mut s).await.unwrap();
        assert_eq!(a, Some("198.51.100.9:40000".parse().unwrap()));
        let mut rest = [0u8; 3];
        s.read_exact(&mut rest).await.unwrap();
        assert_eq!(rest, [0x16, 0x03, 0x01], "TLS baytlari tegilmagan");
        c.await.unwrap();
    }
}
