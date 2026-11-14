//! `.baraka` almashish qoidalari (SPEC 6.3, DESKTOP_PROMPT D14): kalit qurilma va fork aniqlash.
//!
//! * Har bir kelishuvning bitta hisob yurituvchi qurilmasi bor (`custody.keeper_device_id`).
//!   Jurnalga faqat shu qurilma yozadi; boshqasida jurnal faqat o'qish uchun.
//! * Import paytida zanjir tekshiriladi. Mahalliy va kiruvchi zanjir bir xil oraliqda farq qilsa —
//!   FORK: import to'xtatiladi, avtomatik birlashtirilmaydi.

use crate::DomainError;

/// Yozuvni faqat kalit qurilma qo'shishi mumkin.
pub fn ensure_keeper(keeper_device_id: &str, writer_device_id: &str) -> Result<(), DomainError> {
    if keeper_device_id != writer_device_id {
        return Err(DomainError::NotKeeperDevice);
    }
    Ok(())
}

/// Ikki zanjirni solishtiradi. Umumiy oraliqda xeshlar farq qilsa — birinchi farq (1 dan) qaytadi.
/// Yo'q bo'lsa — `Ok(())`: kiruvchi zanjir mahalliyning davomi yoki undan qisqa.
pub fn check_import(local_hashes: &[String], incoming_hashes: &[String]) -> Result<(), usize> {
    for (index, (local, incoming)) in local_hashes.iter().zip(incoming_hashes.iter()).enumerate() {
        if local != incoming {
            return Err(index + 1);
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn faqat_kalit_qurilma_yozadi() {
        assert!(ensure_keeper("desktop-1", "desktop-1").is_ok());
        assert_eq!(
            ensure_keeper("desktop-1", "phone-1"),
            Err(DomainError::NotKeeperDevice)
        );
    }

    #[test]
    fn fork_birinchi_farq_bilan_topiladi() {
        let local = vec!["a".to_owned(), "b".to_owned(), "c".to_owned()];
        let same_prefix = vec!["a".to_owned(), "b".to_owned(), "d".to_owned()];
        assert_eq!(check_import(&local, &same_prefix), Err(3));
        assert_eq!(check_import(&local, &local[..2]), Ok(()));
    }
}
