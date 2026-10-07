use crate::TaskTrigger;

/// Bir haftaning ilova ma'lumotlaridan hisoblangan faktlari.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct WeekFacts {
    pub income_count: u32,
    /// Ajratma qilingan turli kunlar soni.
    pub allocation_days: u32,
    pub audit_completed: bool,
    pub obligations_added: u32,
}

/// Avtomatik trigger shartlari. `Manual` doim `false` (foydalanuvchi belgilaydi).
#[must_use]
pub const fn trigger_met(trigger: TaskTrigger, facts: &WeekFacts) -> bool {
    match trigger {
        TaskTrigger::Manual => false,
        TaskTrigger::IncomeRecorded { min } => facts.income_count >= min,
        TaskTrigger::AllocationMade { min_days } => facts.allocation_days >= min_days,
        TaskTrigger::AuditCompleted => facts.audit_completed,
        TaskTrigger::ObligationAdded => facts.obligations_added >= 1,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn each_trigger_reads_its_own_fact() {
        let none = WeekFacts::default();
        let some = WeekFacts {
            income_count: 2,
            allocation_days: 1,
            audit_completed: true,
            obligations_added: 1,
        };
        for t in [
            TaskTrigger::IncomeRecorded { min: 1 },
            TaskTrigger::AllocationMade { min_days: 1 },
            TaskTrigger::AuditCompleted,
            TaskTrigger::ObligationAdded,
        ] {
            assert!(!trigger_met(t, &none), "{t:?}");
            assert!(trigger_met(t, &some), "{t:?}");
        }
        assert!(!trigger_met(TaskTrigger::Manual, &some));
    }

    #[test]
    fn thresholds_are_inclusive() {
        let f = WeekFacts {
            income_count: 2,
            allocation_days: 2,
            ..WeekFacts::default()
        };
        assert!(trigger_met(TaskTrigger::IncomeRecorded { min: 2 }, &f));
        assert!(!trigger_met(TaskTrigger::IncomeRecorded { min: 3 }, &f));
        assert!(trigger_met(TaskTrigger::AllocationMade { min_days: 2 }, &f));
        assert!(!trigger_met(
            TaskTrigger::AllocationMade { min_days: 3 },
            &f
        ));
    }
}
