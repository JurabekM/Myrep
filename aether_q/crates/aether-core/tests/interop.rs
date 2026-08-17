//! Profil bo'yicha to'liq round-trip integratsion testlar — spec 6-bo'lim checklist.

use aether_core::combiner::{combine_default, combine_minimal, combine_paranoid};
use aether_core::ratchet::{CompressRecipient, CompressSender};
use aether_core::record::{derive_record_keys, open_record, seal_record};
use aether_primitives::aead::AeadAlgorithm;
use aether_primitives::kem_hqc192::Hqc192Kem;
use aether_primitives::kem_mlkem768::MlKem768Kem;
use aether_primitives::kem_x25519::X25519Kem;
use aether_primitives::Kem;

#[test]
fn default_profile_0x01_end_to_end() {
    let (pk_mlkem, sk_mlkem) = MlKem768Kem::keypair();
    let (pk_x, sk_x) = X25519Kem::keypair();

    // Sender:
    let (ct_mlkem, ss_mlkem_send) = MlKem768Kem::encapsulate(&pk_mlkem).unwrap();
    let (ct_x, ss_x_send) = X25519Kem::encapsulate(&pk_x).unwrap();
    let ss_sender = combine_default(&ss_mlkem_send, &ss_x_send, &ct_x, &pk_x);

    // Recipient:
    let ss_mlkem_recv = MlKem768Kem::decapsulate(&sk_mlkem, &ct_mlkem).unwrap();
    let ss_x_recv = X25519Kem::decapsulate(&sk_x, &ct_x).unwrap();
    let ss_recipient = combine_default(&ss_mlkem_recv, &ss_x_recv, &ct_x, &pk_x);

    assert_eq!(&*ss_sender, &*ss_recipient);
}

#[test]
fn paranoid_profile_0x02_end_to_end() {
    let (pk_mlkem, sk_mlkem) = MlKem768Kem::keypair();
    let (pk_x, sk_x) = X25519Kem::keypair();
    let (pk_hqc, sk_hqc) = Hqc192Kem::keypair();

    let (ct_mlkem, ss_mlkem_send) = MlKem768Kem::encapsulate(&pk_mlkem).unwrap();
    let (ct_x, ss_x_send) = X25519Kem::encapsulate(&pk_x).unwrap();
    let (ct_hqc, ss_hqc_send) = Hqc192Kem::encapsulate(&pk_hqc).unwrap();
    let ss_sender = combine_paranoid(&ss_mlkem_send, &ss_x_send, &ss_hqc_send, &ct_x, &ct_hqc, &pk_x);

    let ss_mlkem_recv = MlKem768Kem::decapsulate(&sk_mlkem, &ct_mlkem).unwrap();
    let ss_x_recv = X25519Kem::decapsulate(&sk_x, &ct_x).unwrap();
    let ss_hqc_recv = Hqc192Kem::decapsulate(&sk_hqc, &ct_hqc).unwrap();
    let ss_recipient = combine_paranoid(&ss_mlkem_recv, &ss_x_recv, &ss_hqc_recv, &ct_x, &ct_hqc, &pk_x);

    assert_eq!(&*ss_sender, &*ss_recipient);
}

#[test]
fn minimal_profile_0x03_end_to_end() {
    let (pk_mlkem, sk_mlkem) = MlKem768Kem::keypair();

    let (ct_mlkem, ss_send) = MlKem768Kem::encapsulate(&pk_mlkem).unwrap();
    let ss_sender = combine_minimal(&ss_send);

    let ss_recv = MlKem768Kem::decapsulate(&sk_mlkem, &ct_mlkem).unwrap();
    let ss_recipient = combine_minimal(&ss_recv);

    assert_eq!(&*ss_sender, &*ss_recipient);
}

#[test]
fn compress_profile_0x04_ratchet_yields_unique_keys_per_step() {
    let (pk_x, sk_x) = X25519Kem::keypair();
    let session_id = [0xABu8; 8];
    let base_seed = vec![0xCDu8; 32];

    let mut sender = CompressSender::new(session_id, base_seed.clone());
    let mut recipient = CompressRecipient::new(session_id, base_seed);

    let mut secrets = Vec::new();
    for _ in 0..5 {
        let (frame, ss_send) = sender.next_frame::<X25519Kem>(&pk_x).unwrap();
        assert_eq!(frame.len(), 77, "COMPRESS frame to'g'ri 77 bayt bo'lishi SHART");
        let ss_recv = recipient.accept_frame::<X25519Kem>(&frame, &sk_x).unwrap();
        assert_eq!(&*ss_send, &*ss_recv);
        secrets.push(ss_send.to_vec());
    }

    // PQDoubleRatchet: har bir qadam unikal kalit chiqarishi SHART.
    for i in 0..secrets.len() {
        for j in (i + 1)..secrets.len() {
            assert_ne!(secrets[i], secrets[j], "ratchet step {} va {} bir xil kalit chiqardi", i, j);
        }
    }
}

#[test]
fn record_layer_full_handshake_then_data_exchange() {
    let (pk_mlkem, sk_mlkem) = MlKem768Kem::keypair();
    let (pk_x, sk_x) = X25519Kem::keypair();

    let (ct_mlkem, ss_mlkem_send) = MlKem768Kem::encapsulate(&pk_mlkem).unwrap();
    let (ct_x, ss_x_send) = X25519Kem::encapsulate(&pk_x).unwrap();
    let ss_client = combine_default(&ss_mlkem_send, &ss_x_send, &ct_x, &pk_x);

    let ss_mlkem_recv = MlKem768Kem::decapsulate(&sk_mlkem, &ct_mlkem).unwrap();
    let ss_x_recv = X25519Kem::decapsulate(&sk_x, &ct_x).unwrap();
    let ss_server = combine_default(&ss_mlkem_recv, &ss_x_recv, &ct_x, &pk_x);
    assert_eq!(&*ss_client, &*ss_server);

    let client_keys = derive_record_keys(&ss_client);
    let server_keys = derive_record_keys(&ss_server);
    let session_id = [0x11u8; 8];

    let frame = seal_record(
        AeadAlgorithm::ChaCha20Poly1305,
        &client_keys.c2s,
        0x01,
        session_id,
        1,
        b"salom, AETHER-Q!",
    )
    .unwrap();

    let (counter, plaintext) =
        open_record(AeadAlgorithm::ChaCha20Poly1305, &server_keys.c2s, 0x01, session_id, &frame).unwrap();
    assert_eq!(counter, 1);
    assert_eq!(plaintext, b"salom, AETHER-Q!");
}
