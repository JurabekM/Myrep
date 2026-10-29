//! Sintetik hodisalar oqimi (`shield-ml/generate.py`) — CSV o'qish va dvigatel orqali o'tkazish.
//!
//! Ustunlar: `ts,kind,device,card,merchant,country,amount_minor,cdcvm,attestation,label,scenario`.
//! `device`/`card` — sintetik satr ID'lar; dvigatelga `SHA-256(satr)` sifatida beriladi.

use sha2::{Digest, Sha256};

use crate::features::{ProvisionEvent, TxnEvent};

/// Hodisa turi.
#[derive(Debug, Clone)]
pub enum EventKind {
    Txn(TxnEvent),
    Provision(ProvisionEvent),
}

/// Belgilangan hodisa.
#[derive(Debug, Clone)]
pub struct LabeledEvent {
    pub kind: EventKind,
    pub label: u8,
    pub scenario: String,
}

fn id32(s: &str) -> [u8; 32] {
    Sha256::digest(s.as_bytes()).into()
}

/// CSV matnidan hodisalar (sarlavha qatori kutiladi).
pub fn parse_events(
    text: &str,
    is_p2p: impl Fn(&str) -> bool,
) -> Result<Vec<LabeledEvent>, String> {
    let mut lines = text.lines();
    let header = lines.next().ok_or("bo'sh CSV")?;
    if header.trim()
        != "ts,kind,device,card,merchant,country,amount_minor,cdcvm,attestation,label,scenario"
    {
        return Err(format!("kutilmagan sarlavha: {header}"));
    }
    let mut out = Vec::new();
    for (i, line) in lines.enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let c: Vec<&str> = line.split(',').collect();
        if c.len() != 11 {
            return Err(format!("{}-qator: 11 ustun kutilgan", i + 2));
        }
        let num = |s: &str| {
            s.parse::<i64>()
                .map_err(|_| format!("{}-qator: son kutilgan: {s}", i + 2))
        };
        let at = num(c[0])?;
        let device = id32(c[2]);
        let card = id32(c[3]);
        let kind = match c[1] {
            "txn" => EventKind::Txn(TxnEvent {
                at,
                device,
                card,
                merchant: c[4].to_owned(),
                country: num(c[5])? as u16,
                amount_minor: num(c[6])? as u64,
                cdcvm: c[7] == "1",
                is_p2p: is_p2p(c[4]),
            }),
            "provision" => EventKind::Provision(ProvisionEvent {
                at,
                device,
                card,
                attestation_level: num(c[8])? as u8,
                existing_tokens_for_pan: 0,
                existing_tokens_for_device: 0,
                integrity: None,
            }),
            k => return Err(format!("{}-qator: noma'lum tur {k}", i + 2)),
        };
        out.push(LabeledEvent {
            kind,
            label: num(c[9])? as u8,
            scenario: c[10].trim().to_owned(),
        });
    }
    Ok(out)
}
