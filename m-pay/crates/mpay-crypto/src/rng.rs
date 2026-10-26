//! OS CSPRNG (`getrandom`). Boshqa tasodifiylik manbalari ishlatilmaydi.

use zeroize::Zeroizing;

use crate::CryptoError;

/// Buferni OS CSPRNG bilan to'ldiradi.
pub fn fill(buf: &mut [u8]) -> Result<(), CryptoError> {
    getrandom::fill(buf).map_err(|_| CryptoError::Rng)
}

/// `N` tasodifiy bayt (maxfiy bo'lmagan qiymatlar: nonce, ID, UN).
pub fn array<const N: usize>() -> Result<[u8; N], CryptoError> {
    let mut a = [0u8; N];
    fill(&mut a)?;
    Ok(a)
}

/// `N` tasodifiy maxfiy bayt (kalitlar uchun) — `Drop` da tozalanadi.
pub fn secret_array<const N: usize>() -> Result<Zeroizing<[u8; N]>, CryptoError> {
    let mut a = Zeroizing::new([0u8; N]);
    fill(&mut a[..])?;
    Ok(a)
}

/// `0..bound` oralig'ida bir xil taqsimlangan son (rad etish usuli, `bound > 0`).
pub fn below(bound: u64) -> Result<u64, CryptoError> {
    if bound == 0 {
        return Err(CryptoError::BadInput("bound = 0"));
    }
    let zone = u64::MAX - (u64::MAX % bound);
    loop {
        let v = u64::from_be_bytes(array::<8>()?);
        if v < zone {
            return Ok(v % bound);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn random_values_differ() {
        assert_ne!(array::<32>().unwrap(), array::<32>().unwrap());
        for _ in 0..100 {
            assert!(below(10).unwrap() < 10);
        }
        assert!(below(0).is_err());
    }
}
