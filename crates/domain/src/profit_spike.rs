//! «Katta foyda» ogohlantirishi (SPEC 2F.7, DESKTOP_PROMPT D13A): taqsimotdan oldin navbatdan tashqari ko'rik.
//!
//! Ogohlantirish (`alert`), agar foyda musbat bo'lib, quyidagilardan kamida biri bajarilsa:
//! * A — reja bor (`plan > 0`) va `actual ≥ 1,5 × plan`;
//! * B — oxirgi uch davr ma'lum va `S > 0` (S — uch davr yig'indisi) va `actual ≥ 2 × (S / 3)`.
//!
//! Hammasi butun sonlarda: bo'lish yo'q, solishtirish ko'paytirish orqali (`actual·10 000 ≥ plan·15 000`).

/// A qoida: reja bo'yicha chegara, 150% (bp: 15 000 / 10 000).
const PLAN_NUMERATOR: i128 = 15_000;
/// B qoida: uch davr o'rtachasi bo'yicha chegara, 200%.
const AVERAGE_NUMERATOR: i128 = 20_000;

/// Ogohlantirish holati.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SpikeInput {
    /// Rejadagi foyda (minor), bo'lsa.
    pub plan: Option<i64>,
    /// Oxirgi uch davr foydasi (minor), to'liq bo'lsa.
    pub last_three: Option<[i64; 3]>,
    /// Joriy davr foydasi (minor).
    pub actual: i64,
}

/// Ogohlantirish kerakmi.
pub fn profit_spike_alert(input: SpikeInput) -> bool {
    let actual = i128::from(input.actual);
    if actual <= 0 {
        return false;
    }
    let by_plan = input
        .plan
        .is_some_and(|plan| plan > 0 && actual * 10_000 >= i128::from(plan) * PLAN_NUMERATOR);
    let by_average = input.last_three.is_some_and(|last| {
        let total: i128 = last.iter().map(|value| i128::from(*value)).sum();
        total > 0 && actual * 3 * 10_000 >= total * AVERAGE_NUMERATOR
    });
    by_plan || by_average
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn chegara_aniq_olinadi() {
        let at_limit = SpikeInput {
            plan: Some(100_000_000),
            last_three: None,
            actual: 150_000_000,
        };
        assert!(profit_spike_alert(at_limit));
        assert!(!profit_spike_alert(SpikeInput {
            actual: 149_999_999,
            ..at_limit
        }));
    }
}
