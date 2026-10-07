//! "Kelajagim"dan pul olish: pauza va tasdiq (SPEC 2.2). Pul darrov chiqmaydi.
use time::{Duration, OffsetDateTime};

use crate::WithdrawalStatus;

/// Standart pauza: 24 soat.
pub const DEFAULT_COOLDOWN_SECS: i64 = 24 * 3600;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConfirmCheck {
    Ok,
    /// Pauza tugamagan; qolgan soniyalar.
    Cooling {
        remaining_secs: i64,
    },
    NotPending,
}

#[must_use]
pub fn available_at(requested_at: OffsetDateTime, cooldown_secs: i64) -> OffsetDateTime {
    requested_at + Duration::seconds(cooldown_secs)
}

#[must_use]
pub fn check_confirm(
    status: WithdrawalStatus,
    available_at: OffsetDateTime,
    now: OffsetDateTime,
) -> ConfirmCheck {
    if status != WithdrawalStatus::Pending {
        return ConfirmCheck::NotPending;
    }
    if now < available_at {
        return ConfirmCheck::Cooling {
            remaining_secs: (available_at - now).whole_seconds(),
        };
    }
    ConfirmCheck::Ok
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cooldown_then_ok() {
        let t0 = OffsetDateTime::UNIX_EPOCH;
        let at = available_at(t0, 100);
        assert_eq!(
            check_confirm(WithdrawalStatus::Pending, at, t0 + Duration::seconds(40)),
            ConfirmCheck::Cooling { remaining_secs: 60 }
        );
        assert_eq!(
            check_confirm(WithdrawalStatus::Pending, at, at),
            ConfirmCheck::Ok
        );
        assert_eq!(
            check_confirm(WithdrawalStatus::Confirmed, at, at),
            ConfirmCheck::NotPending
        );
        assert_eq!(
            check_confirm(WithdrawalStatus::Cancelled, at, at),
            ConfirmCheck::NotPending
        );
    }
}
