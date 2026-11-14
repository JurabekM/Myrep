//! Joylangan ONNX model: Python (onnxruntime) bilan parity va dvigatel darajasidagi tekshiruvlar.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::ports::{
    IdvDecider, IdvRequest, RiskDecision, RiskRequest, RiskScorer, SecurityLevel,
};
use mpay_common::{DeviceId, Pan, PanFingerprint, TokenId};
use mpay_shield::features::TXN_FEATURES;
use mpay_shield::model::{MlScorer, TractScorer};
use mpay_shield::Shield;
use time::OffsetDateTime;

#[test]
fn tract_matches_onnxruntime() {
    let m = TractScorer::default_model().unwrap();
    assert_eq!(m.meta().feature_names.len(), TXN_FEATURES.len());
    let text = include_str!("data/parity.csv");
    let mut lines = text.lines();
    let header: Vec<&str> = lines.next().unwrap().split(',').collect();
    assert_eq!(&header[..TXN_FEATURES.len()], &TXN_FEATURES[..]);
    let mut n = 0;
    for l in lines.filter(|l| !l.is_empty()) {
        let v: Vec<f32> = l.split(',').map(|x| x.parse().unwrap()).collect();
        let (f, want) = v.split_at(TXN_FEATURES.len());
        let got = m.predict(f).unwrap();
        assert!(
            (got - want[0]).abs() < 1e-4,
            "qator {n}: rust {got} ≠ python {}",
            want[0]
        );
        n += 1;
    }
    assert_eq!(n, 500);
}

#[test]
fn drifted_metadata_rejected() {
    let bad = r#"{"version":"x","feature_names":["a","b"]}"#;
    assert!(TractScorer::load(mpay_shield::model::DEFAULT_MODEL, bad).is_err());
}

fn req(at: i64, amount: u64, merchant: &str) -> RiskRequest {
    RiskRequest {
        token_id: TokenId::from_random([1; 16]),
        device_id: DeviceId([1; 32]),
        pan_fingerprint: PanFingerprint([2; 32]),
        amount_minor: amount,
        currency: 860,
        merchant_id: merchant.into(),
        terminal_id: "TERM0001".into(),
        country: 860,
        atc: 1,
        cdcvm_performed: false,
        at: OffsetDateTime::from_unix_timestamp(at).unwrap(),
    }
}

#[tokio::test]
async fn engine_with_model_ports() {
    let s = Shield::with_defaults().unwrap();
    // Provisioning (GREEN) va oddiy xarid (APPROVE).
    let idv = s
        .decide(&IdvRequest {
            fpan: Pan::from_prefix("990012100001001").unwrap(),
            pan_fingerprint: PanFingerprint([2; 32]),
            device_id: DeviceId([1; 32]),
            attestation_level: SecurityLevel::StrongBox,
            existing_tokens_for_pan: 0,
            existing_tokens_for_device: 0,
            at: OffsetDateTime::from_unix_timestamp(1_800_000_000).unwrap(),
        })
        .await
        .unwrap();
    assert_eq!(idv.decision, mpay_common::ports::IdvDecision::Green);
    let t0 = 1_800_000_000 + 30 * 86_400;
    let a = s.score(&req(t0, 12_500_000, "SHOP0001")).await.unwrap();
    assert_eq!(a.decision, RiskDecision::Approve, "{a:?}");
    // Tez-tez urinishlar → DECLINE.
    let mut last = a;
    for i in 1..8 {
        last = s.score(&req(t0 + i * 5, 50_000, "WEB0001")).await.unwrap();
    }
    assert_eq!(last.decision, RiskDecision::Decline, "{last:?}");
    assert!(last.score >= 800);
}
