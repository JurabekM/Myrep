//! BER-TLV parser: panic bo'lmasligi va qayta kodlash barqarorligi.
#![no_main]

use libfuzzer_sys::fuzz_target;
use mpay_common::tlv;

fuzz_target!(|data: &[u8]| {
    if let Ok(list) = tlv::parse_all(data) {
        // Minimal kodlash qayta o'qilganda aynan shu daraxtni berishi shart.
        let re = tlv::encode_all(&list);
        assert_eq!(tlv::parse_all(&re).as_ref(), Ok(&list));
    }
    let _ = tlv::parse_dol(data);
});
