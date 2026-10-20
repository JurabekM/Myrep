//! Taklif tekshiruvi: «Kafolatlangan foyda» detektori (SPEC 2E.5) va «Besh xavf belgisi» (SPEC 2G.1, 7-qonun).
//!
//! Kirish — 9 savolga `HA | YO'Q | BILMAYMAN` javoblar. Natija:
//! * **bayroqlar** (2E.5): qizil — kafolat, zarar bo'lishilmaydi, real mol yo'q, yangi a'zo talabi; sariq —
//!   shoshirish, yozma shartnoma yo'q, chiqish qiyin, ruxsat yo'q, o'z ko'zi bilan ko'rmagan, har qanday «bilmayman»;
//! * **besh belgi** (`ScamSign`) va **daraja** (hojining qoidasi): 0 — belgi yo'q, 1 — «hushyor torting» (kamida sariq),
//!   2+ — «qoching» (qizil);
//! * **umumiy baho** = bayroqlar bahosi va daraja bahosining eng og'iri;
//! * **toifalar** (2G.7): `RIBO` — kafolat; `GHARAR` — ko'rinmas ish; `QIMOR` — daromad yangi odamlardan.
//!
//! Qoida mobil bilan umumiy vektor `spec/test-vectors/scam_signals.json` bilan qotirilgan (avvalgi «uch sariq —
//! qizil» qoidasi vektorga zid edi va olib tashlandi — OPEN_QUESTIONS, 7-qonun).

/// Savolga javob.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Answer {
    /// Ha.
    Yes,
    /// Yo'q.
    No,
    /// Bilmayman (javob yo'q) — sariq bayroq.
    Unknown,
}

impl Answer {
    /// JSON kodi.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Yes => "YES",
            Self::No => "NO",
            Self::Unknown => "UNKNOWN",
        }
    }

    /// Koddan javob; noma'lum kod — `Unknown` (saqlangan javoblarni o'qish chidamli).
    pub fn from_code(code: &str) -> Self {
        match code {
            "YES" => Self::Yes,
            "NO" => Self::No,
            _ => Self::Unknown,
        }
    }
}

/// To'qqiz savol (vektordagi kodlar bilan).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Question {
    /// Foyda kafolatlangan deyishadimi.
    Guaranteed,
    /// Zarar ham bo'lishiladimi (tavakkal tan olinadimi).
    LossShared,
    /// Real mol yoki ish bormi.
    RealGoods,
    /// Daromad yangi odam olib kelishdan keladimi.
    Recruitment,
    /// Shoshirishadimi.
    Pressure,
    /// Yozma shartnoma bormi.
    WrittenContract,
    /// Pulni istagan vaqtda qaytarib olsa bo'ladimi.
    ExitEasy,
    /// Odamlardan pul yig'ishga davlat ruxsati bormi.
    License,
    /// Ishni o'z ko'zi bilan ko'rdimi (ko'rsatishdimi).
    VerifiedInPerson,
}

impl Question {
    /// Barcha savollar, ekran tartibida.
    pub const ALL: [Self; 9] = [
        Self::Guaranteed,
        Self::LossShared,
        Self::RealGoods,
        Self::Recruitment,
        Self::Pressure,
        Self::WrittenContract,
        Self::ExitEasy,
        Self::License,
        Self::VerifiedInPerson,
    ];

    /// Vektor va JSON kodi (`camelCase`).
    pub const fn code(self) -> &'static str {
        match self {
            Self::Guaranteed => "guaranteed",
            Self::LossShared => "lossShared",
            Self::RealGoods => "realGoods",
            Self::Recruitment => "recruitment",
            Self::Pressure => "pressure",
            Self::WrittenContract => "writtenContract",
            Self::ExitEasy => "exitEasy",
            Self::License => "license",
            Self::VerifiedInPerson => "verifiedInPerson",
        }
    }

    /// Koddan savol.
    pub fn from_code(code: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|q| q.code() == code)
    }
}

/// Javoblar to'plami.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct OfferAnswers {
    /// Foyda kafolatlangan.
    pub guaranteed: Answer,
    /// Zarar bo'lishiladi.
    pub loss_shared: Answer,
    /// Real mol yoki ish bor.
    pub real_goods: Answer,
    /// Daromad yangi odam olib kelishdan.
    pub recruitment: Answer,
    /// Shoshirish bor.
    pub pressure: Answer,
    /// Yozma shartnoma bor.
    pub written_contract: Answer,
    /// Pulni istagan vaqtda qaytarib olsa bo'ladi.
    pub exit_easy: Answer,
    /// Davlat ruxsati bor.
    pub license: Answer,
    /// O'z ko'zi bilan ko'rdi.
    pub verified_in_person: Answer,
}

impl OfferAnswers {
    /// Hamma savolga «bilmayman».
    pub const UNKNOWN: Self = Self {
        guaranteed: Answer::Unknown,
        loss_shared: Answer::Unknown,
        real_goods: Answer::Unknown,
        recruitment: Answer::Unknown,
        pressure: Answer::Unknown,
        written_contract: Answer::Unknown,
        exit_easy: Answer::Unknown,
        license: Answer::Unknown,
        verified_in_person: Answer::Unknown,
    };

    /// Savol bo'yicha javob.
    pub const fn get(&self, question: Question) -> Answer {
        match question {
            Question::Guaranteed => self.guaranteed,
            Question::LossShared => self.loss_shared,
            Question::RealGoods => self.real_goods,
            Question::Recruitment => self.recruitment,
            Question::Pressure => self.pressure,
            Question::WrittenContract => self.written_contract,
            Question::ExitEasy => self.exit_easy,
            Question::License => self.license,
            Question::VerifiedInPerson => self.verified_in_person,
        }
    }

    /// Savol bo'yicha javobni o'rnatadi.
    pub const fn set(&mut self, question: Question, answer: Answer) {
        match question {
            Question::Guaranteed => self.guaranteed = answer,
            Question::LossShared => self.loss_shared = answer,
            Question::RealGoods => self.real_goods = answer,
            Question::Recruitment => self.recruitment = answer,
            Question::Pressure => self.pressure = answer,
            Question::WrittenContract => self.written_contract = answer,
            Question::ExitEasy => self.exit_easy = answer,
            Question::License => self.license = answer,
            Question::VerifiedInPerson => self.verified_in_person = answer,
        }
    }
}

/// Besh xavf belgisi (SPEC 2G.1), tartib qat'iy.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScamSign {
    /// Katta foyda kafolatlab va'da qilinadi.
    GuaranteedHighReturn,
    /// «Faqat bugun, joy kam, tezroq».
    Urgency,
    /// Daromad moldan emas, yangi odam olib kelishdan.
    RecruitmentIncome,
    /// Ishning o'zi ko'rinmaydi: mol, ruxsat yo'q yoki ko'rsatishmadi.
    NoRealBusiness,
    /// Kirish oson, chiqish qiyin.
    HardExit,
}

impl ScamSign {
    /// Tartib (vektordagi).
    pub const ALL: [Self; 5] = [
        Self::GuaranteedHighReturn,
        Self::Urgency,
        Self::RecruitmentIncome,
        Self::NoRealBusiness,
        Self::HardExit,
    ];

    /// Barqaror kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::GuaranteedHighReturn => "GUARANTEED_HIGH_RETURN",
            Self::Urgency => "URGENCY",
            Self::RecruitmentIncome => "RECRUITMENT_INCOME",
            Self::NoRealBusiness => "NO_REAL_BUSINESS",
            Self::HardExit => "HARD_EXIT",
        }
    }

    /// Koddan belgi.
    pub fn from_code(code: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|s| s.code() == code)
    }

    /// Izoh — Sobir hoji ohangida, ayblamasdan.
    pub const fn explanation(self) -> &'static str {
        match self {
            Self::GuaranteedHighReturn => {
                "Katta foyda kafolatlab va'da qilinmoqda. Halol foydaning kafolati bo'lmaydi — u yerda tavakkal bor."
            }
            Self::Urgency => {
                "«Faqat bugun», «joy kam», «tezroq» — shoshirishmoqda. O'ylab olishingizdan qo'rqishadi."
            }
            Self::RecruitmentIncome => {
                "Daromad moldan emas, yangi odam olib kelishdan. Siz xaridor emas, molsiz."
            }
            Self::NoRealBusiness => {
                "Ishning o'zi ko'rinmaydi: ombor, mol, hujjat yoki ruxsat yo'q, yoki ko'rsatishmadi. Ekran mol emas."
            }
            Self::HardExit => {
                "Kirish oson, chiqish qiyin: pulni qaytarib so'rasangiz «keyinroq» deyishadi."
            }
        }
    }
}

/// Daraja: hojining qoidasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScamLevel {
    /// Belgi yo'q.
    None,
    /// Bitta belgi — hushyor torting.
    Caution,
    /// Ikki va undan ko'p — qoching.
    Flee,
}

impl ScamLevel {
    /// Barqaror kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::None => "NONE",
            Self::Caution => "CAUTION",
            Self::Flee => "FLEE",
        }
    }
}

/// Umumiy baho.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum OfferVerdict {
    /// Yashil: belgilar yo'q.
    Green,
    /// Sariq: ehtiyotkorlik.
    Yellow,
    /// Qizil: chetlaning.
    Red,
}

impl OfferVerdict {
    /// Barqaror kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Green => "GREEN",
            Self::Yellow => "YELLOW",
            Self::Red => "RED",
        }
    }

    /// Koddan baho.
    pub fn from_code(code: &str) -> Option<Self> {
        match code {
            "GREEN" => Some(Self::Green),
            "YELLOW" => Some(Self::Yellow),
            "RED" => Some(Self::Red),
            _ => None,
        }
    }
}

/// Taklif toifasi (SPEC 2G.7).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OfferCategory {
    /// Zarar bo'lishilmaydigan kafolatli foyda.
    Ribo,
    /// Noaniq bitim: nima sotilayotgani, pul qayerda ishlayotgani noma'lum.
    Gharar,
    /// Yutuq faqat boshqaning yutqazishidan.
    Qimor,
}

impl OfferCategory {
    /// Barqaror kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Ribo => "RIBO",
            Self::Gharar => "GHARAR",
            Self::Qimor => "QIMOR",
        }
    }

    /// Koddan toifa.
    pub fn from_code(code: &str) -> Option<Self> {
        match code {
            "RIBO" => Some(Self::Ribo),
            "GHARAR" => Some(Self::Gharar),
            "QIMOR" => Some(Self::Qimor),
            _ => None,
        }
    }
}

/// Bayroq (2E.5): qaysi savol, nima uchun muhim.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Flag {
    /// Belgi kodi.
    pub code: &'static str,
    /// Qaysi savoldan.
    pub question: Question,
    /// Izoh (o'zbekcha).
    pub explanation: &'static str,
    /// Qizilmi (sariq bo'lmasa).
    pub red: bool,
}

/// To'liq natija.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OfferReport {
    /// Besh belgidan topilganlari (tartib bilan).
    pub signs: Vec<ScamSign>,
    /// Daraja.
    pub level: ScamLevel,
    /// Umumiy baho.
    pub verdict: OfferVerdict,
    /// Toifalar.
    pub categories: Vec<OfferCategory>,
    /// 2E.5 bayroqlari.
    pub flags: Vec<Flag>,
}

const fn unknown_flag(question: Question) -> Flag {
    Flag {
        code: "UNKNOWN",
        question,
        explanation: "Bu savolga javob yo'q — bilmaslik ham xavf: so'rang, ko'ring, keyin qaror qiling.",
        red: false,
    }
}

/// Bayroqlar (2E.5 + 2G.1 savollari).
fn flags_of(a: &OfferAnswers) -> Vec<Flag> {
    let mut flags = Vec::new();
    let mut push = |cond: bool, code, question, explanation, red| {
        if cond {
            flags.push(Flag {
                code,
                question,
                explanation,
                red,
            });
        }
    };
    push(
        a.guaranteed == Answer::Yes,
        "GUARANTEED_PROFIT",
        Question::Guaranteed,
        "tavakkalsiz kafolatlangan foyda — ribo yoki firibgarlik belgisi",
        true,
    );
    push(
        a.loss_shared == Answer::No,
        "LOSS_NOT_SHARED",
        Question::LossShared,
        "zarar bo'lishilmaydi deyilmoqda — har qanday halol ishda tavakkal bor",
        true,
    );
    push(
        a.real_goods == Answer::No,
        "NO_REAL_GOODS_OR_WORK",
        Question::RealGoods,
        "real mol yoki ish ko'rsatilmagan",
        true,
    );
    push(
        a.recruitment == Answer::Yes,
        "NEEDS_NEW_MEMBERS",
        Question::Recruitment,
        "yangi a'zo jalb qilish talab qilinadi — piramida belgisi",
        true,
    );
    push(
        a.pressure == Answer::Yes,
        "RUSH_PRESSURE",
        Question::Pressure,
        "shoshiltirish bor — qaror uchun vaqt berilmayapti",
        false,
    );
    push(
        a.written_contract == Answer::No,
        "NO_WRITTEN_CONTRACT",
        Question::WrittenContract,
        "yozma shartnoma yo'q",
        false,
    );
    push(
        a.exit_easy == Answer::No,
        "HARD_EXIT",
        Question::ExitEasy,
        "pulni qaytarib olish qiyin — «keyinroq» deyishadi",
        false,
    );
    push(
        a.license == Answer::No,
        "NO_LICENSE",
        Question::License,
        "odamlardan pul yig'ishga davlat ruxsati yo'q",
        false,
    );
    push(
        a.verified_in_person == Answer::No,
        "NOT_VERIFIED",
        Question::VerifiedInPerson,
        "ishni o'z ko'zingiz bilan ko'rmadingiz yoki ko'rsatishmadi",
        false,
    );
    for question in Question::ALL {
        if a.get(question) == Answer::Unknown {
            flags.push(unknown_flag(question));
        }
    }
    flags
}

/// Besh belgi (tartib qat'iy).
fn signs_of(a: &OfferAnswers) -> Vec<ScamSign> {
    let mut signs = Vec::new();
    if a.guaranteed == Answer::Yes {
        signs.push(ScamSign::GuaranteedHighReturn);
    }
    if a.pressure == Answer::Yes {
        signs.push(ScamSign::Urgency);
    }
    if a.recruitment == Answer::Yes {
        signs.push(ScamSign::RecruitmentIncome);
    }
    if a.real_goods == Answer::No || a.license == Answer::No || a.verified_in_person == Answer::No {
        signs.push(ScamSign::NoRealBusiness);
    }
    if a.exit_easy == Answer::No {
        signs.push(ScamSign::HardExit);
    }
    signs
}

/// Taklifni baholaydi.
pub fn offer_check(answers: &OfferAnswers) -> OfferReport {
    let flags = flags_of(answers);
    let signs = signs_of(answers);
    let level = match signs.len() {
        0 => ScamLevel::None,
        1 => ScamLevel::Caution,
        _ => ScamLevel::Flee,
    };
    let by_flags = if flags.iter().any(|f| f.red) {
        OfferVerdict::Red
    } else if flags.is_empty() {
        OfferVerdict::Green
    } else {
        OfferVerdict::Yellow
    };
    let by_level = match level {
        ScamLevel::None => OfferVerdict::Green,
        ScamLevel::Caution => OfferVerdict::Yellow,
        ScamLevel::Flee => OfferVerdict::Red,
    };
    let verdict = by_flags.max(by_level);
    let mut categories = Vec::new();
    if signs.contains(&ScamSign::GuaranteedHighReturn) {
        categories.push(OfferCategory::Ribo);
    }
    if signs.contains(&ScamSign::NoRealBusiness) {
        categories.push(OfferCategory::Gharar);
    }
    if signs.contains(&ScamSign::RecruitmentIncome) {
        categories.push(OfferCategory::Qimor);
    }
    OfferReport {
        signs,
        level,
        verdict,
        categories,
        flags,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn clean() -> OfferAnswers {
        OfferAnswers {
            guaranteed: Answer::No,
            loss_shared: Answer::Yes,
            real_goods: Answer::Yes,
            recruitment: Answer::No,
            pressure: Answer::No,
            written_contract: Answer::Yes,
            exit_easy: Answer::Yes,
            license: Answer::Yes,
            verified_in_person: Answer::Yes,
        }
    }

    #[test]
    fn toza_taklif_yashil() {
        let report = offer_check(&clean());
        assert_eq!(report.verdict, OfferVerdict::Green);
        assert_eq!(report.level, ScamLevel::None);
        assert!(report.signs.is_empty() && report.flags.is_empty());
    }

    #[test]
    fn bitta_belgi_hushyor_ikkitasi_qoch() {
        let mut one = clean();
        one.pressure = Answer::Yes;
        let report = offer_check(&one);
        assert_eq!(report.level, ScamLevel::Caution);
        assert_eq!(report.verdict, OfferVerdict::Yellow);
        let mut two = one;
        two.exit_easy = Answer::No;
        let report = offer_check(&two);
        assert_eq!(report.signs, vec![ScamSign::Urgency, ScamSign::HardExit]);
        assert_eq!(report.level, ScamLevel::Flee);
        assert_eq!(report.verdict, OfferVerdict::Red);
    }

    #[test]
    fn kafolat_bitta_ozi_qizil_va_ribo() {
        let mut a = clean();
        a.guaranteed = Answer::Yes;
        let report = offer_check(&a);
        assert_eq!(report.level, ScamLevel::Caution);
        assert_eq!(
            report.verdict,
            OfferVerdict::Red,
            "2E.5 qizil bayrog'i og'irroq"
        );
        assert_eq!(report.categories, vec![OfferCategory::Ribo]);
    }

    #[test]
    fn hamma_bilmayman_sariq_belgisiz() {
        let report = offer_check(&OfferAnswers::UNKNOWN);
        assert!(report.signs.is_empty());
        assert_eq!(report.verdict, OfferVerdict::Yellow);
        assert_eq!(report.flags.len(), 9);
        assert!(report.flags.iter().all(|f| f.code == "UNKNOWN"));
    }

    #[test]
    fn plyus_taklifi_tort_belgi_uch_toifa() {
        let a = OfferAnswers {
            guaranteed: Answer::Yes,
            loss_shared: Answer::No,
            real_goods: Answer::Unknown,
            recruitment: Answer::Yes,
            pressure: Answer::Yes,
            written_contract: Answer::Yes,
            exit_easy: Answer::Unknown,
            license: Answer::Unknown,
            verified_in_person: Answer::No,
        };
        let report = offer_check(&a);
        assert_eq!(report.signs.len(), 4);
        assert_eq!(
            report.categories,
            vec![
                OfferCategory::Ribo,
                OfferCategory::Gharar,
                OfferCategory::Qimor
            ]
        );
        assert_eq!(report.verdict, OfferVerdict::Red);
    }

    #[test]
    fn kodlar_qaytariladi() {
        for q in Question::ALL {
            assert_eq!(Question::from_code(q.code()), Some(q));
        }
        for s in ScamSign::ALL {
            assert_eq!(ScamSign::from_code(s.code()), Some(s));
        }
        assert_eq!(Answer::from_code("nimadir"), Answer::Unknown);
    }
}
