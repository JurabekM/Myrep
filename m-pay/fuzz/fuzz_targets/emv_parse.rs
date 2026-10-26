//! EMV profil parserlari: PDOL ma'lumoti, Track 2, IAD.
#![no_main]

use libfuzzer_sys::fuzz_target;
use mpay_common::emv::{Iad, TerminalData, Track2};

fuzz_target!(|data: &[u8]| {
    if let Ok(t) = TerminalData::from_pdol_data(data) {
        assert_eq!(t.to_pdol_data().ok().as_ref().map(|d| &d[..]), Some(data));
    }
    let _ = Track2::from_emv(data);
    if let Ok(s) = std::str::from_utf8(data) {
        let _ = Track2::from_iso(s);
    }
    let _ = Iad::from_bytes(data);
});
