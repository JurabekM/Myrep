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
str_enum!(
    /// "Kimning puli?" ekrani egalari (SPEC 2.4). "O'zingiz" va "izohsiz" hisoblanadi, saqlanmaydi.
    MoneyOwner {
        Landlord => "LANDLORD", Bank => "BANK", Shop => "SHOP", State => "STATE",
        Fuel => "FUEL", Other => "OTHER",
    }
);
str_enum!(ObligationKind { Recurring => "RECURRING", Nasiya => "NASIYA" });
str_enum!(
    /// Kelajagim yozuvining manbasi: faqat `Allocation` "o'zingizga to'langan" va streak hisobiga kiradi.
    VaultSource { Allocation => "ALLOCATION", Opening => "OPENING", Manual => "MANUAL" }
);
str_enum!(WithdrawalStatus { Pending => "PENDING", Confirmed => "CONFIRMED", Cancelled => "CANCELLED" });
str_enum!(
    /// «Qutqarilgan pul» manbasi.
    RescueKind { HavasDrop => "HAVAS_DROP", Subscription => "SUBSCRIPTION" }
);
str_enum!(
    /// «Kelajagim» ikkiga bo'linadi (SPEC 2C.3).
    VaultType { Qorovul => "QOROVUL", Osadigan => "OSADIGAN" }
);
str_enum!(
    /// Daromad manbasi: ter / mol / tavakkal testi (SPEC 2C.5). `Ribo` — foizli daromad, alohida ko'rsatiladi.
    IncomeSourceType { Ter => "TER", Mol => "MOL", Tavakkal => "TAVAKKAL", Ribo => "RIBO" }
);
str_enum!(
    /// Kreditor turi (SPEC 2C.7). Do'kon nasiyasi ham shu yerga birlashadi.
    CreditorType { Bank => "BANK", Shop => "SHOP", Relative => "RELATIVE", Friend => "FRIEND", Other => "OTHER" }
);
str_enum!(
    /// Jadval turi: `Annuity`/`Differentiated` bank shartnomasidagi jadval (simulyator D10 da);
    /// `FixedMarkup` — teng bo'laklar; `Manual` — foydalanuvchi qatorlari.
    ScheduleKind {
        Annuity => "ANNUITY", Differentiated => "DIFFERENTIATED",
        FixedMarkup => "FIXED_MARKUP", Manual => "MANUAL",
    }
);
str_enum!(
    /// Friction so'rovi: zaruratmi yoki hashamatmi (SPEC 2D.6).
    BorrowNeed { Need => "NEED", Luxury => "LUXURY" }
);
str_enum!(
    /// Friction so'rovi: foizsiz muqobil ko'rib chiqildimi.
    BorrowAlternative {
        None => "NONE", Guard => "GUARD", Relative => "RELATIVE", SellItem => "SELL_ITEM",
    }
);
str_enum!(ReceiptKind { Debt => "DEBT", Receivable => "RECEIVABLE" });
str_enum!(SellStatus { Listed => "LISTED", Sold => "SOLD" });
str_enum!(
    /// Byudjet rejimi (SPEC 2D.1).
    BudgetMode { Standard => "STANDARD", DebtRecovery => "DEBT_RECOVERY" }
);
str_enum!(
    /// Marosim turi (SPEC 2D.8).
    CeremonyKind {
        Wedding => "WEDDING", Beshik => "BESHIK", Sunnat => "SUNNAT", Maraka => "MARAKA", Other => "OTHER",
    }
);
str_enum!(
    /// Byudjet qatorining moliyalash manbasi.
    FundingSource {
        Savings => "SAVINGS", Family => "FAMILY", ExpectedGifts => "EXPECTED_GIFTS", Debt => "DEBT",
    }
);
str_enum!(CeremonyStatus { Draft => "DRAFT", Confirmed => "CONFIRMED" });

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
