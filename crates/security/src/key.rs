use rand::{TryRng, rngs::SysRng};
use zeroize::Zeroizing;

use crate::SecurityError;

/// Kalit uzunligi (bayt): 256 bit.
pub const KEY_LEN: usize = 32;

/// 256-bitli kalit. Baytlar `Zeroizing` ichida saqlanadi: o'chirilganda xotira tozalanadi.
/// `Debug` kalit baytlarini chiqarmaydi.
pub struct SecretKey(Zeroizing<[u8; KEY_LEN]>);

impl SecretKey {
    /// OS CSPRNG'dan tasodifiy kalit.
    pub fn random() -> Result<Self, SecurityError> {
        let mut bytes = [0_u8; KEY_LEN];
        let result = SysRng.try_fill_bytes(&mut bytes);
        if let Err(error) = result {
            zeroize::Zeroize::zeroize(&mut bytes);
            return Err(SecurityError::Rng(error.to_string()));
        }
        Ok(Self::from_array(bytes))
    }

    /// Tayyor massivdan kalit. Massivning nusxasi tozalanishi chaqiruvchi zimmasida.
    pub fn from_array(bytes: [u8; KEY_LEN]) -> Self {
        Self(Zeroizing::new(bytes))
    }

    /// Baytlar ketma-ketligidan kalit. Uzunlik 32 bo'lmasa — `None`.
    pub fn from_slice(bytes: &[u8]) -> Option<Self> {
        let array: [u8; KEY_LEN] = bytes.try_into().ok()?;
        Some(Self::from_array(array))
    }

    /// Kalit baytlari. Faqat shifrlash va bazani ochish uchun ishlatilsin.
    pub fn as_bytes(&self) -> &[u8; KEY_LEN] {
        &self.0
    }
}

impl std::fmt::Debug for SecretKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("SecretKey(<yashirin>)")
    }
}
