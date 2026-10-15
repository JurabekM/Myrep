use serde::{Deserialize, Serialize};

/// Matn ko'rinishi barqaror bo'lgan enum'lar uchun `as_str` / `parse`.
macro_rules! str_enum {
    ($(#[$m:meta])* $name:ident { $($variant:ident => $text:literal),+ $(,)? }) => {
        $(#[$m])*
        #[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
        pub enum $name {
            $(#[serde(rename = $text)] $variant),+
        }

        impl $name {
            pub const ALL: &'static [$name] = &[$($name::$variant),+];

            pub const fn as_str(self) -> &'static str {
                match self { $($name::$variant => $text),+ }
            }

            pub fn parse(s: &str) -> Option<Self> {
                Self::ALL.iter().copied().find(|v| v.as_str() == s)
            }
        }
    };
}

str_enum!(
    /// Ilova ichidagi makon (2.2).
    SpaceKind { Uy => "UY", Kasbkor => "KASBKOR", Musofir => "MUSOFIR" }
);

str_enum!(
    /// Oila a'zosining roli.
    MemberRole { Adult => "ADULT", Child => "CHILD" }
);

str_enum!(
    /// Xarajat zaruriyati: avval ZARUR, keyin KERAK, oxirida HAVAS (uy/SPEC 2B.2).
    Necessity { Zarur => "ZARUR", Kerak => "KERAK", Havas => "HAVAS" }
);

str_enum!(
    /// To'lov kanali.
    Channel { Cash => "CASH", Card => "CARD" }
);

str_enum!(
    /// Qiymat saqlovchi aktiv turi (uy/SPEC 4.3).
    AssetType {
        Cash => "CASH",
        BankCard => "BANK_CARD",
        Vault => "VAULT",
        Gold => "GOLD",
        Silver => "SILVER",
        ForeignCurrency => "FOREIGN_CURRENCY",
        Receivable => "RECEIVABLE",
        TradeGoods => "TRADE_GOODS",
        BusinessShare => "BUSINESS_SHARE",
    }
);

str_enum!(
    /// «Kelajagim» jamg'armasining turi (uy/SPEC 2C.3).
    VaultType { Qorovul => "QOROVUL", Osadigan => "OSADIGAN" }
);

str_enum!(
    /// Halol foyda testi: ter, mol, tavakkal (yoki ribo) — ixtiyoriy belgi.
    IncomeSourceType { Ter => "TER", Mol => "MOL", Tavakkal => "TAVAKKAL", Ribo => "RIBO" }
);

str_enum!(
    /// Yozuvning oila a'zolariga ko'rinishi (OQ-M2).
    Visibility { Shared => "SHARED", Private => "PRIVATE" }
);

str_enum!(
    /// Jamg'arma harakati sababi.
    VaultReason {
        Initial => "INITIAL",
        Allocation => "ALLOCATION",
        Manual => "MANUAL",
        Withdrawal => "WITHDRAWAL",
        Rescue => "RESCUE",
    }
);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip() {
        for k in SpaceKind::ALL {
            assert_eq!(SpaceKind::parse(k.as_str()), Some(*k));
        }
        assert_eq!(AssetType::parse("BANK_CARD"), Some(AssetType::BankCard));
        assert_eq!(Necessity::parse("nope"), None);
    }
}
