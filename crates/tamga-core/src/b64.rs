//! base64url, to'ldirishsiz (RFC 4648 §5) — spec §2.3.

use base64::Engine as _;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;

pub fn encode(bytes: &[u8]) -> String {
    URL_SAFE_NO_PAD.encode(bytes)
}

/// Qat'iy dekodlash: to'ldirish (`=`) va kanonik bo'lmagan oxirgi bitlar rad etiladi.
pub fn decode(s: &str) -> Option<Vec<u8>> {
    let bytes = URL_SAFE_NO_PAD.decode(s).ok()?;
    (encode(&bytes) == s).then_some(bytes)
}

#[cfg(test)]
mod tests {
    #[test]
    fn round_trip_and_strictness() {
        // RFC 4648 §10 namunalari (to'ldirishsiz).
        for (raw, enc) in [
            ("", ""),
            ("f", "Zg"),
            ("fo", "Zm8"),
            ("foo", "Zm9v"),
            ("foob", "Zm9vYg"),
        ] {
            assert_eq!(super::encode(raw.as_bytes()), enc);
            assert_eq!(super::decode(enc).unwrap(), raw.as_bytes());
        }
        assert!(super::decode("Zg==").is_none(), "to'ldirish rad etiladi");
        assert!(
            super::decode("Zh").is_none(),
            "kanonik bo'lmagan oxirgi bitlar"
        );
        assert_eq!(super::encode(&[0xfb, 0xff]), "-_8", "url-safe alifbo");
    }
}
