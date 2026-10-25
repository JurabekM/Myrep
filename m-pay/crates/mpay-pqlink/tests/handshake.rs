//! PQ Link integratsion testlari: to'liq handshake, replay, buzilgan imzo va attestatsiya.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::sync::Arc;

use mpay_common::clock::{Clock, ManualClock};
use mpay_common::ports::SecurityLevel;
use mpay_crypto::keystore::{KeyKind, KeyLabel, KeyStore, MemoryKeyStore};
use mpay_pqlink::attestation::AttestationPolicy;
use mpay_pqlink::identity::ServerSigner;
use mpay_pqlink::sandbox::{SandboxAttestationCa, SoftDeviceKey};
use mpay_pqlink::wire::{ServerHello, MLDSA65_SIG_LEN};
use mpay_pqlink::{
    ClientHandshake, ClientSession, DeviceSigner, KeyStoreServerSigner, MlDsaSeedBlob, PqLinkError,
    PqLinkServer, ServerConfig, ServerIdentity,
};
use time::{Duration, OffsetDateTime};

struct Fixture {
    server: PqLinkServer,
    signer: Arc<KeyStoreServerSigner>,
    ca: SandboxAttestationCa,
    device: SoftDeviceKey,
    clock: Arc<ManualClock>,
}

fn fixture_with(cfg: ServerConfig) -> Fixture {
    let ks: Arc<dyn KeyStore> = Arc::new(MemoryKeyStore::random());
    let kek = KeyLabel::new(KeyLabel::KEK);
    let ed = KeyLabel::new(KeyLabel::SERVER_ED25519);
    ks.ensure_key(&kek, KeyKind::Aes256).unwrap();
    ks.ensure_key(&ed, KeyKind::Ed25519).unwrap();
    let blob = MlDsaSeedBlob::generate(ks.as_ref(), &kek).unwrap();
    let signer = Arc::new(KeyStoreServerSigner::new(ks, ed, blob).unwrap());
    let ca = SandboxAttestationCa::generate().unwrap();
    let device = ca
        .issue_device(SecurityLevel::StrongBox, b"enroll")
        .unwrap();
    let clock = Arc::new(ManualClock::new(OffsetDateTime::now_utc()));
    let server = PqLinkServer::new(signer.clone(), ca.anchors().unwrap(), cfg, clock.clone());
    Fixture {
        server,
        signer,
        ca,
        device,
        clock,
    }
}

fn fixture() -> Fixture {
    fixture_with(ServerConfig::default())
}

fn connect(f: &Fixture, device: &dyn DeviceSigner) -> Result<ClientSession, PqLinkError> {
    let (hs, ch) = ClientHandshake::start(f.signer.identity().clone())?;
    let sh = f.server.handle_hello(&ch)?;
    let (pending, cf) = hs.on_server_hello(&sh, device)?;
    let (_info, sa) = f.server.handle_finish(&cf)?;
    pending.on_accept(&sa)
}

#[test]
fn full_handshake_and_records() {
    let f = fixture();
    let mut c = connect(&f, &f.device).unwrap();
    assert_eq!(f.server.session_count(), 1);

    for i in 0..5u8 {
        let req = c.seal(&[b'q', i]).unwrap();
        let (info, pt) = f.server.open(&req).unwrap();
        assert_eq!(&pt[..], &[b'q', i]);
        assert_eq!(info.device_id, c.device_id());
        assert_eq!(info.security_level, SecurityLevel::StrongBox);
        let resp = f.server.seal(&info.session_id, &[b'r', i]).unwrap();
        assert_eq!(&c.open(&resp).unwrap()[..], &[b'r', i]);
    }
}

#[test]
fn replayed_and_reordered_records_rejected() {
    let f = fixture();
    let mut c = connect(&f, &f.device).unwrap();
    let r1 = c.seal(b"one").unwrap();
    let r2 = c.seal(b"two").unwrap();

    // Tartibsiz: r2 r1 dan oldin.
    assert_eq!(
        f.server.open(&r2).unwrap_err(),
        PqLinkError::Replay {
            expected: 1,
            got: 2
        }
    );
    f.server.open(&r1).unwrap();
    // Takror: r1 qayta.
    assert_eq!(
        f.server.open(&r1).unwrap_err(),
        PqLinkError::Replay {
            expected: 2,
            got: 1
        }
    );
    // Sessiya buzilmagan — r2 endi qabul qilinadi.
    f.server.open(&r2).unwrap();

    // Server javobi ham takrorlanmaydi.
    let (_, sid) = (0, *c.session_id());
    let s1 = f.server.seal(&sid, b"a").unwrap();
    c.open(&s1).unwrap();
    assert!(matches!(c.open(&s1), Err(PqLinkError::Replay { .. })));
}

#[test]
fn tampered_record_rejected_but_session_survives() {
    let f = fixture();
    let mut c = connect(&f, &f.device).unwrap();
    let r = c.seal(b"pan").unwrap();
    // `session_id` va `seq` ochiq sarlavhada: begona tomon soxta yozuv yuborsa ham sessiya yopilmasin.
    let mut forged = r.clone();
    let n = forged.len();
    forged[n - 1] ^= 0x80;
    assert_eq!(f.server.open(&forged).unwrap_err(), PqLinkError::Decrypt);
    assert_eq!(f.server.session_count(), 1);
    // Haqiqiy yozuv (o'sha seq) baribir qabul qilinadi.
    assert_eq!(&*f.server.open(&r).unwrap().1, b"pan");
}

/// ServerHello'dagi imzoni buzib client'ga beradi.
fn tamper_sh(sh: &[u8], offset_from_sig: usize) -> Vec<u8> {
    let (_, unsigned_len) = ServerHello::decode(sh).unwrap();
    let mut b = sh.to_vec();
    b[unsigned_len + offset_from_sig] ^= 0x01;
    b
}

#[test]
fn broken_ed25519_signature_rejected() {
    let f = fixture();
    let (hs, ch) = ClientHandshake::start(f.signer.identity().clone()).unwrap();
    let sh = f.server.handle_hello(&ch).unwrap();
    let bad = tamper_sh(&sh, 5);
    assert_eq!(
        hs.on_server_hello(&bad, &f.device).err(),
        Some(PqLinkError::BadServerSignature("Ed25519"))
    );
}

#[test]
fn broken_mldsa_signature_rejected() {
    let f = fixture();
    let (hs, ch) = ClientHandshake::start(f.signer.identity().clone()).unwrap();
    let sh = f.server.handle_hello(&ch).unwrap();
    let bad = tamper_sh(&sh, 64 + 1000);
    assert!(matches!(
        hs.on_server_hello(&bad, &f.device),
        Err(PqLinkError::BadServerSignature(_))
    ));
}

#[test]
fn broken_server_finished_rejected() {
    let f = fixture();
    let (hs, ch) = ClientHandshake::start(f.signer.identity().clone()).unwrap();
    let sh = f.server.handle_hello(&ch).unwrap();
    let bad = tamper_sh(&sh, 64 + MLDSA65_SIG_LEN + 3);
    assert_eq!(
        hs.on_server_hello(&bad, &f.device).err(),
        Some(PqLinkError::BadFinished)
    );
}

/// Faqat bitta (Ed25519) kalitni egallagan hujumchi: ML-DSA qismi boshqa kalit bilan.
#[test]
fn server_with_only_one_valid_key_rejected() {
    let real = fixture();
    let other = fixture();
    // Mijoz haqiqiy serverni pinlagan, lekin u boshqa serverga ulanadi: fp mos emas.
    let (hs, ch) = ClientHandshake::start(real.signer.identity().clone()).unwrap();
    let sh = other.server.handle_hello(&ch).unwrap();
    assert_eq!(
        hs.on_server_hello(&sh, &real.device).err(),
        Some(PqLinkError::ServerNotPinned)
    );

    // Hujumchi pinlangan fp'ni qo'yib, o'z imzolari bilan yuboradi (Ed25519 ham, ML-DSA ham boshqa).
    let (hs, ch) = ClientHandshake::start(real.signer.identity().clone()).unwrap();
    let sh = other.server.handle_hello(&ch).unwrap();
    let (mut parsed, _) = ServerHello::decode(&sh).unwrap();
    parsed.server_fp = real.signer.identity().fingerprint();
    let forged = parsed.encode().unwrap();
    assert!(matches!(
        hs.on_server_hello(&forged, &real.device),
        Err(PqLinkError::BadServerSignature(_))
    ));

    // Gibrid kafolat: Ed25519 to'g'ri, ML-DSA esa boshqa kalitniki bo'lgan identifikator.
    let mixed = ServerIdentity::new(
        real.signer.identity().ed25519,
        other.signer.identity().mldsa65.clone(),
    )
    .unwrap();
    let th = [9u8; 32];
    let (ed, ml) = real.signer.sign(&th).unwrap();
    assert!(mixed.verify(&th, &ed, &ml).is_err());
}

#[test]
fn untrusted_or_weak_device_rejected() {
    let f = fixture();
    // Boshqa CA bergan qurilma.
    let rogue_ca = SandboxAttestationCa::generate().unwrap();
    let rogue = rogue_ca
        .issue_device(SecurityLevel::StrongBox, b"")
        .unwrap();
    assert!(matches!(
        connect(&f, &rogue),
        Err(PqLinkError::Attestation(_))
    ));
    // TEE darajasi (siyosat: StrongBox).
    let tee =
        f.ca.issue_device(SecurityLevel::TrustedEnvironment, b"")
            .unwrap();
    assert!(matches!(
        connect(&f, &tee),
        Err(PqLinkError::Attestation(_))
    ));
    // Muvaffaqiyatsiz handshake'lar sessiya qoldirmaydi.
    assert_eq!(f.server.session_count(), 0);

    // Yumshoq siyosat bilan TEE qabul qilinadi.
    let relaxed = fixture_with(ServerConfig {
        attestation: AttestationPolicy {
            min_security_level: SecurityLevel::TrustedEnvironment,
            ..AttestationPolicy::default()
        },
        ..ServerConfig::default()
    });
    let tee2 = relaxed
        .ca
        .issue_device(SecurityLevel::TrustedEnvironment, b"")
        .unwrap();
    assert!(connect(&relaxed, &tee2).is_ok());
}

/// Zanjir to'g'ri, lekin imzo boshqa kalit bilan (kalit o'g'irlanmagan qurilma zanjirini ko'chirish).
struct ChainThief<'a> {
    chain_of: &'a SoftDeviceKey,
    key_of: &'a SoftDeviceKey,
}

impl DeviceSigner for ChainThief<'_> {
    fn cert_chain(&self) -> Vec<Vec<u8>> {
        self.chain_of.cert_chain()
    }
    fn sign(&self, msg: &[u8]) -> Result<Vec<u8>, PqLinkError> {
        self.key_of.sign(msg)
    }
}

#[test]
fn copied_attestation_chain_rejected() {
    let f = fixture();
    let other = f.ca.issue_device(SecurityLevel::StrongBox, b"").unwrap();
    let thief = ChainThief {
        chain_of: &f.device,
        key_of: &other,
    };
    assert_eq!(
        connect(&f, &thief).unwrap_err(),
        PqLinkError::BadDeviceSignature
    );
}

#[test]
fn client_finished_tamper_and_replay() {
    let f = fixture();
    let (hs, ch) = ClientHandshake::start(f.signer.identity().clone()).unwrap();
    let sh = f.server.handle_hello(&ch).unwrap();
    let (pending, cf) = hs.on_server_hello(&sh, &f.device).unwrap();
    let mut bad = cf.clone();
    let n = bad.len();
    bad[n - 2] ^= 1;
    assert_eq!(
        f.server.handle_finish(&bad).unwrap_err(),
        PqLinkError::Decrypt
    );
    // Buzilgan urinishdan keyin pending sessiya o'chirildi — asl CF ham endi rad.
    assert_eq!(
        f.server.handle_finish(&cf).unwrap_err(),
        PqLinkError::UnknownSession
    );
    drop(pending);

    // Muvaffaqiyatli handshake'dan keyin CF takrori sessiyani buzmaydi.
    let (hs, ch) = ClientHandshake::start(f.signer.identity().clone()).unwrap();
    let sh = f.server.handle_hello(&ch).unwrap();
    let (pending, cf) = hs.on_server_hello(&sh, &f.device).unwrap();
    let (_, sa) = f.server.handle_finish(&cf).unwrap();
    assert_eq!(
        f.server.handle_finish(&cf).unwrap_err(),
        PqLinkError::UnexpectedMessage
    );
    let mut c = pending.on_accept(&sa).unwrap();
    f.server.open(&c.seal(b"ok").unwrap()).unwrap();
}

#[test]
fn sessions_expire() {
    let f = fixture();
    let mut c = connect(&f, &f.device).unwrap();
    f.clock.advance(Duration::minutes(16));
    assert_eq!(
        f.server.open(&c.seal(b"x").unwrap()).unwrap_err(),
        PqLinkError::UnknownSession
    );

    // Yakunlanmagan handshake 60 s dan keyin yaroqsiz.
    let (hs, ch) = ClientHandshake::start(f.signer.identity().clone()).unwrap();
    let sh = f.server.handle_hello(&ch).unwrap();
    let (_p, cf) = hs.on_server_hello(&sh, &f.device).unwrap();
    f.clock.advance(Duration::seconds(61));
    assert_eq!(
        f.server.handle_finish(&cf).unwrap_err(),
        PqLinkError::UnknownSession
    );
    let _ = f.clock.unix();
}

#[test]
fn session_limit_enforced() {
    let f = fixture_with(ServerConfig {
        max_sessions: 2,
        ..ServerConfig::default()
    });
    connect(&f, &f.device).unwrap();
    connect(&f, &f.device).unwrap();
    assert_eq!(
        connect(&f, &f.device).unwrap_err(),
        PqLinkError::TooManySessions
    );
    // Muddati o'tganlar tozalanadi.
    f.clock.advance(Duration::minutes(20));
    assert!(connect(&f, &f.device).is_ok());
}

#[test]
fn pending_handshake_flood_is_capped() {
    let f = fixture_with(ServerConfig {
        max_pending: 2,
        ..ServerConfig::default()
    });
    // Faqat hello (finish'siz) — yakunlanmagan handshake'lar chegarasi.
    for _ in 0..2 {
        let (_hs, ch) = ClientHandshake::start(f.signer.identity().clone()).unwrap();
        f.server.handle_hello(&ch).unwrap();
    }
    let (_hs, ch) = ClientHandshake::start(f.signer.identity().clone()).unwrap();
    assert_eq!(
        f.server.handle_hello(&ch).unwrap_err(),
        PqLinkError::TooManySessions
    );
    // Yakunlanmaganlar muddati o'tgach joy bo'shaydi; to'liq handshake ishlaydi.
    f.clock.advance(Duration::minutes(2));
    connect(&f, &f.device).unwrap();
}

#[test]
fn garbage_inputs_are_errors_not_panics() {
    let f = fixture();
    for junk in [&b""[..], b"MPQL", b"MPQL\x01\x01", &[0u8; 2000][..]] {
        assert!(f.server.handle_hello(junk).is_err());
        assert!(f.server.handle_finish(junk).is_err());
        assert!(f.server.open(junk).is_err());
    }
}
