//! HTTP API (`mpay-server` router'i, jarayon ichida): ochiq so'rovlar va haqiqiy PQ Link sessiyasi bilan
//! muhrlangan ixtiyoriy JSON. Kirish formati va invariantlar — `mpay_e2e::apifuzz`: panic yo'q,
//! `500` yo'q, xato shartnomasi (`{"error": {"code"}}`) va muhrlangan konvert saqlanadi.
#![no_main]

use std::sync::LazyLock;

use libfuzzer_sys::fuzz_target;
use mpay_e2e::apifuzz::ApiHarness;

static H: LazyLock<ApiHarness> = LazyLock::new(ApiHarness::new);

fuzz_target!(|data: &[u8]| {
    let _ = H.run(data);
});
