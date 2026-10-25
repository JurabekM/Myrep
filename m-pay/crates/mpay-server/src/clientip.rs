//! Mijozning haqiqiy IP manzili (IP chegaralari uchun): server ishonchli teskari proksi ortida
//! bo'lsa `X-Forwarded-For` dan olinadi, aks holda TCP manzili. Sarlavha faqat ulanish ishonchli
//! proksidan kelganda o'qiladi — aks holda mijoz uni soxtalashtirib chegarani chetlab o'tardi.

use std::fmt;
use std::net::IpAddr;
use std::str::FromStr;

use serde::{Deserialize, Deserializer, Serialize, Serializer};

/// IP tarmog'i (`10.0.0.0/8`, `fd00::/8`) yoki bitta manzil.
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct Cidr {
    net: IpAddr,
    prefix: u8,
}

impl fmt::Debug for Cidr {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}/{}", self.net, self.prefix)
    }
}

impl FromStr for Cidr {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let (ip, prefix) = match s.split_once('/') {
            Some((ip, p)) => (ip, Some(p)),
            None => (s, None),
        };
        let net: IpAddr = ip
            .trim()
            .parse()
            .map_err(|_| format!("noto'g'ri IP: {s}"))?;
        let max = if net.is_ipv4() { 32 } else { 128 };
        let prefix = match prefix {
            Some(p) => p
                .trim()
                .parse::<u8>()
                .ok()
                .filter(|p| *p <= max)
                .ok_or_else(|| format!("noto'g'ri prefiks: {s}"))?,
            None => max,
        };
        Ok(Self { net, prefix })
    }
}

impl Serialize for Cidr {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(&format!("{}/{}", self.net, self.prefix))
    }
}

impl<'de> Deserialize<'de> for Cidr {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        String::deserialize(d)?
            .parse()
            .map_err(serde::de::Error::custom)
    }
}

fn bits(ip: IpAddr) -> u128 {
    match ip {
        IpAddr::V4(v) => u128::from(u32::from(v)),
        IpAddr::V6(v) => u128::from(v),
    }
}

impl Cidr {
    pub fn contains(&self, ip: IpAddr) -> bool {
        // IPv4-mapped IPv6 (`::ffff:a.b.c.d`) — IPv4 sifatida.
        let ip = ip.to_canonical();
        if ip.is_ipv4() != self.net.is_ipv4() {
            return false;
        }
        let width = if ip.is_ipv4() { 32 } else { 128 };
        if self.prefix == 0 {
            return true;
        }
        let shift = width - u32::from(self.prefix);
        (bits(ip) >> shift) == (bits(self.net) >> shift)
    }
}

/// Mijoz IP'si. `peer` ishonchli proksi bo'lsa `X-Forwarded-For` o'ngdan chapga o'qiladi:
/// ishonchli proksilar o'tkazib yuboriladi, birinchi ishonchsiz manzil — mijoz. Yaroqsiz yozuvda
/// to'xtaladi va oxirgi ishonchli hop qaytariladi (soxta sarlavha chegarani chetlab o'tolmaydi).
pub fn client_ip(peer: IpAddr, xff: &[&str], trusted: &[Cidr]) -> IpAddr {
    let is_trusted = |ip: IpAddr| trusted.iter().any(|c| c.contains(ip));
    if !is_trusted(peer) {
        return peer;
    }
    let mut last = peer;
    for part in xff.iter().rev().flat_map(|h| h.rsplit(',')) {
        let Ok(ip) = part.trim().parse::<IpAddr>() else {
            return last;
        };
        if !is_trusted(ip) {
            return ip;
        }
        last = ip;
    }
    last
}

/// IP chegarasi kaliti: IPv4 — manzil, IPv6 — `/64` tarmoq. Bitta abonentga odatda butun `/64`
/// beriladi: manzil bo'yicha kalit bo'lsa, mijoz har so'rovni yangi manzildan yuborib (2^64 ta)
/// chegarani chetlab o'tardi.
pub fn rate_key(ip: IpAddr) -> String {
    match ip.to_canonical() {
        IpAddr::V4(v) => v.to_string(),
        IpAddr::V6(v) => {
            let s = v.segments();
            format!("{:x}:{:x}:{:x}:{:x}::/64", s[0], s[1], s[2], s[3])
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ip(s: &str) -> IpAddr {
        s.parse().unwrap()
    }

    #[test]
    fn cidr_parse_and_contains() {
        let c: Cidr = "10.0.0.0/8".parse().unwrap();
        assert!(c.contains(ip("10.1.2.3")));
        assert!(!c.contains(ip("11.0.0.1")));
        assert!(c.contains(ip("::ffff:10.9.9.9")), "IPv4-mapped");
        let one: Cidr = "127.0.0.1".parse().unwrap();
        assert!(one.contains(ip("127.0.0.1")) && !one.contains(ip("127.0.0.2")));
        let v6: Cidr = "fd00::/8".parse().unwrap();
        assert!(v6.contains(ip("fd12::1")) && !v6.contains(ip("fe80::1")));
        assert!(!v6.contains(ip("10.0.0.1")));
        assert!("10.0.0.0/33".parse::<Cidr>().is_err());
        assert!("bad".parse::<Cidr>().is_err());
        let any: Cidr = "0.0.0.0/0".parse().unwrap();
        assert!(any.contains(ip("8.8.8.8")));
    }

    #[test]
    fn ipv6_rate_key_is_slash64() {
        assert_eq!(rate_key(ip("1.2.3.4")), "1.2.3.4");
        assert_eq!(rate_key(ip("::ffff:1.2.3.4")), "1.2.3.4");
        let a = rate_key(ip("2001:db8:1:2::1"));
        assert_eq!(a, "2001:db8:1:2::/64");
        assert_eq!(a, rate_key(ip("2001:db8:1:2:ffff:eeee:dddd:cccc")));
        assert_ne!(a, rate_key(ip("2001:db8:1:3::1")));
    }

    #[test]
    fn forwarded_for_only_from_trusted_proxy() {
        let t: Vec<Cidr> = vec!["10.0.0.0/8".parse().unwrap()];
        // Ishonchsiz ulanish — sarlavha e'tiborsiz (soxtalashtirish).
        assert_eq!(client_ip(ip("8.8.8.8"), &["1.2.3.4"], &t), ip("8.8.8.8"));
        // Ishonchli proksi — o'ngdan birinchi ishonchsiz manzil.
        assert_eq!(client_ip(ip("10.0.0.5"), &["1.2.3.4"], &t), ip("1.2.3.4"));
        // Mijoz o'zi qo'shgan soxta chap qism e'tiborsiz: proksi zanjiri o'ngdan o'qiladi.
        assert_eq!(
            client_ip(ip("10.0.0.5"), &["6.6.6.6, 1.2.3.4, 10.0.0.9"], &t),
            ip("1.2.3.4")
        );
        // Bir nechta sarlavha qatori.
        assert_eq!(
            client_ip(ip("10.0.0.5"), &["6.6.6.6", "1.2.3.4"], &t),
            ip("1.2.3.4")
        );
        // Yaroqsiz yozuv — oxirgi ishonchli hop.
        assert_eq!(client_ip(ip("10.0.0.5"), &["junk"], &t), ip("10.0.0.5"));
        assert_eq!(client_ip(ip("10.0.0.5"), &[], &t), ip("10.0.0.5"));
    }
}
