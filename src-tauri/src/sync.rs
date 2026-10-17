//! D14 xizmati: `.baraka` eksport/import — konteyner (Argon2id + XChaCha20-Poly1305), fayl yozish/o'qish,
//! birlashtirish hisoboti. Qoidalar `storage::interchange` da; parol konteynerda, loglarda yo'q.

use std::path::{Path, PathBuf};

use security::{KdfParams, SecurityError, open_container, seal_container};
use storage::interchange::{ImportReport, export_json, import_json};
use storage::{Database, StorageError};
use time::OffsetDateTime;
use time::format_description::well_known::Iso8601;

use crate::dto::{
    ConflictDto, ExportInputDto, ExportResultDto, ForkDto, ImportInputDto, ImportReportDto,
    TableCountDto,
};
use crate::finance::{self, DEVICE_ID};
use crate::session::SessionError;

/// Fayl kengaytmasi.
pub const EXTENSION: &str = "baraka";

fn ts(now: OffsetDateTime) -> String {
    now.format(&Iso8601::DEFAULT).unwrap_or_default()
}

fn report_dto(report: ImportReport) -> ImportReportDto {
    let counts = |map: std::collections::BTreeMap<String, u32>| {
        map.into_iter()
            .map(|(table, count)| TableCountDto { table, count })
            .collect()
    };
    ImportReportDto {
        blocked: report.blocked,
        inserted: counts(report.inserted),
        updated: counts(report.updated),
        conflicts: report
            .conflicts
            .into_iter()
            .map(|c| ConflictDto {
                table: c.table,
                id: c.id,
                reason: c.reason,
            })
            .collect(),
        forks: report
            .forks
            .into_iter()
            .map(|f| ForkDto {
                agreement_id: f.agreement_id,
                first_broken: u32::try_from(f.first_broken).unwrap_or(u32::MAX),
            })
            .collect(),
        journal_appended: report.journal_appended,
        exported_at: report.exported_at,
        device_id: report.device_id,
        household_mismatch: report.household_mismatch,
    }
}

/// Eksport: JSON → konteyner → fayl. `path` bo'sh bo'lsa — `default_dir/baraka-<vaqt>.baraka`.
pub fn export(
    db: &Database,
    now: OffsetDateTime,
    default_dir: &Path,
    params: KdfParams,
    input: ExportInputDto,
) -> Result<ExportResultDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let since = input.since.as_deref().filter(|s| !s.trim().is_empty());
    let payload = export_json(db, &ctx.household.id, DEVICE_ID, &ts(now), since)?;
    let rows = payload["tables"].as_object().map_or(0, |t| {
        t.values().filter_map(|v| v.as_array()).map(Vec::len).sum()
    });
    let tables = payload["tables"].as_object().map_or(0, |t| t.len());
    let json = serde_json::to_vec(&payload)
        .map_err(|_| StorageError::InvalidData("eksport JSON".to_owned()))?;
    let bytes = seal_container(&input.password, params, &json)?;
    let path = match input.path.as_deref().filter(|p| !p.trim().is_empty()) {
        Some(text) => PathBuf::from(text.trim()),
        None => {
            let stamp = now
                .format(&time::macros::format_description!(
                    "[year][month][day]-[hour][minute][second]"
                ))
                .unwrap_or_default();
            default_dir.join(format!("baraka-{stamp}.{EXTENSION}"))
        }
    };
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(SecurityError::Io)?;
    }
    std::fs::write(&path, bytes).map_err(SecurityError::Io)?;
    Ok(ExportResultDto {
        path: path.display().to_string(),
        tables: u32::try_from(tables).unwrap_or(u32::MAX),
        rows: u32::try_from(rows).unwrap_or(u32::MAX),
    })
}

fn read_payload(input: &ImportInputDto) -> Result<serde_json::Value, SessionError> {
    let bytes = std::fs::read(input.path.trim()).map_err(SecurityError::Io)?;
    let plain = open_container(&input.password, &bytes)?;
    serde_json::from_slice(&plain)
        .map_err(|_| StorageError::InvalidData("almashish JSON".to_owned()).into())
}

/// Import ko'rigi (dry-run): nima qo'shiladi, nima yangilanadi, ziddiyatlar, forklar.
pub fn preview(db: &Database, input: ImportInputDto) -> Result<ImportReportDto, SessionError> {
    let payload = read_payload(&input)?;
    Ok(report_dto(import_json(db, &payload, true)?))
}

/// Importni qo'llaydi (fork bo'lsa — hech narsa yozilmaydi, hisobot `blocked`).
pub fn apply(db: &Database, input: ImportInputDto) -> Result<ImportReportDto, SessionError> {
    let payload = read_payload(&input)?;
    Ok(report_dto(import_json(db, &payload, false)?))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dto::CeremonyInputDto;
    use security::SecretKey;
    use time::macros::datetime;

    const NOW: OffsetDateTime = datetime!(2026-12-01 06:00 UTC);

    fn database(seed: u8) -> Database {
        Database::open_in_memory(&SecretKey::from_array([seed; 32])).expect("xotirada baza")
    }

    #[test]
    fn eksport_fayli_yangi_bazaga_import_qilinadi_va_notogri_parol_aniq_xato() {
        let source = database(111);
        crate::ceremonies::create(
            &source,
            NOW,
            CeremonyInputDto {
                kind: "TOY".into(),
                title: "To'y".into(),
                event_on: None,
            },
        )
        .expect("marosim");
        let dir = std::env::temp_dir().join(format!("baraka-sync-{}", std::process::id()));
        let result = export(
            &source,
            NOW,
            &dir,
            KdfParams::FAST_FOR_TESTS,
            ExportInputDto {
                path: None,
                password: "juda-sirli-parol".into(),
                since: None,
            },
        )
        .expect("eksport");
        assert!(result.path.ends_with(".baraka"));
        assert!(result.rows >= 3, "xonadon, a'zo, marosim: {}", result.rows);

        let target = database(112);
        // Nishon daftar avto-yaratilgan (bo'sh) xonadonga ega — qoida: u kiruvchi xonadonga bo'shatiladi.
        let seed = finance::context(&target, NOW).expect("urug'");
        assert!(matches!(
            preview(
                &target,
                ImportInputDto {
                    path: result.path.clone(),
                    password: "notogri-parol-1".into(),
                }
            ),
            Err(SessionError::Security(SecurityError::WrongPassword))
        ));
        let report = apply(
            &target,
            ImportInputDto {
                path: result.path.clone(),
                password: "juda-sirli-parol".into(),
            },
        )
        .expect("import");
        assert!(!report.blocked);
        assert!(
            report
                .inserted
                .iter()
                .any(|t| t.table == "ceremonies" && t.count == 1)
        );
        let view = crate::ceremonies::overview(&target, NOW).expect("ro'yxat");
        assert_eq!(view.items.len(), 1);
        assert_eq!(view.items[0].title, "To'y");
        let after = finance::context(&target, NOW).expect("kontekst");
        assert_ne!(
            after.household.id, seed.household.id,
            "urug' xonadon kiruvchi bilan almashdi"
        );
        let households: i64 = target
            .connection()
            .query_row("SELECT COUNT(*) FROM households", [], |r| r.get(0))
            .expect("son");
        assert_eq!(households, 1);
        // Yozuvli boshqa xonadon — import to'xtaydi.
        let busy = database(113);
        crate::ceremonies::create(
            &busy,
            NOW,
            CeremonyInputDto {
                kind: "OTHER".into(),
                title: "Boshqa".into(),
                event_on: None,
            },
        )
        .expect("marosim");
        let report = preview(
            &busy,
            ImportInputDto {
                path: result.path.clone(),
                password: "juda-sirli-parol".into(),
            },
        )
        .expect("ko'rik");
        assert!(report.blocked && report.household_mismatch);
        let _ = std::fs::remove_dir_all(dir);
    }
}
