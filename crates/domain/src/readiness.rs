//! Tayyorgarlik darvozasi (SPEC 2C.4, `ReadinessGate`): qarzga va sheriklikka kirishdan oldingi shart.
//!
//! Darvoza `OPEN` bo'ladi, agar: qorovul zaxirasi ≥ 6 oy VA (foizli qarz yo'q YOKI chiqish rejasi bor).
//! Aks holda `LOCKED`, sabablari bilan. Sabablar tartibi doim bir xil: avval zaxira, keyin qarz.
//! Zaxira — o'n ulushda (60 = 6,0 oy), shuning uchun butun sonlarda tekshiriladi.

/// Darvoza uchun minimal zaxira: 6,0 oy (o'n ulushda).
pub const RESERVE_TARGET_TENTHS: i64 = 60;

/// Darvoza holati.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GateState {
    /// Ochiq: qarz va sheriklik muhokamasi mumkin.
    Open,
    /// Yopiq: bir yoki bir nechta sabab bor.
    Locked,
}

impl GateState {
    /// Bazadagi va vektordagi kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Open => "OPEN",
            Self::Locked => "LOCKED",
        }
    }
}

/// Darvoza yopilishining sababi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GateReason {
    /// Zaxira 6 oydan kam.
    ReserveBelowTarget,
    /// Foizli qarz bor, lekin chiqish rejasi yo'q.
    InterestDebtWithoutPlan,
}

impl GateReason {
    /// Vektor va bazadagi kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::ReserveBelowTarget => "RESERVE_BELOW_TARGET",
            Self::InterestDebtWithoutPlan => "INTEREST_DEBT_WITHOUT_PLAN",
        }
    }
}

/// Darvoza natijasi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GateResult {
    /// Holat.
    pub state: GateState,
    /// Sabablar (`OPEN` bo'lsa — bo'sh).
    pub reasons: Vec<GateReason>,
}

/// Darvoza. `reserve_months_tenths` — zaxira oylari × 10.
pub fn readiness_gate(
    reserve_months_tenths: i64,
    has_interest_debt: bool,
    has_recovery_plan: bool,
) -> GateResult {
    let mut reasons = Vec::new();
    if reserve_months_tenths < RESERVE_TARGET_TENTHS {
        reasons.push(GateReason::ReserveBelowTarget);
    }
    if has_interest_debt && !has_recovery_plan {
        reasons.push(GateReason::InterestDebtWithoutPlan);
    }
    let state = if reasons.is_empty() {
        GateState::Open
    } else {
        GateState::Locked
    };
    GateResult { state, reasons }
}
