//! Vault integratsion testlari: provisioning → LUK → lifecycle → detokenizatsiya → audit.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::sync::Arc;

use mpay_common::clock::{Clock, ManualClock};
use mpay_common::ports::{
    ConsumeOutcome, Detokenizer, IdvDecision, LukStatus, SecurityLevel, TokenState,
};
use mpay_common::{CardExpiry, DeviceId, Pan, TokenId};
use mpay_crypto::keystore::{ensure_standard_keys, KeyLabel, KeyStore, MemoryKeyStore};
use mpay_crypto::scheme::{CryptogramScheme, MpayAes128CmacV1};
use mpay_shield::StubShield;
use mpay_vault::{
    DeviceContext, ProvisionOutcome, ProvisionRequest, Vault, VaultConfig, VaultDetokenizer,
    VaultError,
};
use time::{Duration, OffsetDateTime};

struct Env {
    vault: Arc<Vault>,
    ks: Arc<dyn KeyStore>,
    clock: Arc<ManualClock>,
    _dir: tempfile::TempDir,
    db_path: std::path::PathBuf,
}

async fn env_with(cfg: VaultConfig) -> Env {
    let dir = tempfile::tempdir().unwrap();
    let db_path = dir.path().join("vault.db");
    let pool = mpay_vault::db::open_pool(&format!("sqlite://{}", db_path.display()))
        .await
        .unwrap();
    let ks: Arc<dyn KeyStore> = Arc::new(MemoryKeyStore::from_seed([7; 32]));
    ensure_standard_keys(ks.as_ref()).unwrap();
    let clock = Arc::new(ManualClock::new(OffsetDateTime::now_utc()));
    let vault = Vault::open(
        pool,
        ks.clone(),
        Arc::new(MpayAes128CmacV1),
        Arc::new(StubShield::default()),
        clock.clone(),
        cfg,
    )
    .await
    .unwrap();
    Env {
        vault: Arc::new(vault),
        ks,
        clock,
        _dir: dir,
        db_path,
    }
}

async fn env() -> Env {
    env_with(VaultConfig::default()).await
}

fn dev(n: u8) -> DeviceContext {
    DeviceContext {
        device_id: DeviceId([n; 32]),
        security_level: SecurityLevel::StrongBox,
    }
}

/// Stsenariy kodi (7–8-raqamlar) bilan test FPAN.
fn fpan(scenario: u8, acct: u32) -> Pan {
    Pan::from_prefix(&format!("990012{scenario:02}{acct:07}")).unwrap()
}

fn req(p: &Pan) -> ProvisionRequest {
    ProvisionRequest {
        fpan: p.clone(),
        expiry: CardExpiry::new(2031, 12).unwrap(),
    }
}

#[tokio::test]
async fn green_provisioning_issues_valid_luks() {
    let e = env().await;
    let p = fpan(10, 1);
    let out = e.vault.provision(req(&p), dev(1)).await.unwrap();
    let ProvisionOutcome::Active { profile, idv } = out else {
        panic!("ACTIVE kutilgan");
    };
    assert_eq!(idv.decision, IdvDecision::Green);
    assert_eq!(profile.luks.len(), 5);
    assert_eq!(profile.dpan.kind(), mpay_common::PanKind::Device);
    assert!(profile.dpan.expose_digits().starts_with("990077"));
    assert_ne!(profile.dpan, p);
    assert_eq!(profile.aid, "F04D50415901");

    // LUK'lar IMK'dan mustaqil qayta hosil qilinadigan qiymatga teng.
    let s = MpayAes128CmacV1;
    for g in &profile.luks {
        let k = s
            .luk_from_imk(
                e.ks.as_ref(),
                &KeyLabel::new(KeyLabel::IMK_AC),
                &profile.dpan,
                profile.psn,
                g.seq,
            )
            .unwrap();
        assert_eq!(k, g.key);
        assert_eq!(g.max_uses, 10);
        assert_eq!(g.expires_at - g.issued_at, 86_400);
    }
    let seqs: Vec<u32> = profile.luks.iter().map(|l| l.seq).collect();
    assert_eq!(seqs, vec![1, 2, 3, 4, 5]);

    let sum = e.vault.summary(&profile.token_id).await.unwrap();
    assert_eq!(sum.state, TokenState::Active);
    assert_eq!(sum.luks_active, 5);
    assert!(sum.fpan_masked.contains("******"));
    // Debug ko'rinishlarida sir yo'q.
    assert!(!format!("{profile:?}").contains(profile.dpan.expose_digits()));
    assert!(!format!("{:?}", profile.luks[0]).contains(&hex::encode(profile.luks[0].key.expose())));
}

#[tokio::test]
async fn red_declined_and_no_token_created() {
    let e = env().await;
    let out = e.vault.provision(req(&fpan(95, 2)), dev(1)).await.unwrap();
    assert!(matches!(out, ProvisionOutcome::Declined { .. }));
    let n: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM vault_tokens")
        .fetch_one(e.vault.pool())
        .await
        .unwrap();
    assert_eq!(n, 0);
}

#[tokio::test]
async fn yellow_otp_flow() {
    let e = env().await;
    let out = e.vault.provision(req(&fpan(85, 3)), dev(2)).await.unwrap();
    let ProvisionOutcome::PendingIdv {
        token_id,
        challenge_id,
        ..
    } = out
    else {
        panic!("PENDING_IDV kutilgan");
    };
    assert_eq!(
        e.vault.summary(&token_id).await.unwrap().state,
        TokenState::PendingIdv
    );
    // LUK to'ldirish faollashtirishdan oldin taqiqlangan.
    assert!(matches!(
        e.vault.replenish_luks(&token_id, dev(2)).await,
        Err(VaultError::InvalidState { .. })
    ));

    let otp = e.vault.sandbox_otp(&challenge_id).await.unwrap();
    assert_eq!(otp.len(), 6);
    let wrong = if otp == "000000" { "000001" } else { "000000" };
    assert!(matches!(
        e.vault
            .verify_otp(&token_id, &challenge_id, wrong, dev(2))
            .await,
        Err(VaultError::OtpInvalid)
    ));
    // Boshqa qurilma OTP kirita olmaydi.
    assert!(matches!(
        e.vault
            .verify_otp(&token_id, &challenge_id, &otp, dev(9))
            .await,
        Err(VaultError::DeviceMismatch)
    ));
    let profile = e
        .vault
        .verify_otp(&token_id, &challenge_id, &otp, dev(2))
        .await
        .unwrap();
    assert_eq!(profile.luks.len(), 5);
    assert_eq!(
        e.vault.summary(&token_id).await.unwrap().state,
        TokenState::Active
    );
    // Challenge bir martalik.
    assert!(matches!(
        e.vault
            .verify_otp(&token_id, &challenge_id, &otp, dev(2))
            .await,
        Err(VaultError::InvalidState { .. })
    ));
}

#[tokio::test]
async fn otp_lockout_and_expiry() {
    let e = env().await;
    let ProvisionOutcome::PendingIdv {
        token_id,
        challenge_id,
        ..
    } = e.vault.provision(req(&fpan(80, 4)), dev(3)).await.unwrap()
    else {
        panic!()
    };
    let otp = e.vault.sandbox_otp(&challenge_id).await.unwrap();
    let wrong = if otp == "111111" { "222222" } else { "111111" };
    assert!(matches!(
        e.vault
            .verify_otp(&token_id, &challenge_id, wrong, dev(3))
            .await,
        Err(VaultError::OtpInvalid)
    ));
    assert!(matches!(
        e.vault
            .verify_otp(&token_id, &challenge_id, wrong, dev(3))
            .await,
        Err(VaultError::OtpInvalid)
    ));
    assert!(matches!(
        e.vault
            .verify_otp(&token_id, &challenge_id, wrong, dev(3))
            .await,
        Err(VaultError::OtpLocked)
    ));
    // Endi to'g'ri OTP ham rad.
    assert!(matches!(
        e.vault
            .verify_otp(&token_id, &challenge_id, &otp, dev(3))
            .await,
        Err(VaultError::OtpLocked)
    ));

    let ProvisionOutcome::PendingIdv {
        token_id,
        challenge_id,
        ..
    } = e.vault.provision(req(&fpan(81, 5)), dev(3)).await.unwrap()
    else {
        panic!()
    };
    let otp = e.vault.sandbox_otp(&challenge_id).await.unwrap();
    e.clock.advance(Duration::minutes(6));
    assert!(matches!(
        e.vault
            .verify_otp(&token_id, &challenge_id, &otp, dev(3))
            .await,
        Err(VaultError::OtpExpired)
    ));
}

#[tokio::test]
async fn lifecycle_transitions() {
    let e = env().await;
    let ProvisionOutcome::Active { profile, .. } =
        e.vault.provision(req(&fpan(1, 6)), dev(4)).await.unwrap()
    else {
        panic!()
    };
    let t = &profile.token_id;
    assert_eq!(
        e.vault.suspend(t, "operator:op1").await.unwrap().state,
        TokenState::Suspended
    );
    assert!(matches!(
        e.vault.suspend(t, "operator:op1").await,
        Err(VaultError::InvalidState { .. })
    ));
    assert!(matches!(
        e.vault.replenish_luks(t, dev(4)).await,
        Err(VaultError::InvalidState { .. })
    ));
    assert_eq!(
        e.vault.resume(t, "operator:op1").await.unwrap().state,
        TokenState::Active
    );
    // Boshqa qurilma LUK so'ray olmaydi.
    assert!(matches!(
        e.vault.replenish_luks(t, dev(5)).await,
        Err(VaultError::DeviceMismatch)
    ));
    let more = e.vault.replenish_luks(t, dev(4)).await.unwrap();
    assert_eq!(more.first().unwrap().seq, 6);
    // Faol LUK limiti (2 × batch).
    assert!(matches!(
        e.vault.replenish_luks(t, dev(4)).await,
        Err(VaultError::TooManyLuks)
    ));

    let s = e.vault.delete(t, "operator:op1").await.unwrap();
    assert_eq!(s.state, TokenState::Deleted);
    assert_eq!(s.luks_active, 0, "o'chirilganda LUK'lar bekor qilinadi");
    assert!(matches!(
        e.vault.resume(t, "operator:op1").await,
        Err(VaultError::InvalidState { .. })
    ));
    assert!(matches!(
        e.vault.summary(&TokenId::from_random([1; 16])).await,
        Err(VaultError::TokenNotFound)
    ));
}

#[tokio::test]
async fn detokenizer_lookup_and_consume_rules() {
    let e = env_with(VaultConfig {
        luk: mpay_common::config::LukPolicy {
            max_uses: 2,
            ttl_secs: 3600,
            batch_size: 2,
        },
        ..VaultConfig::default()
    })
    .await;
    let ProvisionOutcome::Active { profile, .. } =
        e.vault.provision(req(&fpan(2, 7)), dev(6)).await.unwrap()
    else {
        panic!()
    };
    let det = VaultDetokenizer::new(e.vault.clone(), "issuer");
    let t = &profile.token_id;

    let v = det.lookup(&profile.dpan, 1).await.unwrap().unwrap();
    assert_eq!(v.fpan, fpan(2, 7));
    assert_eq!(v.state, TokenState::Active);
    assert_eq!(v.luk, LukStatus::Valid { remaining_uses: 2 });
    assert_eq!(v.last_atc, None);
    assert_eq!(
        det.lookup(&profile.dpan, 99).await.unwrap().unwrap().luk,
        LukStatus::Unknown
    );
    // Noma'lum DPAN va FPAN bilan qidiruv.
    assert!(det
        .lookup(&Pan::from_prefix("990077999999999").unwrap(), 1)
        .await
        .unwrap()
        .is_none());
    assert!(det.lookup(&fpan(2, 7), 1).await.unwrap().is_none());

    assert_eq!(
        det.consume(t, 1, 1).await.unwrap(),
        ConsumeOutcome::Consumed
    );
    assert_eq!(
        det.consume(t, 1, 1).await.unwrap(),
        ConsumeOutcome::AtcReplay
    );
    assert_eq!(
        det.consume(t, 1, 3).await.unwrap(),
        ConsumeOutcome::Consumed
    );
    assert_eq!(
        det.consume(t, 1, 4).await.unwrap(),
        ConsumeOutcome::LukExhausted
    );
    assert_eq!(
        det.consume(t, 9, 5).await.unwrap(),
        ConsumeOutcome::LukUnknown
    );
    assert_eq!(
        det.lookup(&profile.dpan, 2)
            .await
            .unwrap()
            .unwrap()
            .last_atc,
        Some(3)
    );

    e.clock.advance(Duration::hours(2));
    assert_eq!(
        det.lookup(&profile.dpan, 2).await.unwrap().unwrap().luk,
        LukStatus::Expired
    );
    assert_eq!(
        det.consume(t, 2, 6).await.unwrap(),
        ConsumeOutcome::LukExpired
    );

    e.vault.suspend(t, "operator:op").await.unwrap();
    assert_eq!(
        det.consume(t, 2, 7).await.unwrap(),
        ConsumeOutcome::TokenNotActive
    );
    let _ = e.clock.unix();
}

#[tokio::test]
async fn pan_is_only_stored_encrypted() {
    let e = env().await;
    let p = fpan(3, 1_234_567);
    let ProvisionOutcome::Active { profile, .. } =
        e.vault.provision(req(&p), dev(7)).await.unwrap()
    else {
        panic!()
    };
    // Ikkinchi token o'sha karta uchun — karta qatori qayta ishlatiladi.
    e.vault.provision(req(&p), dev(8)).await.unwrap();
    let cards: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM vault_cards")
        .fetch_one(e.vault.pool())
        .await
        .unwrap();
    assert_eq!(cards, 1);

    sqlx::query("PRAGMA wal_checkpoint(TRUNCATE)")
        .execute(e.vault.pool())
        .await
        .unwrap();
    let mut raw = std::fs::read(&e.db_path).unwrap();
    if let Ok(wal) = std::fs::read(e.db_path.with_extension("db-wal")) {
        raw.extend_from_slice(&wal);
    }
    for secret in [p.expose_digits(), profile.dpan.expose_digits()] {
        let needle = secret.as_bytes();
        assert!(
            !raw.windows(needle.len()).any(|w| w == needle),
            "DB faylida ochiq PAN topildi"
        );
        // Track 2 BCD ko'rinishi ham yo'q.
        let bcd: Vec<u8> = needle
            .chunks(2)
            .map(|c| ((c[0] - b'0') << 4) | (c[1] - b'0'))
            .collect();
        assert!(!raw.windows(bcd.len()).any(|w| w == bcd.as_slice()));
    }
    // LUK kalitlari ham DB'da yo'q.
    let key = profile.luks[0].key.expose();
    assert!(!raw.windows(16).any(|w| w == key));
}

#[tokio::test]
async fn audit_chain_verifies_and_is_append_only() {
    let e = env().await;
    let ProvisionOutcome::Active { profile, .. } =
        e.vault.provision(req(&fpan(4, 9)), dev(9)).await.unwrap()
    else {
        panic!()
    };
    e.vault
        .suspend(&profile.token_id, "operator:op")
        .await
        .unwrap();
    e.vault
        .resume(&profile.token_id, "operator:op")
        .await
        .unwrap();
    let rep = e.vault.verify_audit().await.unwrap();
    assert!(rep.entries >= 5, "{rep:?}");

    // UPDATE va DELETE trigger tomonidan taqiqlangan.
    assert!(
        sqlx::query("UPDATE vault_audit SET actor = 'x' WHERE seq = 2")
            .execute(e.vault.pool())
            .await
            .is_err()
    );
    assert!(sqlx::query("DELETE FROM vault_audit WHERE seq = 2")
        .execute(e.vault.pool())
        .await
        .is_err());

    // Trigger'ni chetlab o'tgan hujumchi (DB fayliga to'g'ridan-to'g'ri yozish) — zanjir tekshiruvi aniqlaydi.
    sqlx::query("DROP TRIGGER vault_audit_no_update")
        .execute(e.vault.pool())
        .await
        .unwrap();
    sqlx::query("UPDATE vault_audit SET details = '{}' WHERE seq = 3")
        .execute(e.vault.pool())
        .await
        .unwrap();
    assert!(matches!(
        e.vault.verify_audit().await,
        Err(VaultError::AuditBroken(3))
    ));

    // Audit yozuvlarida ochiq PAN yo'q.
    let details: Vec<String> = sqlx::query_scalar("SELECT details FROM vault_audit")
        .fetch_all(e.vault.pool())
        .await
        .unwrap();
    for d in details {
        assert!(!d.contains(profile.dpan.expose_digits()));
        assert!(!d.contains(fpan(4, 9).expose_digits()));
    }
}

#[tokio::test]
async fn validation_errors() {
    let e = env().await;
    let dpan = Pan::from_prefix("990077000000001").unwrap();
    assert!(matches!(
        e.vault.provision(req(&dpan), dev(1)).await,
        Err(VaultError::BadRequest(_))
    ));
    let expired = ProvisionRequest {
        fpan: fpan(1, 1),
        expiry: CardExpiry::new(2020, 1).unwrap(),
    };
    assert!(matches!(
        e.vault.provision(expired, dev(1)).await,
        Err(VaultError::BadRequest(_))
    ));

    let small = env_with(VaultConfig {
        max_tokens_per_device: 1,
        ..VaultConfig::default()
    })
    .await;
    small
        .vault
        .provision(req(&fpan(1, 2)), dev(1))
        .await
        .unwrap();
    assert!(matches!(
        small.vault.provision(req(&fpan(1, 3)), dev(1)).await,
        Err(VaultError::TooManyTokens)
    ));
}

#[tokio::test]
async fn reopen_with_same_seed_reads_existing_data() {
    let dir = tempfile::tempdir().unwrap();
    let url = format!("sqlite://{}", dir.path().join("v.db").display());
    let mk = |seed: [u8; 32]| {
        let url = url.clone();
        async move {
            let ks: Arc<dyn KeyStore> = Arc::new(MemoryKeyStore::from_seed(seed));
            ensure_standard_keys(ks.as_ref()).unwrap();
            Vault::open(
                mpay_vault::db::open_pool(&url).await.unwrap(),
                ks,
                Arc::new(MpayAes128CmacV1),
                Arc::new(StubShield::default()),
                Arc::new(mpay_common::clock::SystemClock),
                VaultConfig::default(),
            )
            .await
        }
    };
    let v1 = Arc::new(mk([1; 32]).await.unwrap());
    let ProvisionOutcome::Active { profile, .. } =
        v1.provision(req(&fpan(5, 5)), dev(1)).await.unwrap()
    else {
        panic!()
    };
    drop(v1);
    let v2 = Arc::new(mk([1; 32]).await.unwrap());
    let det = VaultDetokenizer::new(v2, "issuer");
    assert_eq!(
        det.lookup(&profile.dpan, 1).await.unwrap().unwrap().fpan,
        fpan(5, 5)
    );
    // Boshqa urug' (boshqa KEK) bilan ochib bo'lmaydi.
    assert!(mk([2; 32]).await.is_err());
}
