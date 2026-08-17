//! Domain separation const'lar — spec 5-bo'lim, band S4.

/// `\ . / / ^ \` — DEFAULT (X-Wing) profil uchun KEM combiner label'i.
pub const XWING_LABEL: &[u8] = &[0x5c, 0x2e, 0x2f, 0x2f, 0x5e, 0x5c];

/// PARANOID (Triple-Hybrid) profil uchun KEM combiner label'i.
pub const PARANOID_LABEL: &[u8] = b"AETHER-Q-v3-KEM/L3/v1";

/// AUTH-AKEM (0x05) profil uchun transcript/combiner label'i.
pub const AKEM_LABEL: &[u8] = b"AETHER-Q-v4-AKEM/L3/v1";

/// Record layer (7-bo'lim) HKDF-Expand konteksti uchun yo'nalishga xos label'lar.
pub const RECORD_C2S_KEY_LABEL: &[u8] = b"AETHER-Q-v4/c2s/key";
pub const RECORD_S2C_KEY_LABEL: &[u8] = b"AETHER-Q-v4/s2c/key";
pub const RECORD_C2S_NIV_LABEL: &[u8] = b"AETHER-Q-v4/c2s/niv";
pub const RECORD_S2C_NIV_LABEL: &[u8] = b"AETHER-Q-v4/s2c/niv";

/// Implicit Rejection fallback label'i (spec 4.1, band 4).
pub const REJECT_LABEL: &[u8] = b"REJECT";
