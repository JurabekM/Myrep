#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! Musofir sovutish detektoridagi U12 savollari jadvali va «besh xavf belgisi» `domain-uy::venture::offer_check` bilan bir xil
//! (domen qatlamlari bir-biriga bog'lanmaydi — jadval nusxa, bu test ularni bog'lab turadi).

use baraka_domain_musofir::cooling::{cooling_check, CoolingExtra, DecisionKind, Reply as MfReply};
use baraka_domain_uy::venture::{offer_check, OfferAnswers, Reply};
use baraka_money::{Currency, Money};
use chrono::NaiveDate;

#[test]
fn offer_questions_match_u12_for_all_answers() {
    let replies = [Reply::Yes, Reply::No, Reply::Unknown];
    let mf = |r: Reply| match r {
        Reply::Yes => MfReply::Yes,
        Reply::No => MfReply::No,
        Reply::Unknown => MfReply::Unknown,
    };
    let today = NaiveDate::from_ymd_opt(2026, 10, 19).unwrap();
    for n in 0..19_683_usize {
        let pick = |i: u32| replies[(n / 3_usize.pow(i)) % 3];
        let a = OfferAnswers {
            guaranteed: pick(0),
            loss_shared: pick(1),
            real_activity: pick(2),
            recruitment: pick(3),
            urgency: pick(4),
            written: pick(5),
            licensed: pick(6),
            inspection: pick(7),
            exit_easy: pick(8),
        };
        let u12: Vec<(&str, &str)> = offer_check(&a)
            .flags
            .iter()
            .map(|f| (f.code, f.level.as_str()))
            .collect();
        let answers = [
            ("guaranteed", mf(a.guaranteed)),
            ("lossShared", mf(a.loss_shared)),
            ("realActivity", mf(a.real_activity)),
            ("recruitment", mf(a.recruitment)),
            ("urgency", mf(a.urgency)),
            ("written", mf(a.written)),
            ("licensed", mf(a.licensed)),
            ("inspection", mf(a.inspection)),
            ("exitEasy", mf(a.exit_easy)),
            ("approached", MfReply::No),
            ("upfront", MfReply::No),
            ("abroadJobFee", MfReply::No),
            ("familyDiscussed", MfReply::Yes),
        ];
        let c = cooling_check(
            today,
            None,
            None,
            DecisionKind::Partnership,
            Money::new(1, Currency::Uzs),
            &answers,
            CoolingExtra::default(),
        )
        .unwrap();
        let ours: Vec<(&str, &str)> = c.flags.iter().map(|f| (f.code, f.level.as_str())).collect();
        assert_eq!(ours, u12, "{n}");
        assert_eq!(c.signs, offer_check(&a).signs, "{n}");
    }
}
