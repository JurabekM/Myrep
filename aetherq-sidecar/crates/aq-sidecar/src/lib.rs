//! aq-sidecar kutubxonasi: AETHER-Q tunel runtime'i (CLI `aq-sidecar` va GUI `aq-studio` uchun umumiy).

pub mod runtime;

pub use runtime::{
    cache_key, explain_alert, explain_io, hint_for, null_sink, short_fp, ConnectOptions, Event, ServeOptions, Sink,
    Stats, StatsSnapshot, Tunnel,
};
