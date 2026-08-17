//! Umumiy maqsadli CSPRNG wrapper'i — ilova darajasidagi tasodifiy qiymatlar
//! (masalan `z_recip`, session_id) uchun, tizim entropiya manbaidan (`getrandom`).

use getrandom::rand_core::{Rng, UnwrapErr};
use getrandom::SysRng;

/// `len` baytlik kriptografik jihatdan xavfsiz tasodifiy buferni qaytaradi.
pub fn random_bytes(len: usize) -> Vec<u8> {
    let mut buf = vec![0u8; len];
    UnwrapErr(SysRng).fill_bytes(&mut buf);
    buf
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn produces_requested_length_and_varies() {
        let a = random_bytes(32);
        let b = random_bytes(32);
        assert_eq!(a.len(), 32);
        assert_ne!(a, b);
    }
}
