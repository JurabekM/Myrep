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
/// Async (masalan DB'ga murojaat): `PqLinkServer::commit_finish` dan chaqiriladi.
#[async_trait::async_trait]
pub trait EnrollmentGate: Send + Sync + std::fmt::Debug {
    /// Qurilma ro'yxatda bo'lsa — ruxsat; bo'lmasa `attestation_challenge` haqiqiy, ishlatilmagan va
    /// muddati o'tmagan nonce bo'lishi shart (u iste'mol qilinadi va qurilma ro'yxatga olinadi).
    /// Qaytaradi: qurilma oxirgi marta attestatsiyadan o'tgan vaqt (unix) — sessiyaga yoziladi,
    /// davriy qayta attestatsiya har so'rovda reyestrga murojaatsiz tekshiriladi (ADR-0015).
    async fn admit(&self, device: &VerifiedDevice) -> Result<i64, PqLinkError>;
}
