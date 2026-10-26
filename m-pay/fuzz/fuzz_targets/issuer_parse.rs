//! Emitent `0100` tahlilchisi (`mpay_issuer::validate_request`): ISO 8583 → Track 2 → ICC (maydon 55)
//! → PDOL ↔ maydon 4/49. Uch rejim: ixtiyoriy baytlar; haqiqiy xabarda maydon 55 almashtiriladi;
//! haqiqiy xabarga bit-flip. Invariant: panic yo'q, buzilmagan haqiqiy xabar har doim o'tadi.
#![no_main]

use std::sync::OnceLock;

use libfuzzer_sys::fuzz_target;
use mpay_common::emv::Track2;
use mpay_common::ids::TokenId;
use mpay_common::iso8583::{IsoMessage, Mti};
use mpay_common::pan::{CardExpiry, Pan};
use mpay_common::tlv;
use mpay_crypto::SecretKey16;
use mpay_issuer::validate_request;
use mpay_terminal_sim::apdu::Loopback;
use mpay_terminal_sim::card::{CardLuk, CardPolicy, CardProfile, SoftCard};
use mpay_terminal_sim::terminal::{tap, TxnParams};

const AMOUNT: u64 = 1_250_000;

/// Soft-karta + terminal yadrosi bilan yig'ilgan haqiqiy `0100` (acquirer bilan bir xil maydonlar).
fn base() -> &'static (IsoMessage, Vec<u8>) {
    static B: OnceLock<(IsoMessage, Vec<u8>)> = OnceLock::new();
    B.get_or_init(|| {
        let dpan = Pan::from_prefix("990077000000123").expect("DPAN");
        let expiry = CardExpiry::new(2029, 12).expect("muddat");
        let mut card = SoftCard::new(
            CardProfile {
                token_id: TokenId::from_random([1; 16]),
                dpan: dpan.clone(),
                expiry,
                psn: 0,
                luks: vec![CardLuk {
                    seq: 1,
                    key: SecretKey16::from_bytes([7; 16]),
                    expires_at: i64::MAX,
                    uses_left: 5,
                }],
                atc: 0,
            },
            CardPolicy::default(),
        );
        let icc = tap(&mut Loopback::new(&mut card), &TxnParams::purchase(AMOUNT))
            .expect("tap")
            .icc;
        let mut m = IsoMessage::new(Mti::AUTH_REQUEST);
        let t2 = Track2::new(dpan.clone(), expiry);
        m.set_str(2, dpan.expose_digits()).expect("2");
        m.set_str(3, "000000").expect("3");
        m.set_num(4, AMOUNT).expect("4");
        m.set_str(7, "1024120000").expect("7");
        m.set_num(11, 1).expect("11");
        m.set_str(14, &expiry.to_yymm()).expect("14");
        m.set_str(22, "071").expect("22");
        m.set_str(35, &t2.to_iso()).expect("35");
        m.set_str(37, "629700000001").expect("37");
        m.set_str(41, "TERM0001").expect("41");
        m.set_str(42, "SHOP00000000001").expect("42");
        m.set_num(49, 860).expect("49");
        m.set(55, tlv::encode_all(&icc)).expect("55");
        assert_eq!(validate_request(&m), Ok(()), "asosiy xabar yaroqli bo'lishi shart");
        let packed = m.pack();
        (m, packed)
    })
}

fuzz_target!(|data: &[u8]| {
    let Some((&mode, rest)) = data.split_first() else {
        return;
    };
    let (msg, packed) = base();
    match mode % 3 {
        0 => {
            if let Ok(m) = IsoMessage::unpack(rest) {
                let _ = validate_request(&m);
            }
        }
        1 => {
            let mut m = msg.clone();
            if m.set(55, rest.to_vec()).is_ok() {
                let _ = validate_request(&m);
            }
        }
        _ => {
            let mut b = packed.clone();
            for pair in rest.chunks_exact(3) {
                let i = usize::from(u16::from_le_bytes([pair[0], pair[1]])) % b.len();
                b[i] ^= pair[2];
            }
            if let Ok(m) = IsoMessage::unpack(&b) {
                let r = validate_request(&m);
                if &b == packed {
                    assert_eq!(r, Ok(()));
                }
            }
        }
    }
});
