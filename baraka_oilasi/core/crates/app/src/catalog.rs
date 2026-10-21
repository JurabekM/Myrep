//! Makon turiga qarab standart kategoriyalar (i18n kalitlari bilan).
use baraka_domain_common::SpaceKind;

/// `(name_key, standart toifa)`. `None` — toifasiz (masalan, sadaqa: havas emas).
pub(crate) fn default_categories(
    kind: SpaceKind,
) -> &'static [(&'static str, Option<&'static str>)] {
    match kind {
        SpaceKind::Uy => &[
            ("category.food", Some("ZARUR")),
            ("category.rent", Some("ZARUR")),
            ("category.utilities", Some("ZARUR")),
            ("category.transport", Some("ZARUR")),
            ("category.medicine", Some("ZARUR")),
            ("category.debt_payment", Some("ZARUR")),
            ("category.phone", Some("KERAK")),
            ("category.clothes", Some("KERAK")),
            ("category.child_education", Some("KERAK")),
            ("category.snacks", Some("HAVAS")),
            ("category.cafe", Some("HAVAS")),
            ("category.entertainment", Some("HAVAS")),
            ("category.gifts", Some("KERAK")),
            (SADAQA_KEY, None),
            ("category.other", None),
        ],
        SpaceKind::Kasbkor => &[
            ("category.kk.materials", None),
            ("category.kk.rent", None),
            ("category.kk.wages", None),
            ("category.kk.transport", None),
            ("category.kk.marketing", None),
            ("category.kk.tax", None),
            ("category.kk.equipment", None),
            ("category.kk.other", None),
        ],
        SpaceKind::Musofir => &[
            ("category.mf.rent", Some("ZARUR")),
            ("category.mf.food", Some("ZARUR")),
            ("category.mf.transport", Some("ZARUR")),
            ("category.mf.phone", Some("KERAK")),
            ("category.mf.transfer_fee", Some("ZARUR")),
            ("category.mf.other", None),
        ],
    }
}

/// Sadaqa kategoriyasi: havas va «oqib ketish» hisobiga kirmaydi (uy/SPEC 2B.8).
pub(crate) const SADAQA_KEY: &str = "category.sadaqa";

/// Boshlang'ich avto-ulush: 5% (uy/SPEC 2.2).
pub(crate) const DEFAULT_SHARE_BP: i64 = 500;

#[cfg(test)]
mod tests {
    use super::*;

    /// Har bir standart kategoriya nomi tarjima manbasida bor (aks holda UI kalitni ko'rsatadi).
    #[test]
    fn every_category_key_is_translated() {
        let uz = include_str!("../../../../shared/i18n/uz.json");
        let ru = include_str!("../../../../shared/i18n/ru.json");
        for kind in SpaceKind::ALL {
            for (key, _) in default_categories(*kind) {
                let needle = format!("\"{key}\":");
                assert!(uz.contains(&needle), "uz.json: {key}");
                assert!(ru.contains(&needle), "ru.json: {key}");
            }
        }
    }
}
