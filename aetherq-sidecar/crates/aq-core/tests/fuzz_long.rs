//! Uzun handshake fuzz (state mashinasi): buzilgan CH / CKX-flight / SF kirishlari panic qilmasligi shart.
//! ML-KEM keygen har iteratsiyada bo'lgani uchun iteratsiya soni kam (30 000).
//! Ishga tushirish: cargo test --release -p aq-core --test fuzz_long -- --ignored --nocapture

mod common {
    include!("fuzz_common.rs");
}

use aq_core::handshake::{ClientConfig, ClientHs, ServerConfig, ServerHs};
use aq_core::Identity;
use common::{mutate, Lcg};

#[test]
#[ignore]
fn long_handshake_state_fuzz_30k() {
    let srv = Identity::from_seed([61; 32]);
    let mut c = ClientHs::new(ClientConfig::default());
    let ch = c.start().unwrap();
    let mut s0 = ServerHs::new(ServerConfig { identity: Some(srv.clone()), ..Default::default() });
    let sh = s0.recv_hello(&ch, None).unwrap().into_bytes();
    let flight = c.recv(&sh).unwrap().unwrap();
    let total = 30_000usize;
    let mut rng = Lcg(0xC0FFEE);
    let mut panics = 0usize;
    let mut ok_connects = 0usize;
    for i in 0..total {
        let r = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let mut s = ServerHs::new(ServerConfig { identity: Some(srv.clone()), ..Default::default() });
            let mutated_ch = if i % 3 == 0 { mutate(&mut rng, &ch) } else { ch.clone() };
            let _ = s.recv_hello(&mutated_ch, None);
            let m = mutate(&mut rng, &flight);
            s.recv_flight(&m).is_ok()
        }));
        match r {
            Ok(true) => ok_connects += 1,
            Ok(false) => {}
            Err(_) => panics += 1,
        }
    }
    println!("long_handshake_state_fuzz_30k: {total} holat, panic={panics}, muvaffaqiyatli_ulanish={ok_connects}");
    assert_eq!(panics, 0, "handshake state mashinasida panic");
}
