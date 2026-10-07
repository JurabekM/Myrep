/// `Enum <-> DB matni`. Matn qiymatlari SPEC va mobil ilova bilan bir xil (UPPER_SNAKE).
macro_rules! str_enum {
    ($(#[$m:meta])* $name:ident { $($variant:ident => $text:literal),+ $(,)? }) => {
        $(#[$m])*
        #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
        pub enum $name { $($variant),+ }

        impl $name {
            #[must_use]
            pub const fn as_str(self) -> &'static str {
                match self { $(Self::$variant => $text),+ }
            }

            #[must_use]
            pub fn parse(s: &str) -> Option<Self> {
                match s { $($text => Some(Self::$variant),)+ _ => None }
            }
        }
    };
}

str_enum!(MemberRole { Adult => "ADULT", Child => "CHILD", Viewer => "VIEWER" });
str_enum!(
    /// SPEC 2B.2. Kelajak maydoni: jadvallarda hozirdan nullable.
    Necessity { Zarur => "ZARUR", Kerak => "KERAK", Havas => "HAVAS" }
);
str_enum!(PaymentChannel { Cash => "CASH", Card => "CARD" });
str_enum!(AssetType {
    Cash => "CASH", BankCard => "BANK_CARD", Vault => "VAULT", Gold => "GOLD",
    Silver => "SILVER", ForeignCurrency => "FOREIGN_CURRENCY", Receivable => "RECEIVABLE",
    TradeGoods => "TRADE_GOODS", BusinessShare => "BUSINESS_SHARE",
});
str_enum!(VaultTxKind { Deposit => "DEPOSIT", Withdraw => "WITHDRAW" });
str_enum!(AllocationKind { Percent => "PERCENT", FixedAmount => "FIXED_AMOUNT" });

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn text_roundtrip() {
        for t in [AssetType::Cash, AssetType::BusinessShare, AssetType::Vault] {
            assert_eq!(AssetType::parse(t.as_str()), Some(t));
        }
        assert_eq!(Necessity::parse("HAVAS"), Some(Necessity::Havas));
        assert_eq!(MemberRole::parse("nope"), None);
    }
}
