//! Sirlarni (API kalit, token, .env) yozuvdan oldin yashirish
//!
//! F0: skelet. Haqiqiy implementatsiya docs/PLAN.md dagi bosqichda.

/// AAR format versiyasi, crate qaysi spec bilan mos ekani.
pub const AAR_VERSION: &str = "0.1";

#[cfg(test)]
mod tests {
    #[test]
    fn version_is_set() {
        assert_eq!(super::AAR_VERSION, "0.1");
    }
}
