//! ISO 8583 unpacker: panic bo'lmasligi va pack(unpack(x)) == x (qat'iy format).
#![no_main]

use libfuzzer_sys::fuzz_target;
use mpay_common::iso8583::IsoMessage;

fuzz_target!(|data: &[u8]| {
    if let Ok(m) = IsoMessage::unpack(data) {
        assert_eq!(m.pack(), data);
    }
});
