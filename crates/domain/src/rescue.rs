//! «Qutqarilgan pul» (SPEC 2B.7, MVP_PLAN VAZIFA 8). Formula mobil `rescue.dart` bilan bir xil.
//!
//! * havas kamayishi = bazaviy davr havasi × (joriy davrning o'tgan kunlari / bazaviy davr kunlari)
//!   − joriy davr havasi. Manfiy bo'lishi mumkin: ko'rsatishda 0 (ayblov yo'q);
//! * + bekor qilingan obunalar tejami ([`subscription_savings`]);
//! * + shu davrda yopilgan konvert qoldiqlari.
//!
//! Yaxlitlash yarmidan boshlab yuqoriga (half-up). Pul faqat minor birlikda, faqat shu modulda hisoblanadi.

use money::{Currency, Money, round_half_up_div};
use time::Date;

use crate::calendar::DateRange;
use crate::{DomainError, Meta, validate_uuid_v7};

/// Obuna tejami uchun oylik ekvivalent kun soni (mobil bilan bir xil).
pub const MONTH_DAYS: i128 = 30;

/// «Qutqarilgan pul» manbasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RescueKind {
    /// Bekor qilingan obuna (oylik ekvivalent).
    Subscription,
    /// Konvert qoldig'i (hafta oxirida kiritiladi).
    EnvelopeLeftover,
    /// «Kelajagim»ga o'tkazilgan (o'tkazish shu manbadan kamayadi).
    Transfer,
}

impl RescueKind {
    /// Bazadagi kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Subscription => "SUBSCRIPTION",
            Self::EnvelopeLeftover => "ENVELOPE_LEFTOVER",
            Self::Transfer => "TRANSFER",
        }
    }

    /// Koddan tur. Noma'lum kod — `None`.
    pub fn from_code(code: &str) -> Option<Self> {
        match code {
            "SUBSCRIPTION" => Some(Self::Subscription),
            "ENVELOPE_LEFTOVER" => Some(Self::EnvelopeLeftover),
            "TRANSFER" => Some(Self::Transfer),
            _ => None,
        }
    }
}

/// «Qutqarilgan pul» yozuvi (qo'shiladi, o'zgartirilmaydi).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SavingsRescue {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Manba turi.
    pub kind: RescueKind,
    /// Summa (musbat).
    pub amount: Money,
    /// Sana (Toshkent).
    pub occurred_on: Date,
    /// Manba identifikatori (obuna yoki konvert), bo'lsa.
    pub source_id: Option<String>,
    /// Metama'lumot.
    pub meta: Meta,
}

impl SavingsRescue {
    /// Yangi yozuv. Summa musbat bo'lishi kerak. Manba identifikatori — [`SavingsRescue::with_source`] bilan.
    pub fn create(
        id: &str,
        household_id: &str,
        kind: RescueKind,
        amount: Money,
        occurred_on: Date,
        now: time::OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if amount.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            kind,
            amount,
            occurred_on,
            source_id: None,
            meta: Meta::created(now, origin_device_id),
        })
    }

    /// Manba identifikatorini qo'yadi (obuna yoki konvert).
    pub fn with_source(mut self, source_id: Option<String>) -> Self {
        self.source_id = source_id;
        self
    }
}

/// Qutqarilgan pul hisobining tarkibi (bitta davr uchun).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RescueBreakdown {
    /// Havas kamayishi; manfiy — ko'proq sarflangan.
    pub havas_delta: Money,
    /// Bekor qilingan obunalar tejami.
    pub subscriptions: Money,
    /// Konvert qoldiqlari.
    pub envelopes: Money,
    /// Shu davrda «Kelajagim»ga o'tkazilgan.
    pub transferred: Money,
    /// Bazaviy davr tanlanganmi.
    pub has_baseline: bool,
}

impl RescueBreakdown {
    /// Ko'proq sarflanganmi (ayblovsiz: faqat holat).
    pub fn spent_more(&self) -> bool {
        self.havas_delta.minor() < 0
    }

    /// Ko'rsatiladigan havas qismi — manfiy bo'lsa 0.
    pub fn havas_shown(&self) -> Money {
        non_negative(self.havas_delta)
    }

    /// Jami qutqarilgan (havas qismi + obunalar + konvertlar).
    pub fn total(&self) -> Result<Money, DomainError> {
        Ok(self
            .havas_shown()
            .checked_add(self.subscriptions)?
            .checked_add(self.envelopes)?)
    }

    /// Hali o'tkazilmagan qismi — manfiy bo'lmaydi.
    pub fn available(&self) -> Result<Money, DomainError> {
        Ok(non_negative(self.total()?.checked_sub(self.transferred)?))
    }
}

fn non_negative(money: Money) -> Money {
    if money.minor() < 0 {
        Money::zero(money.currency())
    } else {
        money
    }
}

/// «Qutqarilgan pul» formulasi. `baseline` — (bazaviy davr havasi, bazaviy davr kunlari).
/// `elapsed_days` — joriy davrning o'tgan kunlari (bugun kiradi).
pub fn compute_rescue(
    currency: Currency,
    elapsed_days: i64,
    current_havas: Money,
    baseline: Option<(Money, i64)>,
    subscriptions: Money,
    envelopes: Money,
    transferred: Money,
) -> Result<RescueBreakdown, DomainError> {
    if elapsed_days <= 0 {
        return Err(DomainError::InvalidDay);
    }
    let (havas_delta, has_baseline) = match baseline {
        None => (Money::zero(currency), false),
        Some((base, base_days)) => {
            if base_days <= 0 {
                return Err(DomainError::InvalidDay);
            }
            let scaled = round_half_up_div(
                i128::from(base.minor()) * i128::from(elapsed_days),
                i128::from(base_days),
            )?;
            let scaled_minor = i64::try_from(scaled).unwrap_or(i64::MAX);
            let delta = scaled_minor.saturating_sub(current_havas.minor());
            (Money::new(delta, currency), true)
        }
    };
    Ok(RescueBreakdown {
        havas_delta,
        subscriptions,
        envelopes,
        transferred,
        has_baseline,
    })
}

/// Bekor qilingan obunalar tejami davrda: har biri bekor qilingan kundan (davr boshidan oldin bo'lsa —
/// davr boshidan) [`today`] gacha, oylik ekvivalent × kunlar / 30. Butun so'mgacha yaxlitlanadi.
pub fn subscription_savings(
    currency: Currency,
    cancelled: &[(Money, Date)],
    period: DateRange,
    today: Date,
) -> Result<Money, DomainError> {
    let per_major = i128::from(currency.minor_per_major());
    let mut total_minor: i128 = 0;
    for (monthly, on) in cancelled {
        if monthly.currency() != currency {
            continue;
        }
        let from = if *on > period.start {
            *on
        } else {
            period.start
        };
        if from >= period.end || today < from {
            continue;
        }
        let days = i128::from((today - from).whole_days()) + 1;
        total_minor += round_half_up_div(i128::from(monthly.minor()) * days, MONTH_DAYS)?;
    }
    let whole_major = round_half_up_div(total_minor, per_major)?;
    Ok(Money::new(
        i64::try_from(whole_major * per_major).unwrap_or(i64::MAX),
        currency,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::calendar::DateRange;
    use time::macros::{date, datetime};

    const ID: &str = "0192f000-0000-7000-8000-000000000001";
    const HOUSEHOLD: &str = "0192f000-0000-7000-8000-0000000000aa";

    fn uzs(minor: i64) -> Money {
        Money::new(minor, Currency::Uzs)
    }

    #[test]
    fn manba_kodi_qaytariladi() {
        for kind in [
            RescueKind::Subscription,
            RescueKind::EnvelopeLeftover,
            RescueKind::Transfer,
        ] {
            assert_eq!(RescueKind::from_code(kind.code()), Some(kind));
        }
        assert_eq!(RescueKind::from_code("NOMA_LUM"), None);
    }

    #[test]
    fn manfiy_holat_nolga_tushadi() {
        let breakdown = compute_rescue(
            Currency::Uzs,
            10,
            uzs(150_000_000),
            Some((uzs(300_000_000), 30)),
            uzs(0),
            uzs(0),
            uzs(0),
        )
        .expect("hisob");
        assert!(breakdown.spent_more());
        assert_eq!(breakdown.havas_shown(), uzs(0));
        assert_eq!(breakdown.total().expect("jami"), uzs(0));
    }

    #[test]
    fn qoldiq_transferdan_kop_bolmaydi() {
        let breakdown = compute_rescue(
            Currency::Uzs,
            10,
            uzs(0),
            None,
            uzs(10_000_000),
            uzs(5_000_000),
            uzs(20_000_000),
        )
        .expect("hisob");
        assert_eq!(breakdown.available().expect("qoldiq"), uzs(0));
    }

    #[test]
    fn bosh_davr_hisoblanmaydi() {
        assert!(matches!(
            compute_rescue(Currency::Uzs, 0, uzs(0), None, uzs(0), uzs(0), uzs(0)),
            Err(DomainError::InvalidDay)
        ));
    }

    #[test]
    fn obuna_tejami_davr_boshidan_hisoblanadi() {
        let period = DateRange {
            start: date!(2026 - 10 - 01),
            end: date!(2026 - 11 - 01),
        };
        // Bekor qilingan davrdan oldin — davr boshidan hisoblanadi: 30 kun × oylik / 30.
        let savings = subscription_savings(
            Currency::Uzs,
            &[(uzs(30_000_000), date!(2026 - 09 - 15))],
            period,
            date!(2026 - 10 - 30),
        )
        .expect("tejam");
        assert_eq!(savings, uzs(30_000_000));
    }

    #[test]
    fn create_summa_musbat_bolishi_kerak() {
        let now = datetime!(2026-10-15 06:00 UTC);
        assert_eq!(
            SavingsRescue::create(
                ID,
                HOUSEHOLD,
                RescueKind::Transfer,
                uzs(0),
                date!(2026 - 10 - 15),
                now,
                "desktop",
            ),
            Err(DomainError::AmountNotPositive)
        );
    }
}
