//! PQ Link xabar dekoderlari va attestatsiya tahlilchisi: panic bo'lmasligi, roundtrip.
#![no_main]

use libfuzzer_sys::fuzz_target;
use mpay_pqlink::attestation::parse_key_description;
use mpay_pqlink::wire::{ClientFinishedInner, ClientHello, MsgType, Sealed, ServerAcceptInner, ServerHello};

fuzz_target!(|data: &[u8]| {
    if let Ok(ch) = ClientHello::decode(data) {
        assert_eq!(ch.encode().ok().as_deref(), Some(data));
    }
    if let Ok((sh, _)) = ServerHello::decode(data) {
        assert_eq!(sh.encode().ok().as_deref(), Some(data));
    }
    for kind in [MsgType::ClientFinished, MsgType::ServerAccept, MsgType::Record] {
        if let Ok(s) = Sealed::decode(data, kind) {
            assert_eq!(s.encode(), data);
        }
    }
    if let Ok(cf) = ClientFinishedInner::decode(data) {
        assert_eq!(cf.encode().ok().as_deref(), Some(data));
    }
    let _ = ServerAcceptInner::decode(data);
    let _ = parse_key_description(data);
});
