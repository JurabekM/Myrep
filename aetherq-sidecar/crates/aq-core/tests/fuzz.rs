//! Mutatsion fuzz (deterministik, LCG): buzilgan handshake/record kiritishlari panic qilmasligi shart.
//! Har bir kirish yo'li faqat `Ok` yoki `Err` qaytaradi — boshqa natija (panic) test xatosi.
//! Uzun rejim (1M holat): `cargo test --release --test fuzz -- --ignored --nocapture`.

use aq_core::handshake::{ClientConfig, ClientHs, ServerConfig, ServerHs};
use aq_core::{Identity, Role, Session};

pub struct Lcg(pub u64);

impl Lcg {
    pub fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        self.0 >> 33
    }
    pub fn below(&mut self, n: usize) -> usize {
        (self.next() as usize) % n.max(1)
    }
}

pub fn mutate(rng: &mut Lcg, data: &[u8]) -> Vec<u8> {
    let mut v = data.to_vec();
    match rng.below(5) {
        0 => {
            if !v.is_empty() {
                let i = rng.below(v.len());
                v[i] ^= 1 << rng.below(8);
            }
        }
        1 => {
            let n = rng.below(v.len() + 1);
            v.truncate(n);
        }
        2 => {
            for _ in 0..(rng.below(8) + 1) {
                v.push(rng.next() as u8);
            }
        }
        3 => {
            if v.len() >= 4 {
                let i = rng.below(v.len() - 3);
                v[i..i + 4].copy_from_slice(&(rng.next() as u32).to_be_bytes());
            }
        }
        _ => {
            // uzunlik maydonini (3-5 baytlar) ataylab buzish
            if v.len() >= 6 {
                v[3..6].copy_from_slice(&[(rng.next() as u8), 0xFF, 0xFF]);
            }
        }
    }
    v
}

const ITER: usize = 1500;

#[test]
fn mutated_client_hello_never_panics() {
    let srv = Identity::from_seed([42; 32]);
    let mut c = ClientHs::new(ClientConfig::default());
    let base = c.start().unwrap();
    let mut rng = Lcg(1);
    for _ in 0..ITER {
        let m = mutate(&mut rng, &base);
        let mut s = ServerHs::new(ServerConfig { identity: Some(srv.clone()), ..Default::default() });
        let _ = s.recv_hello(&m, None);
    }
}

#[test]
fn mutated_server_hello_never_panics() {
    let srv = Identity::from_seed([43; 32]);
    let mut c0 = ClientHs::new(ClientConfig::default());
    let ch = c0.start().unwrap();
    let mut s0 = ServerHs::new(ServerConfig { identity: Some(srv.clone()), ..Default::default() });
    let sh = s0.recv_hello(&ch, None).unwrap().into_bytes();
    let mut rng = Lcg(2);
    for _ in 0..ITER {
        let m = mutate(&mut rng, &sh);
        let mut c = ClientHs::new(ClientConfig { server_pub: Some(srv.pk.clone()), ..Default::default() });
        let _ = c.start().unwrap();
        let _ = c.recv(&m);
    }
}

#[test]
fn mutated_client_flight_never_panics() {
    let srv = Identity::from_seed([44; 32]);
    let mut c = ClientHs::new(ClientConfig::default());
    let ch = c.start().unwrap();
    let mut s0 = ServerHs::new(ServerConfig { identity: Some(srv.clone()), ..Default::default() });
    let sh = s0.recv_hello(&ch, None).unwrap().into_bytes();
    let flight = c.recv(&sh).unwrap().unwrap();
    let mut rng = Lcg(3);
    // Har iteratsiyada ML-KEM keygen + ML-DSA imzo bor: kamroq iteratsiya.
    for _ in 0..ITER / 5 {
        let m = mutate(&mut rng, &flight);
        let mut s = ServerHs::new(ServerConfig { identity: Some(srv.clone()), ..Default::default() });
        let _ = s.recv_hello(&ch, None).unwrap();
        let _ = s.recv_flight(&m);
    }
}

#[test]
fn random_records_never_panic_and_never_authenticate() {
    let master = [7u8; 32];
    let mut srv = Session::from_master(&master, 1, Role::Server);
    let mut cli = Session::from_master(&master, 1, Role::Client);
    let good = cli.seal(b"ok").unwrap();
    assert!(srv.open(&good).is_ok());
    let mut rng = Lcg(4);
    let mut accepted = 0usize;
    for _ in 0..ITER {
        let m = mutate(&mut rng, &good);
        // Qayta-foydalanish: har iteratsiyada yangi qabul qiluvchi sessiya (seq=0).
        let mut s = Session::from_master(&master, 1, Role::Server);
        if s.open(&m).is_ok() && m != good {
            accepted += 1;
        }
    }
    assert_eq!(accepted, 0, "buzilgan record AEAD tekshiruvidan o'tdi");
}

/// Uzun fuzz: 1M parser/record holati (ML-KEM'siz, tez). Ishga tushirish: --ignored.
#[test]
#[ignore]
fn long_parser_fuzz_1m() {
    use aq_core::wire;
    let seeds: Vec<Vec<u8>> = {
        let mut c = ClientHs::new(ClientConfig::default());
        let ch = c.start().unwrap();
        vec![
            ch,
            wire::enc_finished(&[1u8; 32]),
            wire::enc_client_kex(&[2u8; 1088]),
            wire::alert_frame(0x2A),
            wire::enc_nst(&[3u8; 69], 3600),
            wire::enc_hello_retry(&[4u8; 24], 8),
        ]
    };
    let mut rng = Lcg(0xDEADBEEF);
    let mut panics = 0usize;
    let total = 1_000_000usize;
    for i in 0..total {
        let base = &seeds[i % seeds.len()];
        let m = mutate(&mut rng, base);
        let r = std::panic::catch_unwind(|| {
            let _ = wire::parse_exact(&m);
            let _ = wire::parse_frame(&m);
            let _ = wire::dec_client_hello(m.get(6..).unwrap_or(&[]));
            let _ = wire::dec_server_hello(m.get(6..).unwrap_or(&[]));
            let _ = wire::dec_client_kex(m.get(6..).unwrap_or(&[]));
            let _ = wire::dec_client_auth(m.get(6..).unwrap_or(&[]));
            let _ = wire::dec_finished(m.get(6..).unwrap_or(&[]));
            let _ = wire::dec_hello_retry(m.get(6..).unwrap_or(&[]));
            let _ = wire::dec_client_hello_retry(m.get(6..).unwrap_or(&[]));
            let _ = wire::dec_nst(m.get(6..).unwrap_or(&[]));
            let mut s = Session::from_master(&[5u8; 32], 1, Role::Server);
            let _ = s.open(&m);
        });
        if r.is_err() {
            panics += 1;
        }
    }
    println!("long_parser_fuzz_1m: {total} holat, panic={panics}");
    assert_eq!(panics, 0, "parserlarda panic topildi");
}
