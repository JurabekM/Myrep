use argon2::{Algorithm, Argon2, Params, Version};
use zeroize::Zeroize;

use crate::key::KEY_LEN;
use crate::{SecretKey, SecurityError};

/// Tuz uzunligi (bayt).
pub const SALT_LEN: usize = 16;

/// Argon2id parametrlari. Fayl ichida saqlanadi, shuning uchun kelajakda oshirish mumkin.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct KdfParams {
    /// Xotira narxi (KiB).
    pub m_cost_kib: u32,
    /// Takrorlashlar soni.
    pub t_cost: u32,
    /// Parallellik darajasi.
    pub p_cost: u32,
}

impl KdfParams {
    /// OWASP tavsiyasi: Argon2id, 19 MiB, t=2, p=1.
    pub const RECOMMENDED: Self = Self {
        m_cost_kib: 19_456,
        t_cost: 2,
        p_cost: 1,
    };

    /// Faqat testlar uchun: tez, lekin xavfsiz emas. Ishlab chiqarishda ishlatilmasin.
    pub const FAST_FOR_TESTS: Self = Self {
        m_cost_kib: 64,
        t_cost: 1,
        p_cost: 1,
    };
}

/// PIN baytlaridan va tuzdan Argon2id bilan 256-bitli kalit hosil qiladi.
pub fn derive_pin_key(
    pin: &[u8],
    salt: &[u8; SALT_LEN],
    params: KdfParams,
) -> Result<SecretKey, SecurityError> {
    let argon_params = Params::new(
        params.m_cost_kib,
        params.t_cost,
        params.p_cost,
        Some(KEY_LEN),
    )
    .map_err(|_| SecurityError::Kdf)?;
    let argon = Argon2::new(Algorithm::Argon2id, Version::V0x13, argon_params);

    let mut out = [0_u8; KEY_LEN];
    let result = argon.hash_password_into(pin, salt, &mut out);
    if result.is_err() {
        out.zeroize();
        return Err(SecurityError::Kdf);
    }
    let key = SecretKey::from_array(out);
    out.zeroize();
    Ok(key)
}
