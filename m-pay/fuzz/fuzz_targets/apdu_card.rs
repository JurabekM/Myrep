//! Soft-karta applet'i (M-Pay Test Scheme): ixtiyoriy C-APDU ketma-ketligi.
//! Invariantlar: panic yo'q; har javob ≥ 2 bayt; ATC kamaymaydi; `9000` bilan GPO javobi —
//! bitta `77` shabloni; muvaffaqiyatli GPO soni LUK limitidan (2) oshmaydi; CDCVM limitidan
//! katta summa biometriyasiz o'tmaydi.
#![no_main]

use libfuzzer_sys::fuzz_target;
use mpay_common::emv;
use mpay_common::ids::TokenId;
use mpay_common::pan::{CardExpiry, Pan};
use mpay_common::tlv;
use mpay_crypto::SecretKey16;
use mpay_terminal_sim::apdu::{ApduHandler, Command};
use mpay_terminal_sim::card::{CardLuk, CardPolicy, CardProfile, SoftCard};

const MAX_USES: u32 = 2;

fn card() -> SoftCard {
    let p = CardProfile {
        token_id: TokenId::from_random([1; 16]),
        dpan: Pan::from_prefix("990077000000123").expect("DPAN"),
        expiry: CardExpiry::new(2029, 12).expect("muddat"),
        psn: 0,
        luks: vec![CardLuk {
            seq: 1,
            key: SecretKey16::from_bytes([7; 16]),
            expires_at: i64::MAX,
            uses_left: MAX_USES,
        }],
        atc: 0,
    };
    SoftCard::new(p, CardPolicy::default()).with_clock(|| 1_790_000_000)
}

fuzz_target!(|data: &[u8]| {
    let Some((&flags, mut rest)) = data.split_first() else {
        return;
    };
    let mut c = card();
    // Chuqurroq holatlarga tezroq yetish: oldindan SELECT AID va/yoki CDCVM.
    if flags & 1 != 0 {
        c.process(&Command::select(&emv::AID).to_bytes());
    }
    let cdcvm = flags & 2 != 0;
    c.set_cdcvm_verified(cdcvm);

    let mut atc = 0u16;
    let mut approved = 0u32;
    let mut steps = 0;
    while let Some((&len, tail)) = rest.split_first() {
        let n = usize::from(len).min(tail.len());
        let (capdu, next) = tail.split_at(n);
        rest = next;

        let r = c.process(capdu);
        assert!(r.len() >= 2, "R-APDU holat so'zisiz");
        let sw = u16::from_be_bytes([r[r.len() - 2], r[r.len() - 1]]);
        let is_gpo = capdu.len() >= 2 && capdu[0] == 0x80 && capdu[1] == 0xA8;
        if sw == 0x9000 && is_gpo {
            approved += 1;
            let t = tlv::parse_all(&r[..r.len() - 2]).expect("GPO javobi TLV emas");
            assert_eq!(t.len(), 1, "GPO javobida bitta shablon");
            assert_eq!(t[0].tag.0, 0x77, "GPO javobi 77 shabloni emas");
            // Summa PDOL ma'lumotining boshida (9F02, 6 bayt BCD): GPO buyrug'ida 83 L <data>.
            if capdu.len() >= 7 + 6 && !cdcvm {
                if let Ok(amount) = emv::from_bcd(&capdu[7..13]) {
                    assert!(amount <= 100_000_000, "CDCVM'siz katta summa o'tdi");
                }
            }
        }
        let p = c.profile();
        assert!(p.atc >= atc, "ATC kamaydi");
        atc = p.atc;
        assert!(approved <= MAX_USES, "LUK limitidan ko'p GPO");
        steps += 1;
        if steps >= 64 {
            break;
        }
    }
});
