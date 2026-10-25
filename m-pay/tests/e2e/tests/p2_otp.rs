//! 2-faza P2.1 (ADR-0016): OTP karta egasining emitentdagi telefoniga virtual SMS shlyuzi
//! (`mpay-smsgw`) orqali yetkaziladi; qayta yuborish, chegaralar, nosozliklar va loglar.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::api::{ProvisionResponse, SandboxOtp};
use mpay_common::TokenId;
use mpay_e2e::{logs, test_fpan, Sandbox};
use mpay_issuer::TestAccount;
use mpay_server::config::ShieldEngine;
use mpay_server::otp::{OtpChannelKind, WebhookConfig};
use mpay_smsgw::{Gateway, RunningGateway};
use mpay_terminal_sim::wallet::SoftWallet;
use mpay_terminal_sim::WalletError;

/// Shlyuz + webhook kanalli server. `env` — shu test uchun alohida token o'zgaruvchisi.
async fn setup(env: &str, accounts: Vec<TestAccount>) -> (Sandbox, RunningGateway, String) {
    let token = format!("sinov-{env}");
    std::env::set_var(env, &token);
    let gw = mpay_smsgw::spawn(
        "127.0.0.1:0".parse().unwrap(),
        Gateway::new(Some(token.clone())),
    )
    .await
    .unwrap();
    let url = gw.url();
    let env = env.to_owned();
    let sb = Sandbox::start_with(move |c| {
        c.shield.engine = ShieldEngine::Engine;
        c.issuer.accounts = accounts;
        c.otp.channel = OtpChannelKind::Webhook;
        c.otp.webhook = Some(WebhookConfig {
            url,
            token_env: Some(env),
            timeout_ms: 2000,
            ca_file: None,
        });
    })
    .await;
    (sb, gw, token)
}

fn account(pan: &str, phone: Option<&str>) -> TestAccount {
    TestAccount {
        pan: pan.to_owned(),
        balance_minor: 100_000_000,
        label: "p2".into(),
        phone: phone.map(str::to_owned),
    }
}

/// Karta birinchi telefonda faollashadi, ikkinchisida — YELLOW (OTP kerak).
async fn second_device_pending(
    sb: &Sandbox,
    card: &str,
) -> (SoftWallet, SoftWallet, TokenId, String, Option<String>) {
    let mut phone1 = sb.wallet().await;
    assert!(matches!(
        phone1.provision(card, "3112").await.unwrap(),
        ProvisionResponse::Active { .. }
    ));
    let mut phone2 = sb.wallet().await;
    let ProvisionResponse::PendingIdv {
        token_id,
        challenge_id,
        otp_sent_to,
        ..
    } = phone2.provision(card, "3112").await.unwrap()
    else {
        panic!("YELLOW kutilgan");
    };
    (phone1, phone2, token_id, challenge_id, otp_sent_to)
}

fn api_code(e: &WalletError) -> (u16, String) {
    match e {
        WalletError::Api { status, code, .. } => (*status, code.clone()),
        other => panic!("API xatosi kutilgan: {other:?}"),
    }
}

/// SMS matnidan 6 xonali kodni oladi (foydalanuvchi telefondan o'qigandek).
fn code_from_sms(text: &str) -> String {
    text.split(|c: char| !c.is_ascii_digit())
        .find(|w| w.len() == 6)
        .expect("SMS'da kod yo'q")
        .to_owned()
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn otp_sms_delivered_resent_and_verified() {
    let card = test_fpan(10, 4101);
    let phone = "+998000004101";
    let (sb, gw, _) = setup("MPAY_E2E_SMS_TOKEN_A", vec![account(&card, Some(phone))]).await;
    let (mut phone1, mut phone2, token_id, challenge_id, sent_to) =
        second_device_pending(&sb, &card).await;
    assert_eq!(sent_to.as_deref(), Some("+998*******01"));

    // SMS karta egasining emitentdagi raqamiga keldi; kod sandbox OTP bilan bir xil.
    let inbox = gw.gateway.messages(Some(phone));
    assert_eq!(inbox.len(), 1, "{inbox:?}");
    assert_eq!(inbox[0].reference, challenge_id);
    let otp: SandboxOtp = sb
        .client()
        .get_json(
            &format!("/v1/sandbox/otp/{challenge_id}"),
            Some(&sb.operator_key),
        )
        .await
        .unwrap();
    let code = code_from_sms(&inbox[0].text);
    assert_eq!(code, *otp.otp);
    assert!(inbox[0].text.contains("hech kimga aytmang"));

    // Boshqa qurilma bu challenge uchun SMS so'ray olmaydi.
    let e = phone1
        .resend_otp(&token_id, &challenge_id)
        .await
        .unwrap_err();
    assert_eq!(api_code(&e), (403, "DEVICE_MISMATCH".into()));

    // Qayta yuborish: o'sha kod, chegara — 3 marta.
    for i in 0..3 {
        let r = phone2.resend_otp(&token_id, &challenge_id).await.unwrap();
        assert_eq!(r.otp_sent_to, "+998*******01");
        assert_eq!(gw.gateway.messages(Some(phone)).len(), 2 + i);
    }
    let e = phone2
        .resend_otp(&token_id, &challenge_id)
        .await
        .unwrap_err();
    assert_eq!(api_code(&e), (429, "OTP_RESEND_LIMIT".into()));
    let inbox = gw.gateway.messages(Some(phone));
    assert_eq!(inbox.len(), 4);
    assert!(inbox.iter().all(|m| code_from_sms(&m.text) == code));

    // SMS'dagi kod bilan tasdiqlash → token faol.
    let profile = phone2
        .verify_otp(&token_id, &challenge_id, &code)
        .await
        .unwrap();
    assert_eq!(profile.luks.len(), 5);
    let e = phone2
        .resend_otp(&token_id, &challenge_id)
        .await
        .unwrap_err();
    assert_eq!(api_code(&e), (404, "CHALLENGE_NOT_FOUND".into()));

    // Server logida OTP ham, to'liq telefon ham yo'q (faqat maskalangan).
    let log = logs().text();
    assert!(
        log.contains("+998*******01"),
        "maskalangan telefon logda bo'lishi kerak"
    );
    assert!(!log.contains(phone), "to'liq telefon logga tushdi");
    assert!(!log.contains(&code), "OTP logga tushdi");
    assert!(!log.contains(&card), "PAN logga tushdi");
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn otp_without_phone_and_gateway_failures() {
    let no_phone = test_fpan(10, 4201);
    let flaky = test_fpan(10, 4202);
    let phone = "+998000004202";
    let (sb, mut gw, token) = setup(
        "MPAY_E2E_SMS_TOKEN_B",
        vec![account(&no_phone, None), account(&flaky, Some(phone))],
    )
    .await;

    // Emitentda telefon yo'q: provisioning to'xtamaydi, SMS yuborilmaydi, resend — NO_CONTACT.
    let (_p1, mut p2, tok, ch, sent_to) = second_device_pending(&sb, &no_phone).await;
    assert_eq!(sent_to, None);
    let e = p2.resend_otp(&tok, &ch).await.unwrap_err();
    assert_eq!(api_code(&e), (409, "NO_CONTACT".into()));

    // Operator nosoz (2 × 503 — server bir marta qayta urinadi): javobda `otp_sent_to` yo'q,
    // qurilma keyin `resend` qiladi.
    gw.gateway.fail_next(2);
    let (_q1, mut q2, tok, ch, sent_to) = second_device_pending(&sb, &flaky).await;
    assert_eq!(sent_to, None);
    assert!(gw.gateway.messages(Some(phone)).is_empty());
    // Bitta 503 dan keyin qayta urinish muvaffaqiyatli.
    gw.gateway.fail_next(1);
    assert_eq!(
        q2.resend_otp(&tok, &ch).await.unwrap().otp_sent_to,
        "+998*******02"
    );
    assert_eq!(gw.gateway.messages(Some(phone)).len(), 1);

    // Shlyuz tokeni noto'g'ri bo'lsa 401 → qayta urinilmaydi; to'g'ri tokenli so'rov o'tadi.
    let http = raw_post(gw.addr, "noto'g'ri").await;
    assert_eq!(http, 401);
    assert_eq!(raw_post(gw.addr, &token).await, 202);

    // Shlyuz butunlay o'chgan → 502 OTP_DELIVERY_FAILED.
    gw.shutdown();
    tokio::time::sleep(std::time::Duration::from_millis(200)).await;
    let e = q2.resend_otp(&tok, &ch).await.unwrap_err();
    assert_eq!(api_code(&e), (502, "OTP_DELIVERY_FAILED".into()));
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn sandbox_channel_does_not_send() {
    let card = test_fpan(10, 4301);
    let sb = Sandbox::start_with(|c| {
        c.shield.engine = ShieldEngine::Engine;
        c.issuer.accounts = vec![account(&card, Some("+998000004301"))];
    })
    .await;
    let (_p1, mut p2, tok, ch, sent_to) = second_device_pending(&sb, &card).await;
    assert_eq!(sent_to, None);
    let e = p2.resend_otp(&tok, &ch).await.unwrap_err();
    assert_eq!(api_code(&e), (409, "OTP_CHANNEL_DISABLED".into()));
}

/// Shlyuzga to'g'ridan-to'g'ri `POST /send` (HTTP/1.1, tokio TCP) — status kodini qaytaradi.
async fn raw_post(addr: std::net::SocketAddr, token: &str) -> u16 {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    let body = r#"{"to":"+998000009999","text":"sinov","reference":"x"}"#;
    let req = format!(
        "POST /send HTTP/1.1\r\nHost: {addr}\r\nAuthorization: Bearer {token}\r\n\
         Content-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    );
    let mut s = tokio::net::TcpStream::connect(addr).await.unwrap();
    s.write_all(req.as_bytes()).await.unwrap();
    let mut out = String::new();
    s.read_to_string(&mut out).await.unwrap();
    out[9..12].parse().unwrap()
}
