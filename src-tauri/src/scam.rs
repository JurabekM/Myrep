//! 7-qonun xizmati (SPEC 2G, D16): taklif tekshiruvi «besh xavf belgisi» bilan (saqlanadi), «to'xta, maslahatlash»
//! qarori (maslahatchi + 24 soat), va'da qilingan foyda yillikka, piramida modeli, «qal'a devori» taqsimoti,
//! hunar shablonlari. Hisoblar `domain::offer_check` va `domain::scam_math` da; bu yerda faqat yig'iladi.

use std::collections::BTreeMap;

use domain::DomainError;
use domain::content::TaskTrigger;
use domain::offer_check::{Answer, OfferAnswers, Question, offer_check};
use domain::scam_math::{lump_sum_split, promised_return, pyramid_levels};
use money::{Currency, Money};
use money::{FxRate, convert};
use storage::{Database, OfferCheckRepo, OfferCheckRow, StorageError};
use time::{Duration, OffsetDateTime};

use crate::content::record_event;
use crate::dto::{
    DecideOfferInputDto, HustleTemplateDto, LumpSumInputDto, LumpSumPlanDto, MoneyDto,
    OfferCheckDto, OfferFlagDto, OfferInputDto, OfferSignDto, OffersDto, PromisedReturnDto,
    PyramidDto,
};
use crate::finance::{self, CURRENCY, DEVICE_ID, UuidV7, date_text, parse_money};
use crate::reserve;
use crate::session::SessionError;

/// Qaror kodlari.
const DECISIONS: [&str; 3] = ["DECLINED", "POSTPONED", "ACCEPTED"];
/// «Bir kecha uxlab ko'ring»: tekshiruvdan qarorgacha kutish.
pub const COOLING_HOURS: i64 = 24;
/// Yillik ko'paytma uchun oylar.
const YEAR_MONTHS: u32 = 12;

/// Javoblar xaritasi (`savol kodi → javob kodi`) dan domen javoblari. Noma'lum kod — `UNKNOWN` (chidamli).
fn answers_of(map: &BTreeMap<String, String>) -> OfferAnswers {
    let mut answers = OfferAnswers::UNKNOWN;
    for question in Question::ALL {
        if let Some(code) = map.get(question.code()) {
            answers.set(question, Answer::from_code(code));
        }
    }
    answers
}

fn answers_map(answers: &OfferAnswers) -> BTreeMap<String, String> {
    Question::ALL
        .into_iter()
        .map(|q| (q.code().to_owned(), answers.get(q).code().to_owned()))
        .collect()
}

fn promised_dto(monthly_bp: u32) -> Result<PromisedReturnDto, SessionError> {
    let result = promised_return(monthly_bp, YEAR_MONTHS)?;
    Ok(PromisedReturnDto {
        monthly_bp,
        months: YEAR_MONTHS,
        simple_multiple_bp: result.simple_multiple_bp,
        compound_multiple_bp: result.compound_multiple_bp,
    })
}

/// Qachon «pul qo'yaman» ochiladi (tekshiruv + 24 soat).
fn accept_after(checked_at: OffsetDateTime) -> OffsetDateTime {
    checked_at + Duration::hours(COOLING_HOURS)
}

fn dto_of(row: &OfferCheckRow, now: OffsetDateTime) -> Result<OfferCheckDto, SessionError> {
    let map: BTreeMap<String, String> = serde_json::from_str(&row.answers_json)
        .map_err(|_| StorageError::InvalidData("taklif javoblari".to_owned()))?;
    let answers = answers_of(&map);
    let report = offer_check(&answers);
    let promised = row.promised_monthly_bp.map(promised_dto).transpose()?;
    let after = accept_after(row.checked_at);
    let advisor_named = row.advisor.as_deref().is_some_and(|a| !a.trim().is_empty());
    Ok(OfferCheckDto {
        id: row.id.clone(),
        title: row.title.clone(),
        answers: answers_map(&answers),
        verdict: report.verdict.code().to_owned(),
        level: report.level.code().to_owned(),
        signs: report
            .signs
            .iter()
            .map(|s| OfferSignDto {
                code: s.code().to_owned(),
                explanation: s.explanation().to_owned(),
            })
            .collect(),
        categories: report
            .categories
            .iter()
            .map(|c| c.code().to_owned())
            .collect(),
        flags: report
            .flags
            .iter()
            .map(|f| OfferFlagDto {
                code: f.code.to_owned(),
                question: f.question.code().to_owned(),
                explanation: f.explanation.to_owned(),
                red: f.red,
            })
            .collect(),
        amount: row.amount.map(MoneyDto::of),
        promised,
        advisor: row.advisor.clone(),
        decision: row.decision.clone(),
        checked_on: date_text(row.checked_at.date()),
        decided_on: row.decided_at.map(|t| date_text(t.date())),
        cooling_hours_left: u32::try_from((after - now).whole_hours().max(0)).unwrap_or(u32::MAX),
        can_accept: row.decision.is_none() && advisor_named && now >= after,
    })
}

/// Taklifni tekshiradi va yozadi; `OFFER_CHECKED` hodisasi (7-bob vazifasi).
pub fn check_offer(
    db: &Database,
    now: OffsetDateTime,
    input: OfferInputDto,
) -> Result<OfferCheckDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let answers = answers_of(&input.answers);
    let report = offer_check(&answers);
    let amount = match input.amount.as_deref().filter(|t| !t.trim().is_empty()) {
        Some(text) => {
            let amount = parse_money(text)?;
            if amount.minor() <= 0 {
                return Err(DomainError::AmountNotPositive.into());
            }
            Some(amount)
        }
        None => None,
    };
    if let Some(bp) = input.promised_monthly_bp {
        // Chegaralarni oldindan tekshiramiz (xato saqlashdan oldin chiqsin).
        promised_return(bp, YEAR_MONTHS)?;
    }
    let title = match input.title.as_deref().filter(|t| !t.trim().is_empty()) {
        Some(t) => Some(domain::validate_name(t)?),
        None => None,
    };
    let advisor = input
        .advisor
        .as_deref()
        .map(str::trim)
        .filter(|a| !a.is_empty())
        .map(ToOwned::to_owned);
    let row = OfferCheckRow {
        id: domain::IdGen::next_id(&UuidV7),
        household_id: ctx.household.id.clone(),
        title,
        answers_json: serde_json::to_string(&answers_map(&answers))
            .map_err(|_| StorageError::InvalidData("taklif javoblari".to_owned()))?,
        verdict: report.verdict.code().to_owned(),
        level: report.level.code().to_owned(),
        signs_json: serde_json::to_string(
            &report.signs.iter().map(|s| s.code()).collect::<Vec<_>>(),
        )
        .map_err(|_| StorageError::InvalidData("belgilar".to_owned()))?,
        categories_json: serde_json::to_string(
            &report
                .categories
                .iter()
                .map(|c| c.code())
                .collect::<Vec<_>>(),
        )
        .map_err(|_| StorageError::InvalidData("toifalar".to_owned()))?,
        amount,
        promised_monthly_bp: input.promised_monthly_bp,
        advisor,
        decision: None,
        checked_at: now,
        decided_at: None,
        origin_device_id: DEVICE_ID.to_owned(),
    };
    OfferCheckRepo::new(db.connection()).insert(&row)?;
    record_event(db, now, TaskTrigger::OfferChecked)?;
    dto_of(&row, now)
}

/// Tekshiruvlar tarixi (eng yangisi avval).
pub fn list_offers(db: &Database, now: OffsetDateTime) -> Result<OffersDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let rows = OfferCheckRepo::new(db.connection()).list(&ctx.household.id)?;
    let mut items = Vec::with_capacity(rows.len());
    for row in &rows {
        items.push(dto_of(row, now)?);
    }
    Ok(OffersDto { items })
}

/// «To'xta, maslahatlash»: `ACCEPTED` faqat maslahatchi yozilgan va tekshiruvdan 24 soat o'tgan bo'lsa;
/// `DECLINED` va `POSTPONED` darhol. Qaror bir marta.
pub fn decide_offer(
    db: &Database,
    now: OffsetDateTime,
    input: DecideOfferInputDto,
) -> Result<OffersDto, SessionError> {
    let repo = OfferCheckRepo::new(db.connection());
    let row = repo.find(&input.id)?.ok_or(StorageError::NotFound)?;
    if row.decision.is_some() {
        return Err(DomainError::OfferAlreadyDecided.into());
    }
    if !DECISIONS.contains(&input.decision.as_str()) {
        return Err(DomainError::InvalidRule.into());
    }
    let advisor = input
        .advisor
        .as_deref()
        .map(str::trim)
        .filter(|a| !a.is_empty())
        .map(ToOwned::to_owned)
        .or_else(|| row.advisor.clone());
    if input.decision == "ACCEPTED" {
        if advisor.is_none() {
            return Err(DomainError::AdvisorRequired.into());
        }
        if now < accept_after(row.checked_at) {
            return Err(DomainError::CoolingPeriod.into());
        }
    }
    repo.set_decision(&row.id, &input.decision, advisor.as_deref(), now)?;
    list_offers(db, now)
}

/// Oylik va'da → yillik ko'paytma (faqat ogohlantirish).
pub fn promised(monthly_bp: u32) -> Result<PromisedReturnDto, SessionError> {
    promised_dto(monthly_bp)
}

/// Piramida modeli (ta'limiy, saqlanmaydi).
pub fn pyramid(recruits_per_person: u32, population: u32) -> Result<PyramidDto, SessionError> {
    let model = pyramid_levels(u64::from(recruits_per_person), u64::from(population))?;
    let narrow = |v: u64| u32::try_from(v).map_err(|_| DomainError::InvalidRule);
    Ok(PyramidDto {
        recruits_per_person,
        population,
        levels: model.levels,
        participants: narrow(model.participants)?,
        last_level: narrow(model.last_level)?,
        last_level_share_bp: model.last_level_share_bp,
        last_level_full: model.last_level_full,
    })
}

/// «Qal'a devori»: katta summa (chet el valyutasida bo'lsa — kurs bilan) avval 6 oylik zaxira kamomadiga,
/// qolgani sarmoyaga. Zaxira maqsadi xarajat tarixidan; tarix bo'lmasa — foydalanuvchining taxminiy oylik
/// zarur xarajati (`reserve_estimate`) × 6. `EMERGENCY_TARGET_SET` hodisasi (7-bob vazifasi).
pub fn plan_lump_sum(
    db: &Database,
    now: OffsetDateTime,
    input: LumpSumInputDto,
) -> Result<LumpSumPlanDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let currency = Currency::from_iso(&input.currency).map_err(DomainError::from)?;
    let entered = parse_money(&input.amount)?;
    let amount_entered = Money::new(entered.minor(), currency);
    if amount_entered.minor() <= 0 {
        return Err(DomainError::AmountNotPositive.into());
    }
    let (amount, rate_used) = if currency == CURRENCY {
        (amount_entered, None)
    } else {
        let rate_text = input
            .rate
            .as_deref()
            .filter(|t| !t.trim().is_empty())
            .ok_or(DomainError::InvalidRule)?;
        let rate_money = parse_money(rate_text)?;
        let rate = FxRate::new(
            currency,
            CURRENCY,
            rate_money.minor(),
            CURRENCY.minor_per_major(),
            ctx.today,
            "manual",
        )
        .map_err(DomainError::from)?;
        (
            convert(amount_entered, &rate).map_err(DomainError::from)?,
            Some(MoneyDto::of(rate_money)),
        )
    };
    let reserve_view = reserve::reserve(db, now)?;
    let (target, target_source) = match reserve_view.target_full {
        Some(target) => (
            Money::new(
                target
                    .minor
                    .parse::<i64>()
                    .map_err(|_| StorageError::InvalidData("maqsad".to_owned()))?,
                CURRENCY,
            ),
            "HISTORY",
        ),
        None => {
            let estimate_text = input
                .reserve_estimate
                .as_deref()
                .filter(|t| !t.trim().is_empty())
                .ok_or(DomainError::ReserveEstimateRequired)?;
            let monthly = parse_money(estimate_text)?;
            if monthly.minor() <= 0 {
                return Err(DomainError::AmountNotPositive.into());
            }
            let total = monthly
                .minor()
                .checked_mul(i64::from(reserve_view.target_months))
                .ok_or(DomainError::InvalidRule)?;
            (Money::new(total, CURRENCY), "ESTIMATE")
        }
    };
    let balance = Money::new(
        reserve_view
            .balance
            .minor
            .parse::<i64>()
            .map_err(|_| StorageError::InvalidData("balans".to_owned()))?,
        CURRENCY,
    );
    let missing = Money::new((target.minor() - balance.minor()).max(0), CURRENCY);
    let split = lump_sum_split(amount, missing)?;
    record_event(db, now, TaskTrigger::EmergencyTargetSet)?;
    Ok(LumpSumPlanDto {
        amount_entered: MoneyDto::of(amount_entered),
        rate_used,
        amount: MoneyDto::of(amount),
        reserve_target: MoneyDto::of(target),
        reserve_target_source: target_source.to_owned(),
        reserve_balance: MoneyDto::of(balance),
        reserve_missing: MoneyDto::of(missing),
        to_reserve: MoneyDto::of(split.to_reserve),
        to_invest: MoneyDto::of(split.to_invest),
        reserve_filled: missing.minor() == 0 || split.to_reserve.minor() == missing.minor(),
    })
}

/// Hunar shablonlari (SPEC 2G.8): CAPEX nomlari oldindan, summalarni foydalanuvchi yozadi (narx o'ylab topilmaydi).
pub fn hustle_templates() -> Vec<HustleTemplateDto> {
    vec![
        HustleTemplateDto {
            id: "FORGE_WELD".to_owned(),
            name: "Temirchilik / payvand ustaxonasi".to_owned(),
            story: "Rustam: to'rt yil payvandchi va usta boshi bo'lgan — pul hunariga ishlasin: darvoza, panjara, mangal."
                .to_owned(),
            capex_lines: vec![
                "Payvand apparati va niqob".to_owned(),
                "Bolgarka, drel, kesish disklari".to_owned(),
                "Ish stoli, tiski, shablonlar".to_owned(),
                "Ustaxona ijarasi (birinchi oylar)".to_owned(),
                "Boshlang'ich metall (profil, list, armatura)".to_owned(),
                "Bo'yoq va gruntovka".to_owned(),
            ],
            demand_question:
                "Talab bormi? Kim buyurtma beradi — qo'shnilar, quruvchilar, mahalla? Atrofda qancha uy qurilmoqda yoki yangilanmoqda?"
                    .to_owned(),
        },
        HustleTemplateDto {
            id: "SEWING".to_owned(),
            name: "Tikuvchilik ustaxonasi".to_owned(),
            story: "Uy sharoitida boshlanadigan hunar: buyurtma, ta'mir, maktab formasi.".to_owned(),
            capex_lines: vec![
                "Tikuv mashinasi va overlok".to_owned(),
                "Bichish stoli, qaychi, o'lchov asboblari".to_owned(),
                "Boshlang'ich mato va furnitura".to_owned(),
                "Dazmol va dazmol taxtasi".to_owned(),
            ],
            demand_question:
                "Talab bormi? Mahallada tikuvchi bormi, maktab va to'y buyurtmalari qancha?".to_owned(),
        },
        HustleTemplateDto {
            id: "REPAIR".to_owned(),
            name: "Maishiy texnika ta'miri".to_owned(),
            story: "Qo'lida hunari bor ustaga kichik ustaxona va asbob yetadi.".to_owned(),
            capex_lines: vec![
                "Asboblar to'plami va o'lchov qurilmalari".to_owned(),
                "Ehtiyot qismlar zaxirasi".to_owned(),
                "Ish joyi ijarasi yoki uyda burchak".to_owned(),
                "E'lon va vizitka".to_owned(),
            ],
            demand_question:
                "Talab bormi? Eng yaqin ustaxona qayerda, odamlar texnikani qayerga olib boradi?".to_owned(),
        },
    ]
}

#[cfg(test)]
mod tests {
    use super::*;
    use security::SecretKey;
    use time::macros::datetime;

    const NOW: OffsetDateTime = datetime!(2026-10-20 06:00 UTC);

    fn database() -> Database {
        Database::open_in_memory(&SecretKey::from_array([77; 32])).expect("xotirada baza")
    }

    fn answers(pairs: &[(&str, &str)]) -> BTreeMap<String, String> {
        pairs
            .iter()
            .map(|(q, a)| ((*q).to_owned(), (*a).to_owned()))
            .collect()
    }

    fn plyus() -> BTreeMap<String, String> {
        answers(&[
            ("guaranteed", "YES"),
            ("lossShared", "NO"),
            ("realGoods", "UNKNOWN"),
            ("recruitment", "YES"),
            ("pressure", "YES"),
            ("writtenContract", "YES"),
            ("exitEasy", "UNKNOWN"),
            ("license", "UNKNOWN"),
            ("verifiedInPerson", "NO"),
        ])
    }

    #[test]
    fn plyus_taklifi_qizil_saqlanadi_va_tarixda_korinadi() {
        let db = database();
        let dto = check_offer(
            &db,
            NOW,
            OfferInputDto {
                title: Some("«Plyus» — Baxtiyor".into()),
                answers: plyus(),
                amount: Some("10 000".into()),
                promised_monthly_bp: Some(3_500),
                advisor: None,
            },
        )
        .expect("tekshiruv");
        assert_eq!(dto.verdict, "RED");
        assert_eq!(dto.level, "FLEE");
        assert_eq!(dto.signs.len(), 4);
        assert_eq!(dto.categories, vec!["RIBO", "GHARAR", "QIMOR"]);
        let promised = dto.promised.expect("va'da");
        assert_eq!(promised.simple_multiple_bp, 52_000);
        assert_eq!(promised.compound_multiple_bp, 366_439);
        assert!(!dto.can_accept);
        assert_eq!(dto.cooling_hours_left, 24);
        let list = list_offers(&db, NOW).expect("tarix");
        assert_eq!(list.items.len(), 1);
        assert_eq!(list.items[0].answers["guaranteed"], "YES");
        assert_eq!(
            list.items[0].amount.as_ref().map(|m| m.minor.as_str()),
            Some("1000000")
        );
    }

    #[test]
    fn toxta_maslahatlash_qoidasi() {
        let db = database();
        let dto = check_offer(
            &db,
            NOW,
            OfferInputDto {
                title: None,
                answers: answers(&[
                    ("guaranteed", "NO"),
                    ("lossShared", "YES"),
                    ("realGoods", "YES"),
                ]),
                amount: None,
                promised_monthly_bp: None,
                advisor: None,
            },
        )
        .expect("tekshiruv");
        // Maslahatchisiz «pul qo'yaman» — rad.
        let err = decide_offer(
            &db,
            NOW + Duration::hours(30),
            DecideOfferInputDto {
                id: dto.id.clone(),
                decision: "ACCEPTED".into(),
                advisor: None,
            },
        );
        assert!(matches!(
            err,
            Err(SessionError::Domain(DomainError::AdvisorRequired))
        ));
        // Maslahatchi bor, lekin 24 soat o'tmagan — rad.
        let err = decide_offer(
            &db,
            NOW + Duration::hours(5),
            DecideOfferInputDto {
                id: dto.id.clone(),
                decision: "ACCEPTED".into(),
                advisor: Some("Sobir hoji".into()),
            },
        );
        assert!(matches!(
            err,
            Err(SessionError::Domain(DomainError::CoolingPeriod))
        ));
        // 24 soatdan keyin maslahatchi bilan — qabul.
        let list = decide_offer(
            &db,
            NOW + Duration::hours(25),
            DecideOfferInputDto {
                id: dto.id.clone(),
                decision: "ACCEPTED".into(),
                advisor: Some("Sobir hoji".into()),
            },
        )
        .expect("qaror");
        assert_eq!(list.items[0].decision.as_deref(), Some("ACCEPTED"));
        assert_eq!(list.items[0].advisor.as_deref(), Some("Sobir hoji"));
        // Qaror bir marta.
        assert!(matches!(
            decide_offer(
                &db,
                NOW + Duration::hours(26),
                DecideOfferInputDto {
                    id: dto.id,
                    decision: "DECLINED".into(),
                    advisor: None,
                },
            ),
            Err(SessionError::Domain(DomainError::OfferAlreadyDecided))
        ));
        // Rad etish darhol mumkin.
        let other = check_offer(
            &db,
            NOW,
            OfferInputDto {
                title: None,
                answers: plyus(),
                amount: None,
                promised_monthly_bp: None,
                advisor: None,
            },
        )
        .expect("tekshiruv");
        let list = decide_offer(
            &db,
            NOW,
            DecideOfferInputDto {
                id: other.id,
                decision: "DECLINED".into(),
                advisor: None,
            },
        )
        .expect("rad");
        assert_eq!(list.items[0].decision.as_deref(), Some("DECLINED"));
    }

    #[test]
    fn qala_devori_dollar_kurs_bilan_avval_zaxiraga() {
        let db = database();
        // Xarajat tarixi yo'q: taxminiy oylik zarur xarajat 3 000 000 → maqsad 18 000 000.
        let err = plan_lump_sum(
            &db,
            NOW,
            LumpSumInputDto {
                amount: "18 000".into(),
                currency: "USD".into(),
                rate: Some("12 500".into()),
                reserve_estimate: None,
            },
        );
        assert!(matches!(
            err,
            Err(SessionError::Domain(DomainError::ReserveEstimateRequired))
        ));
        let plan = plan_lump_sum(
            &db,
            NOW,
            LumpSumInputDto {
                amount: "18 000".into(),
                currency: "USD".into(),
                rate: Some("12 500".into()),
                reserve_estimate: Some("3 000 000".into()),
            },
        )
        .expect("taqsimot");
        assert_eq!(plan.amount.minor, "22500000000");
        assert_eq!(plan.reserve_target.minor, "1800000000");
        assert_eq!(plan.reserve_target_source, "ESTIMATE");
        assert_eq!(plan.to_reserve.minor, "1800000000");
        assert_eq!(plan.to_invest.minor, "20700000000");
        assert!(plan.reserve_filled);
        // Kichik summa: hammasi zaxiraga, sarmoya 0.
        let plan = plan_lump_sum(
            &db,
            NOW,
            LumpSumInputDto {
                amount: "5 000 000".into(),
                currency: "UZS".into(),
                rate: None,
                reserve_estimate: Some("3 000 000".into()),
            },
        )
        .expect("taqsimot");
        assert_eq!(plan.to_invest.minor, "0");
        assert!(!plan.reserve_filled);
        // Dollar kurssiz — rad.
        assert!(
            plan_lump_sum(
                &db,
                NOW,
                LumpSumInputDto {
                    amount: "100".into(),
                    currency: "USD".into(),
                    rate: None,
                    reserve_estimate: Some("1".into()),
                },
            )
            .is_err()
        );
    }

    #[test]
    fn piramida_va_shablonlar() {
        let model = pyramid(5, 1_000_000).expect("model");
        assert_eq!(model.levels, 10);
        assert_eq!(model.last_level_share_bp, 5_117);
        assert!(pyramid(1, 10).is_err());
        let templates = hustle_templates();
        assert_eq!(templates[0].id, "FORGE_WELD");
        assert!(templates.iter().all(|t| !t.capex_lines.is_empty()));
    }
}
