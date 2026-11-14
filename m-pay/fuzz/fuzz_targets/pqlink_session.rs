//! PQ Link o'rnatilgan sessiyasi: haqiqiy client yozuviga bit-flip.
//! Invariant: server faqat aynan o'zgarmagan yozuvni qabul qiladi (AEAD + seq + session_id),
//! ochilgan matn asl matnga teng; xato bo'lsa panic yo'q.
#![no_main]

use std::sync::{Arc, Mutex};

use libfuzzer_sys::fuzz_target;
use mpay_common::clock::SystemClock;
use mpay_common::ports::SecurityLevel;
use mpay_crypto::keystore::{KeyKind, KeyLabel, KeyStore, MemoryKeyStore};
use mpay_pqlink::sandbox::{SandboxAttestationCa, SoftDeviceKey};
use mpay_pqlink::{
    ClientHandshake, ClientSession, KeyStoreServerSigner, MlDsaSeedBlob, PqLinkServer,
    ServerConfig, ServerSigner,
};

const PLAINTEXT: &[u8] = b"{\"pan\":\"fuzz\"}";

struct State {
    signer: Arc<KeyStoreServerSigner>,
    server: PqLinkServer,
    device: SoftDeviceKey,
    client: ClientSession,
}

impl State {
    fn new() -> Self {
        let ks: Arc<dyn KeyStore> = Arc::new(MemoryKeyStore::random());
        let kek = KeyLabel::new(KeyLabel::KEK);
        let ed = KeyLabel::new(KeyLabel::SERVER_ED25519);
        ks.ensure_key(&kek, KeyKind::Aes256).expect("KEK");
        ks.ensure_key(&ed, KeyKind::Ed25519).expect("Ed25519");
        let blob = MlDsaSeedBlob::generate(ks.as_ref(), &kek).expect("ML-DSA");
        let signer = Arc::new(KeyStoreServerSigner::new(ks, ed, blob).expect("signer"));
        let ca = SandboxAttestationCa::generate().expect("CA");
        let device = ca
            .issue_device(SecurityLevel::StrongBox, b"enroll")
            .expect("device");
        let server = PqLinkServer::new(
            signer.clone(),
            ca.anchors().expect("anchors"),
            ServerConfig::default(),
            Arc::new(SystemClock),
        );
        let client = Self::connect(&signer, &server, &device);
        Self {
            signer,
            server,
            device,
            client,
        }
    }

    fn connect(
        signer: &KeyStoreServerSigner,
        server: &PqLinkServer,
        device: &SoftDeviceKey,
    ) -> ClientSession {
        let (hs, ch) = ClientHandshake::start(signer.identity().clone()).expect("start");
        let sh = server.handle_hello(&ch).expect("hello");
        let (pending, cf) = hs.on_server_hello(&sh, device).expect("server hello");
        let (_, sa) = server.handle_finish(&cf).expect("finish");
        pending.on_accept(&sa).expect("accept")
    }

    fn reconnect(&mut self) {
        self.server.close(self.client.session_id());
        self.client = Self::connect(&self.signer, &self.server, &self.device);
    }
}

static STATE: Mutex<Option<State>> = Mutex::new(None);

fuzz_target!(|data: &[u8]| {
    let mut guard = STATE.lock().unwrap_or_else(|e| e.into_inner());
    let st = guard.get_or_insert_with(State::new);

    let rec = st.client.seal(PLAINTEXT).expect("seal");
    let mut bad = rec.clone();
    for pair in data.chunks_exact(3) {
        let i = usize::from(u16::from_le_bytes([pair[0], pair[1]])) % bad.len();
        bad[i] ^= pair[2];
    }
    // Qolgan bayt(lar) uzunlikni o'zgartiradi: kesish yoki qo'shish.
    match data.len() % 3 {
        1 => bad.truncate(bad.len().saturating_sub(usize::from(data[data.len() - 1]))),
        2 => bad.extend_from_slice(&data[data.len() - 2..]),
        _ => {}
    }

    match st.server.open(&bad) {
        Ok((_, pt)) => {
            assert_eq!(bad, rec, "o'zgartirilgan yozuv qabul qilindi");
            assert_eq!(&pt[..], PLAINTEXT);
        }
        Err(_) => {
            assert_ne!(bad, rec, "buzilmagan yozuv rad etildi");
            // Client seq oldinga ketdi yoki server sessiyani yopdi — yangi sessiya.
            st.reconnect();
        }
    }
});
