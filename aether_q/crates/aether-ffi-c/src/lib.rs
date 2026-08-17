#![allow(clippy::missing_safety_doc)] // barcha funksiyalar FFI chegarasi bo'ylab unsafe — xavfsizlik shartlari yagona: to'g'ri ptr+len juftliklari uzatilishi.
//! Raw C ABI — .NET/C# (yoki boshqa har qanday P/Invoke-mos til) uchun.
//!
//! UniFFI'dan farqli o'laroq bu qatlam qo'lda yozilgan, oddiy `extern "C"`
//! funksiyalar orqali ishlaydi: kirish baytlari ptr+len juftligi sifatida,
//! chiqish baytlari esa chaqiruvchi `aether_free_buffer` bilan tozalashi
//! kerak bo'lgan `ByteBuffer` sifatida uzatiladi. Barcha protokol mantig'i
//! `aether-core`dan qayta ishlatiladi — bu yerda yangi kripto yozilmagan.

use aether_core::akem;
use aether_core::ratchet::{CompressRecipient, CompressSender};
use aether_core::record;
use aether_primitives::aead::AeadAlgorithm;
use aether_primitives::hash::shake256_concat;
use aether_primitives::kem_mlkem768::MlKem768Kem;
use aether_primitives::kem_x25519::X25519Kem;
use aether_primitives::rng::random_bytes;
use aether_primitives::sig_ed25519::Ed25519Signer;
use aether_primitives::{Kem, Signer};
use std::os::raw::c_int;
use std::slice;
use std::sync::Mutex;

/// Rust tomonidan ajratilgan bayt buferi. Chaqiruvchi tomon `aether_free_buffer`
/// orqali tozalashi SHART (aks holda xotira sizib chiqadi).
#[repr(C)]
pub struct ByteBuffer {
    pub ptr: *mut u8,
    pub len: usize,
}

impl ByteBuffer {
    fn from_vec(mut v: Vec<u8>) -> Self {
        let ptr = v.as_mut_ptr();
        let len = v.len();
        std::mem::forget(v);
        ByteBuffer { ptr, len }
    }

    fn empty() -> Self {
        ByteBuffer { ptr: std::ptr::null_mut(), len: 0 }
    }
}

#[no_mangle]
pub unsafe extern "C" fn aether_free_buffer(buf: ByteBuffer) {
    if !buf.ptr.is_null() {
        drop(Vec::from_raw_parts(buf.ptr, buf.len, buf.len));
    }
}

unsafe fn borrow<'a>(ptr: *const u8, len: usize) -> &'a [u8] {
    if len == 0 {
        &[]
    } else {
        slice::from_raw_parts(ptr, len)
    }
}

// ---------------------------------------------------------------------------
// Identity kalitlari
// ---------------------------------------------------------------------------

#[no_mangle]
pub unsafe extern "C" fn aether_generate_x25519_keypair(out_pk: *mut ByteBuffer, out_sk: *mut ByteBuffer) {
    let (pk, sk) = X25519Kem::keypair();
    *out_pk = ByteBuffer::from_vec(pk);
    *out_sk = ByteBuffer::from_vec(sk.to_vec());
}

#[no_mangle]
pub unsafe extern "C" fn aether_generate_mlkem768_keypair(out_pk: *mut ByteBuffer, out_sk: *mut ByteBuffer) {
    let (pk, sk) = MlKem768Kem::keypair();
    *out_pk = ByteBuffer::from_vec(pk);
    *out_sk = ByteBuffer::from_vec(sk.to_vec());
}

#[no_mangle]
pub unsafe extern "C" fn aether_generate_ed25519_keypair(out_pk: *mut ByteBuffer, out_sk: *mut ByteBuffer) {
    let (pk, sk) = Ed25519Signer::keypair();
    *out_pk = ByteBuffer::from_vec(pk);
    *out_sk = ByteBuffer::from_vec(sk.to_vec());
}

#[no_mangle]
pub unsafe extern "C" fn aether_generate_random_bytes(len: usize, out: *mut ByteBuffer) {
    *out = ByteBuffer::from_vec(random_bytes(len));
}

/// `SHAKE-256(input || label)` — Compress-KEM `base_seed`/`session_id` hosil qilish uchun.
#[no_mangle]
pub unsafe extern "C" fn aether_derive_bytes(
    input_ptr: *const u8,
    input_len: usize,
    label_ptr: *const u8,
    label_len: usize,
    out_len: usize,
    out: *mut ByteBuffer,
) {
    let input = borrow(input_ptr, input_len);
    let label = borrow(label_ptr, label_len);
    *out = ByteBuffer::from_vec(shake256_concat(&[input, label], out_len));
}

// ---------------------------------------------------------------------------
// AUTH-AKEM (0x05)
// ---------------------------------------------------------------------------

#[repr(C)]
pub struct AkemEncapsulationResult {
    pub ct_mlkem: ByteBuffer,
    pub ct_x25519: ByteBuffer,
    pub signature: ByteBuffer,
    pub shared_secret: ByteBuffer,
}

/// 0 — muvaffaqiyat, manfiy qiymat — xato (`out` bo'sh buferlar bilan to'ldiriladi).
#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn aether_akem_encapsulate(
    pk_recip_mlkem_ptr: *const u8,
    pk_recip_mlkem_len: usize,
    pk_recip_x25519_ptr: *const u8,
    pk_recip_x25519_len: usize,
    sk_sender_sign_ptr: *const u8,
    sk_sender_sign_len: usize,
    pk_sender_sign_ptr: *const u8,
    pk_sender_sign_len: usize,
    pk_recip_sign_ptr: *const u8,
    pk_recip_sign_len: usize,
    out: *mut AkemEncapsulationResult,
) -> c_int {
    let pk_recip_mlkem = borrow(pk_recip_mlkem_ptr, pk_recip_mlkem_len);
    let pk_recip_x25519 = borrow(pk_recip_x25519_ptr, pk_recip_x25519_len);
    let sk_sender_sign = borrow(sk_sender_sign_ptr, sk_sender_sign_len);
    let pk_sender_sign = borrow(pk_sender_sign_ptr, pk_sender_sign_len);
    let pk_recip_sign = borrow(pk_recip_sign_ptr, pk_recip_sign_len);

    match akem::encapsulate::<MlKem768Kem, X25519Kem, Ed25519Signer>(
        pk_recip_mlkem,
        pk_recip_x25519,
        sk_sender_sign,
        pk_sender_sign,
        pk_recip_sign,
    ) {
        Ok((ct_mlkem, ct_x25519, signature, shared_secret)) => {
            *out = AkemEncapsulationResult {
                ct_mlkem: ByteBuffer::from_vec(ct_mlkem),
                ct_x25519: ByteBuffer::from_vec(ct_x25519),
                signature: ByteBuffer::from_vec(signature),
                shared_secret: ByteBuffer::from_vec(shared_secret.to_vec()),
            };
            0
        }
        Err(_) => {
            *out = AkemEncapsulationResult {
                ct_mlkem: ByteBuffer::empty(),
                ct_x25519: ByteBuffer::empty(),
                signature: ByteBuffer::empty(),
                shared_secret: ByteBuffer::empty(),
            };
            -1
        }
    }
}

/// Imzo yaroqsiz bo'lsa ham xato qaytmaydi — Implicit Rejection natijasi qaytadi
/// (S1/S2, `aether_core::akem` qarang).
#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn aether_akem_decapsulate(
    sk_recip_mlkem_ptr: *const u8,
    sk_recip_mlkem_len: usize,
    sk_recip_x25519_ptr: *const u8,
    sk_recip_x25519_len: usize,
    pk_recip_x25519_ptr: *const u8,
    pk_recip_x25519_len: usize,
    z_recip_ptr: *const u8,
    z_recip_len: usize,
    pk_sender_sign_ptr: *const u8,
    pk_sender_sign_len: usize,
    pk_recip_sign_ptr: *const u8,
    pk_recip_sign_len: usize,
    ct_mlkem_ptr: *const u8,
    ct_mlkem_len: usize,
    ct_x25519_ptr: *const u8,
    ct_x25519_len: usize,
    signature_ptr: *const u8,
    signature_len: usize,
    out: *mut ByteBuffer,
) {
    let sk_recip_mlkem = borrow(sk_recip_mlkem_ptr, sk_recip_mlkem_len);
    let sk_recip_x25519 = borrow(sk_recip_x25519_ptr, sk_recip_x25519_len);
    let pk_recip_x25519 = borrow(pk_recip_x25519_ptr, pk_recip_x25519_len);
    let z_recip = borrow(z_recip_ptr, z_recip_len);
    let pk_sender_sign = borrow(pk_sender_sign_ptr, pk_sender_sign_len);
    let pk_recip_sign = borrow(pk_recip_sign_ptr, pk_recip_sign_len);
    let ct_mlkem = borrow(ct_mlkem_ptr, ct_mlkem_len);
    let ct_x25519 = borrow(ct_x25519_ptr, ct_x25519_len);
    let signature = borrow(signature_ptr, signature_len);

    let ss = akem::decapsulate::<MlKem768Kem, X25519Kem, Ed25519Signer>(
        sk_recip_mlkem,
        sk_recip_x25519,
        pk_recip_x25519,
        z_recip,
        pk_sender_sign,
        pk_recip_sign,
        ct_mlkem,
        ct_x25519,
        signature,
    );
    *out = ByteBuffer::from_vec(ss.to_vec());
}

// ---------------------------------------------------------------------------
// Compress-KEM (0x04) ratchet — opaque handle'lar
// ---------------------------------------------------------------------------

#[repr(C)]
pub struct CompressFrameResultC {
    pub frame: ByteBuffer,
    pub shared_secret: ByteBuffer,
}

#[no_mangle]
pub unsafe extern "C" fn aether_compress_sender_new(
    session_id_ptr: *const u8,
    session_id_len: usize,
    base_seed_ptr: *const u8,
    base_seed_len: usize,
) -> *mut Mutex<CompressSender> {
    let session_id = borrow(session_id_ptr, session_id_len);
    if session_id.len() != 8 {
        return std::ptr::null_mut();
    }
    let mut sid = [0u8; 8];
    sid.copy_from_slice(session_id);
    let base_seed = borrow(base_seed_ptr, base_seed_len).to_vec();
    Box::into_raw(Box::new(Mutex::new(CompressSender::new(sid, base_seed))))
}

#[no_mangle]
pub unsafe extern "C" fn aether_compress_sender_free(handle: *mut Mutex<CompressSender>) {
    if !handle.is_null() {
        drop(Box::from_raw(handle));
    }
}

#[no_mangle]
pub unsafe extern "C" fn aether_compress_sender_next_frame(
    handle: *mut Mutex<CompressSender>,
    recipient_pk_x25519_ptr: *const u8,
    recipient_pk_x25519_len: usize,
    out: *mut CompressFrameResultC,
) -> c_int {
    let recipient_pk = borrow(recipient_pk_x25519_ptr, recipient_pk_x25519_len);
    let mut guard = (*handle).lock().unwrap();
    match guard.next_frame::<X25519Kem>(recipient_pk) {
        Ok((frame, ss)) => {
            *out = CompressFrameResultC {
                frame: ByteBuffer::from_vec(frame.to_vec()),
                shared_secret: ByteBuffer::from_vec(ss.to_vec()),
            };
            0
        }
        Err(_) => {
            *out = CompressFrameResultC { frame: ByteBuffer::empty(), shared_secret: ByteBuffer::empty() };
            -1
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn aether_compress_recipient_new(
    session_id_ptr: *const u8,
    session_id_len: usize,
    base_seed_ptr: *const u8,
    base_seed_len: usize,
) -> *mut Mutex<CompressRecipient> {
    let session_id = borrow(session_id_ptr, session_id_len);
    if session_id.len() != 8 {
        return std::ptr::null_mut();
    }
    let mut sid = [0u8; 8];
    sid.copy_from_slice(session_id);
    let base_seed = borrow(base_seed_ptr, base_seed_len).to_vec();
    Box::into_raw(Box::new(Mutex::new(CompressRecipient::new(sid, base_seed))))
}

#[no_mangle]
pub unsafe extern "C" fn aether_compress_recipient_free(handle: *mut Mutex<CompressRecipient>) {
    if !handle.is_null() {
        drop(Box::from_raw(handle));
    }
}

#[no_mangle]
pub unsafe extern "C" fn aether_compress_recipient_accept_frame(
    handle: *mut Mutex<CompressRecipient>,
    frame_ptr: *const u8,
    frame_len: usize,
    sk_x25519_ptr: *const u8,
    sk_x25519_len: usize,
    out: *mut ByteBuffer,
) -> c_int {
    let frame = borrow(frame_ptr, frame_len);
    let sk_x25519 = borrow(sk_x25519_ptr, sk_x25519_len);
    let mut guard = (*handle).lock().unwrap();
    match guard.accept_frame::<X25519Kem>(frame, sk_x25519) {
        Ok(ss) => {
            *out = ByteBuffer::from_vec(ss.to_vec());
            0
        }
        Err(_) => {
            *out = ByteBuffer::empty();
            -1
        }
    }
}

// ---------------------------------------------------------------------------
// Record layer (7-bo'lim)
// ---------------------------------------------------------------------------

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn aether_seal_record(
    profile_id: u8,
    shared_secret_ptr: *const u8,
    shared_secret_len: usize,
    session_id_ptr: *const u8,
    session_id_len: usize,
    is_client_to_server: u8,
    counter: u32,
    plaintext_ptr: *const u8,
    plaintext_len: usize,
    out: *mut ByteBuffer,
) -> c_int {
    let shared_secret = borrow(shared_secret_ptr, shared_secret_len);
    let session_id = borrow(session_id_ptr, session_id_len);
    let plaintext = borrow(plaintext_ptr, plaintext_len);
    if session_id.len() != 8 {
        *out = ByteBuffer::empty();
        return -1;
    }
    let mut sid = [0u8; 8];
    sid.copy_from_slice(session_id);

    let keys = record::derive_record_keys(shared_secret);
    let dir = if is_client_to_server != 0 { &keys.c2s } else { &keys.s2c };
    match record::seal_record(AeadAlgorithm::ChaCha20Poly1305, dir, profile_id, sid, counter, plaintext) {
        Ok(frame) => {
            *out = ByteBuffer::from_vec(frame);
            0
        }
        Err(_) => {
            *out = ByteBuffer::empty();
            -1
        }
    }
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn aether_open_record(
    profile_id: u8,
    shared_secret_ptr: *const u8,
    shared_secret_len: usize,
    session_id_ptr: *const u8,
    session_id_len: usize,
    is_client_to_server: u8,
    frame_ptr: *const u8,
    frame_len: usize,
    out_counter: *mut u32,
    out: *mut ByteBuffer,
) -> c_int {
    let shared_secret = borrow(shared_secret_ptr, shared_secret_len);
    let session_id = borrow(session_id_ptr, session_id_len);
    let frame = borrow(frame_ptr, frame_len);
    if session_id.len() != 8 {
        *out = ByteBuffer::empty();
        return -1;
    }
    let mut sid = [0u8; 8];
    sid.copy_from_slice(session_id);

    let keys = record::derive_record_keys(shared_secret);
    let dir = if is_client_to_server != 0 { &keys.c2s } else { &keys.s2c };
    match record::open_record(AeadAlgorithm::ChaCha20Poly1305, dir, profile_id, sid, frame) {
        Ok((counter, plaintext)) => {
            *out_counter = counter;
            *out = ByteBuffer::from_vec(plaintext);
            0
        }
        Err(_) => {
            *out_counter = 0;
            *out = ByteBuffer::empty();
            -1
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn akem_and_ratchet_and_record_roundtrip_via_c_abi() {
        unsafe {
            let (mut recip_mlkem_pk, mut recip_mlkem_sk) = (ByteBuffer::empty(), ByteBuffer::empty());
            aether_generate_mlkem768_keypair(&mut recip_mlkem_pk, &mut recip_mlkem_sk);
            let (mut recip_x_pk, mut recip_x_sk) = (ByteBuffer::empty(), ByteBuffer::empty());
            aether_generate_x25519_keypair(&mut recip_x_pk, &mut recip_x_sk);
            let (mut sender_ed_pk, mut sender_ed_sk) = (ByteBuffer::empty(), ByteBuffer::empty());
            aether_generate_ed25519_keypair(&mut sender_ed_pk, &mut sender_ed_sk);
            let (mut recip_ed_pk, mut recip_ed_sk) = (ByteBuffer::empty(), ByteBuffer::empty());
            aether_generate_ed25519_keypair(&mut recip_ed_pk, &mut recip_ed_sk);
            let mut z_recip = ByteBuffer::empty();
            aether_generate_random_bytes(32, &mut z_recip);

            let mut encaps = std::mem::MaybeUninit::<AkemEncapsulationResult>::uninit();
            let rc = aether_akem_encapsulate(
                recip_mlkem_pk.ptr, recip_mlkem_pk.len,
                recip_x_pk.ptr, recip_x_pk.len,
                sender_ed_sk.ptr, sender_ed_sk.len,
                sender_ed_pk.ptr, sender_ed_pk.len,
                recip_ed_pk.ptr, recip_ed_pk.len,
                encaps.as_mut_ptr(),
            );
            assert_eq!(rc, 0);
            let encaps = encaps.assume_init();

            let mut recip_ss = ByteBuffer::empty();
            aether_akem_decapsulate(
                recip_mlkem_sk.ptr, recip_mlkem_sk.len,
                recip_x_sk.ptr, recip_x_sk.len,
                recip_x_pk.ptr, recip_x_pk.len,
                z_recip.ptr, z_recip.len,
                sender_ed_pk.ptr, sender_ed_pk.len,
                recip_ed_pk.ptr, recip_ed_pk.len,
                encaps.ct_mlkem.ptr, encaps.ct_mlkem.len,
                encaps.ct_x25519.ptr, encaps.ct_x25519.len,
                encaps.signature.ptr, encaps.signature.len,
                &mut recip_ss,
            );

            let sender_ss_slice = slice::from_raw_parts(encaps.shared_secret.ptr, encaps.shared_secret.len);
            let recip_ss_slice = slice::from_raw_parts(recip_ss.ptr, recip_ss.len);
            assert_eq!(sender_ss_slice, recip_ss_slice);

            let label = b"test-label";
            let mut base_seed = ByteBuffer::empty();
            aether_derive_bytes(
                encaps.shared_secret.ptr, encaps.shared_secret.len,
                label.as_ptr(), label.len(),
                32,
                &mut base_seed,
            );
            let mut session_id = ByteBuffer::empty();
            aether_derive_bytes(
                encaps.shared_secret.ptr, encaps.shared_secret.len,
                b"session".as_ptr(), 7,
                8,
                &mut session_id,
            );

            let sender_handle = aether_compress_sender_new(session_id.ptr, session_id.len, base_seed.ptr, base_seed.len);
            let recipient_handle =
                aether_compress_recipient_new(session_id.ptr, session_id.len, base_seed.ptr, base_seed.len);
            assert!(!sender_handle.is_null());
            assert!(!recipient_handle.is_null());

            let mut step = std::mem::MaybeUninit::<CompressFrameResultC>::uninit();
            let rc = aether_compress_sender_next_frame(sender_handle, recip_x_pk.ptr, recip_x_pk.len, step.as_mut_ptr());
            assert_eq!(rc, 0);
            let step = step.assume_init();
            assert_eq!(step.frame.len, 77);

            let mut step_ss_recv = ByteBuffer::empty();
            let rc = aether_compress_recipient_accept_frame(
                recipient_handle,
                step.frame.ptr, step.frame.len,
                recip_x_sk.ptr, recip_x_sk.len,
                &mut step_ss_recv,
            );
            assert_eq!(rc, 0);

            let plaintext = b"csharp c-abi smoke test";
            let mut sealed = ByteBuffer::empty();
            let rc = aether_seal_record(
                0x04,
                step.shared_secret.ptr, step.shared_secret.len,
                session_id.ptr, session_id.len,
                1, 1,
                plaintext.as_ptr(), plaintext.len(),
                &mut sealed,
            );
            assert_eq!(rc, 0);

            let mut out_counter: u32 = 0;
            let mut opened = ByteBuffer::empty();
            let rc = aether_open_record(
                0x04,
                step_ss_recv.ptr, step_ss_recv.len,
                session_id.ptr, session_id.len,
                1,
                sealed.ptr, sealed.len,
                &mut out_counter,
                &mut opened,
            );
            assert_eq!(rc, 0);
            assert_eq!(out_counter, 1);
            let opened_slice = slice::from_raw_parts(opened.ptr, opened.len);
            assert_eq!(opened_slice, plaintext);

            aether_compress_sender_free(sender_handle);
            aether_compress_recipient_free(recipient_handle);
            aether_free_buffer(recip_mlkem_pk);
            aether_free_buffer(recip_mlkem_sk);
            aether_free_buffer(recip_x_pk);
            aether_free_buffer(recip_x_sk);
            aether_free_buffer(sender_ed_pk);
            aether_free_buffer(sender_ed_sk);
            aether_free_buffer(recip_ed_pk);
            aether_free_buffer(recip_ed_sk);
            aether_free_buffer(z_recip);
            aether_free_buffer(encaps.ct_mlkem);
            aether_free_buffer(encaps.ct_x25519);
            aether_free_buffer(encaps.signature);
            aether_free_buffer(encaps.shared_secret);
            aether_free_buffer(recip_ss);
            aether_free_buffer(base_seed);
            aether_free_buffer(session_id);
            aether_free_buffer(step.frame);
            aether_free_buffer(step.shared_secret);
            aether_free_buffer(step_ss_recv);
            aether_free_buffer(sealed);
            aether_free_buffer(opened);
        }
    }
}
