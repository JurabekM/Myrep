//! Kelishuvlarni ko'rib chiqish va nizo (SPEC 2F.4, 2F.5, 2F.8; DESKTOP_PROMPT D13A).
//!
//! * `IN_DISPUTE` holatida taqsimot bloklanadi (`IN_DISPUTE`).
//! * Yillik yangilash eslatmasi: `review_date` dan 30 kun oldin.

use time::{Date, Duration};

use crate::DomainError;
use crate::agreement::AgreementStatus;

/// Yillik yangilash eslatmasi: sanadan necha kun oldin.
pub const REVIEW_REMINDER_DAYS: i64 = 30;

/// Yangilash eslatmasi kerakmi: bugun `review_date − 30 kun` yoki undan keyin bo'lsa.
pub fn review_reminder_due(review_date: Date, today: Date) -> bool {
    today >= review_date - Duration::days(REVIEW_REMINDER_DAYS)
}

/// Taqsimot ruxsat etilganmi. Nizoda (`IN_DISPUTE`) — rad etiladi.
pub fn ensure_distribution_allowed(status: AgreementStatus) -> Result<(), DomainError> {
    if status == AgreementStatus::InDispute {
        return Err(DomainError::DistributionBlocked);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use time::macros::date;

    #[test]
    fn eslatma_30_kun_oldin_keladi() {
        let review = date!(2027 - 10 - 01);
        assert!(!review_reminder_due(review, date!(2027 - 08 - 31)));
        assert!(review_reminder_due(review, date!(2027 - 09 - 01)));
    }

    #[test]
    fn nizoda_taqsimot_bloklanadi() {
        assert_eq!(
            ensure_distribution_allowed(AgreementStatus::InDispute),
            Err(DomainError::DistributionBlocked)
        );
        assert!(ensure_distribution_allowed(AgreementStatus::Signed).is_ok());
    }
}
