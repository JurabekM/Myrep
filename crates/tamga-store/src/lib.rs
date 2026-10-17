//! TAMGA saqlash qatlami: papkalar, maxfiy kalitlar, jurnal va checkpoint fayllari, payload vault.
//!
//! Papka tuzilmasi (`TAMGA_HOME`, odatda `%LOCALAPPDATA%\tamga`):
//!
//! ```text
//! logs/<log>.jsonl          jurnal (TAMGA Record 0.1)
//! logs/<log>.checkpoints    imzolangan checkpoint'lar
//! public-key.json           auditor uchun ochiq kalit
//! vault/<s>.key             sessiya kaliti (master kalit bilan shifrlangan) — o'chirilsa, payload'lar unutiladi
//! vault/<s>.bin             sessiya payload'lari (shifrlangan)
//! spool/*.json              daemon ishlamaganda hook yozib qo'ygan hodisalar
//! witness/                  checkpoint nusxalari (ixtiyoriy tashqi guvoh papkasi)
//! ```

pub mod client;
pub mod export;
pub mod home;
pub mod integrate;
pub mod keystore;
pub mod logfile;
pub mod secrets;
pub mod spool;
pub mod vault;

pub use home::Home;

#[derive(Debug, thiserror::Error)]
pub enum StoreError {
    #[error("{path}: {source}")]
    Io {
        path: String,
        #[source]
        source: std::io::Error,
    },
    #[error("maxfiy kalitlar ombori: {0}")]
    Secret(String),
    #[error("jurnal buzilgan, yozish to'xtatildi: {0}")]
    Corrupt(tamga_core::VerifyError),
    #[error("vault: {0}")]
    Vault(String),
    #[error(transparent)]
    Append(#[from] tamga_core::chain::AppendError),
    #[error(transparent)]
    Checkpoint(#[from] tamga_core::checkpoint::CheckpointError),
}

pub type Result<T> = std::result::Result<T, StoreError>;

pub(crate) fn io_err(path: &std::path::Path) -> impl FnOnce(std::io::Error) -> StoreError + '_ {
    move |source| StoreError::Io {
        path: path.display().to_string(),
        source,
    }
}

/// OS'ning kriptografik tasodifiy manbasidan baytlar.
pub fn random<const N: usize>() -> [u8; N] {
    let mut b = [0u8; N];
    getrandom::fill(&mut b).expect("OS tasodifiy manbasi ishlamadi");
    b
}

/// Hozirgi vaqt spec §2.3 formatida (`YYYY-MM-DDTHH:MM:SS.sssZ`).
pub fn now_ts() -> String {
    let d = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    format_ts(d.as_millis() as i64)
}

/// Unix millisekundlarini UTC vaqt satriga aylantiradi (Howard Hinnant fuqarolik taqvimi algoritmi).
pub fn format_ts(unix_ms: i64) -> String {
    let ms = unix_ms.rem_euclid(1000);
    let secs = unix_ms.div_euclid(1000);
    let (days, sod) = (secs.div_euclid(86_400), secs.rem_euclid(86_400));
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = yoe + era * 400 + i64::from(month <= 2);
    format!(
        "{year:04}-{month:02}-{day:02}T{:02}:{:02}:{:02}.{ms:03}Z",
        sod / 3600,
        sod % 3600 / 60,
        sod % 60
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn timestamps_are_spec_shaped() {
        assert_eq!(format_ts(0), "1970-01-01T00:00:00.000Z");
        assert_eq!(format_ts(951_782_400_123), "2000-02-29T00:00:00.123Z");
        assert_eq!(format_ts(1_792_233_667_118), "2026-10-17T10:41:07.118Z");
        assert!(tamga_core::record::valid_timestamp(&now_ts()));
    }
}
