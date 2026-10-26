//! HTTP API mustahkamligi (proptest): `apifuzz` harness'i orqali tasodifiy so'rovlar — ochiq va
//! haqiqiy PQ Link sessiyasi bilan muhrlangan. Har platformada (Windows ham) oddiy `cargo test` bilan;
//! chuqur qidiruv — `fuzz/fuzz_targets/http_api.rs` (libFuzzer).
#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::sync::LazyLock;

use mpay_e2e::apifuzz::ApiHarness;
use proptest::prelude::*;

static H: LazyLock<ApiHarness> = LazyLock::new(ApiHarness::new);

/// Tana: ixtiyoriy baytlar yoki API'ga o'xshash JSON (chuqurroq yo'llarga yetish uchun).
fn body() -> impl Strategy<Value = Vec<u8>> {
    let json = (
        prop::sample::select(vec![
            "pan",
            "expiry",
            "challenge_id",
            "otp",
            "request_hash",
            "preset",
            "integrity_token",
            "cert_chain",
            "signature",
            "terminal_id",
            "merchant_id",
            "stan",
            "icc_data",
        ]),
        prop::sample::select(vec![
            "\"9900121000010013\"".to_owned(),
            "\"3112\"".to_owned(),
            "\"\"".to_owned(),
            "null".to_owned(),
            "-1".to_owned(),
            "18446744073709551616".to_owned(),
            "[\"00\"]".to_owned(),
            "{}".to_owned(),
            "\"chl_00000000000000000000000000000000\"".to_owned(),
            "\"ZZZZ\"".to_owned(),
        ]),
        prop::collection::vec(any::<u8>(), 0..4),
    )
        .prop_map(|(k, v, extra)| {
            let mut b = format!("{{\"{k}\": {v}, \"expiry\": \"3112\"}}").into_bytes();
            b.extend(extra);
            b
        });
    prop_oneof![prop::collection::vec(any::<u8>(), 0..256), json]
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 400, ..ProptestConfig::default() })]

    #[test]
    fn api_never_500_and_keeps_error_contract(
        head in prop::collection::vec(any::<u8>(), 5),
        b in body(),
    ) {
        let mut input = head;
        input.extend(b);
        H.run(&input);
    }
}

/// Harness haqiqatan chuqur yo'llarga yetadi (aks holda fuzzing faqat 404/401 ni "sinardi").
#[test]
fn harness_reaches_handlers() {
    use mpay_e2e::apifuzz::Outcome;
    let sealed = |route: u8, json: &str| {
        let mut d = vec![1, route, 0, 0, 0];
        d.extend_from_slice(json.as_bytes());
        H.run(&d)
    };
    // Muhrlangan provisioning: yaroqli JSON — token yaratiladi; buzuq JSON — BAD_REQUEST.
    let pan = mpay_e2e::test_fpan(10, 9002);
    assert_eq!(
        sealed(0, &format!(r#"{{"pan":"{pan}","expiry":"3112"}}"#)),
        Outcome::Sealed(String::new())
    );
    assert_eq!(sealed(0, "{"), Outcome::Sealed("BAD_REQUEST".into()));
    assert_eq!(
        sealed(0, &format!(r#"{{"pan":"{pan}","expiry":"3112"}}"#)),
        Outcome::Sealed("CARD_ALREADY_ON_DEVICE".into())
    );
    // Sandbox mock tokeni (qurilma yo'li): begona hash — BAD_REQUEST.
    assert_eq!(
        sealed(5, r#"{"request_hash":"x"}"#),
        Outcome::Sealed("BAD_REQUEST".into())
    );
    // Ochiq: operator kaliti bilan token holati (`{id}` = haqiqiy token) — 200; kalitsiz — 401.
    assert_eq!(H.run(&[0, 7, 1, 0, 0]), Outcome::Plain(200));
    assert_eq!(H.run(&[0, 7, 0, 0, 0]), Outcome::Plain(401));
    // Terminal: buzuq avtorizatsiya JSON — 4xx.
    let r = H.run(&[0, 16, 2, 1, 0, b'{']);
    assert!(
        matches!(r, Outcome::Plain(s) if (400..500).contains(&s)),
        "{r:?}"
    );
}
