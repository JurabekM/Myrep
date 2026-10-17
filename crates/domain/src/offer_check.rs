//! «Kafolatlangan foyda» detektori (SPEC 2E.5, DESKTOP_PROMPT D13): taklifni tekshiruv ro'yxati bo'yicha baholash.
//!
//! Natija — yashil / sariq / qizil; har bir bayroq izohlanadi.
//! Qoida (mahsulot qarori, OPEN_QUESTIONS, «Hal qilingan»):
//! * QIZIL — foyda kafolatlangan YOKI yangi a'zo jalb qilish talab qilinadi (piramida belgisi);
//! * SARIQ — shoshiltirish bor, yozma shartnoma yo'q, real mol yoki ish yo'q, yoki zarar mumkin emas deyilmoqda;
//! * YASHIL — yuqoridagilarning hech biri yo'q.

/// Shuncha (yoki ko'proq) sariq bayroq yig'ilsa — natija qizil (OPEN_QUESTIONS, «Hal qilingan»).
pub const YELLOW_FLAGS_FOR_RED: usize = 3;

/// Tekshiruv ro'yxati javoblari (`true` — shu belgi bor).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct OfferAnswers {
    /// Foyda kafolatlanganmi.
    pub guaranteed_profit: bool,
    /// Zarar bo'lishi mumkinmi.
    pub loss_possible: bool,
    /// Real mol yoki ish bormi.
    pub real_goods_or_work: bool,
    /// Yangi a'zo jalb qilish talab qilinadimi.
    pub needs_new_members: bool,
    /// Shoshiltirish bormi.
    pub rush_pressure: bool,
    /// Yozma shartnoma bormi.
    pub written_contract: bool,
}

/// Natija.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OfferVerdict {
    /// Yashil: qizil va sariq belgilar yo'q.
    Green,
    /// Sariq: ehtiyotkorlik.
    Yellow,
    /// Qizil: kafolatlangan foyda yoki piramida belgisi.
    Red,
}

/// Bayroq: qaysi belgi topildi va nima uchun muhim.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Flag {
    /// Belgi kodi.
    pub code: &'static str,
    /// Foydalanuvchiga izoh (o'zbekcha).
    pub explanation: &'static str,
    /// Qizilmi (sariq bo'lmasa).
    pub red: bool,
}

/// Baholash: natija va topilgan bayroqlar.
pub fn offer_check(answers: &OfferAnswers) -> (OfferVerdict, Vec<Flag>) {
    let mut flags = Vec::new();
    if answers.guaranteed_profit {
        flags.push(Flag {
            code: "GUARANTEED_PROFIT",
            explanation: "tavakkalsiz kafolatlangan foyda — ribo yoki firibgarlik belgisi",
            red: true,
        });
    }
    if answers.needs_new_members {
        flags.push(Flag {
            code: "NEEDS_NEW_MEMBERS",
            explanation: "yangi a'zo jalb qilish talab qilinadi — piramida belgisi",
            red: true,
        });
    }
    if answers.rush_pressure {
        flags.push(Flag {
            code: "RUSH_PRESSURE",
            explanation: "shoshiltirish bor — qaror uchun vaqt berilmayapti",
            red: false,
        });
    }
    if !answers.written_contract {
        flags.push(Flag {
            code: "NO_WRITTEN_CONTRACT",
            explanation: "yozma shartnoma yo'q",
            red: false,
        });
    }
    if !answers.real_goods_or_work {
        flags.push(Flag {
            code: "NO_REAL_GOODS_OR_WORK",
            explanation: "real mol yoki ish ko'rsatilmagan",
            red: false,
        });
    }
    if !answers.loss_possible {
        flags.push(Flag {
            code: "LOSS_DENIED",
            explanation: "zarar mumkin emasligi aytilmoqda — har qanday biznesda xavf bor",
            red: false,
        });
    }
    // Uch va undan ko'p sariq bayroq ham qizil: ehtiyotkorlik belgilari yig'ilsa, bu endi tasodif emas.
    let verdict = if flags.iter().any(|flag| flag.red) || flags.len() >= YELLOW_FLAGS_FOR_RED {
        OfferVerdict::Red
    } else if flags.is_empty() {
        OfferVerdict::Green
    } else {
        OfferVerdict::Yellow
    };
    (verdict, flags)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn clean() -> OfferAnswers {
        OfferAnswers {
            guaranteed_profit: false,
            loss_possible: true,
            real_goods_or_work: true,
            needs_new_members: false,
            rush_pressure: false,
            written_contract: true,
        }
    }

    #[test]
    fn toza_taklif_yashil() {
        assert_eq!(offer_check(&clean()).0, OfferVerdict::Green);
    }

    #[test]
    fn kafolat_va_piramida_qizil() {
        let guaranteed = OfferAnswers {
            guaranteed_profit: true,
            ..clean()
        };
        assert_eq!(offer_check(&guaranteed).0, OfferVerdict::Red);
        let pyramid = OfferAnswers {
            needs_new_members: true,
            ..clean()
        };
        assert_eq!(offer_check(&pyramid).0, OfferVerdict::Red);
    }

    #[test]
    fn uch_sariq_bayroq_qizil_boladi() {
        let piled = OfferAnswers {
            rush_pressure: true,
            written_contract: false,
            real_goods_or_work: false,
            ..clean()
        };
        let (verdict, flags) = offer_check(&piled);
        assert_eq!(flags.len(), 3);
        assert!(flags.iter().all(|flag| !flag.red));
        assert_eq!(verdict, OfferVerdict::Red);
    }

    #[test]
    fn shoshiltirish_sariq() {
        let rushed = OfferAnswers {
            rush_pressure: true,
            ..clean()
        };
        let (verdict, flags) = offer_check(&rushed);
        assert_eq!(verdict, OfferVerdict::Yellow);
        assert_eq!(flags[0].code, "RUSH_PRESSURE");
    }
}
