//! Qurilmani ro'yxatdan o'tkazish darvozasi (1-faza P1.7, ADR-0013).
//!
//! Android Key Attestation qurilma holatini (bootloader, verified boot) kalit **yaratilgan paytdagi**
//! holatda yozadi. Shuning uchun yangi qurilma kalitini serverning bir martalik nonce'i bilan
//! (`attestationChallenge`) yaratadi — attestatsiya yangi ekani isbotlanadi. Server ro'yxatga olingan
//! qurilmalarni eslab qoladi; keyingi ulanishlarda nonce talab qilinmaydi.

use crate::attestation::VerifiedDevice;
use crate::PqLinkError;

/// Handshake'da attestatsiya va qurilma imzosi tekshirilgandan keyin chaqiriladi.
///
/// Amalga oshirish bloklovchi bo'lishi mumkin (masalan DB): `PqLinkServer::handle_finish` async
/// kontekstdan emas, bloklovchi oqimdan (`spawn_blocking`) chaqirilishi kerak.
pub trait EnrollmentGate: Send + Sync + std::fmt::Debug {
    /// Qurilma ro'yxatda bo'lsa — ruxsat; bo'lmasa `attestation_challenge` haqiqiy, ishlatilmagan va
    /// muddati o'tmagan nonce bo'lishi shart (u iste'mol qilinadi va qurilma ro'yxatga olinadi).
    fn admit(&self, device: &VerifiedDevice) -> Result<(), PqLinkError>;
}
