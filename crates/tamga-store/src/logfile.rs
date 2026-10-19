//! Diskdagi jurnal: har yozuv `fsync` bilan, ishga tushganda to'liq tekshiruv va checkpoint'lar.

use std::fs::{File, OpenOptions};
use std::io::Write as _;
use std::path::{Path, PathBuf};

use serde_json::{Map, Value};
use tamga_core::chain::{LogWriter, verify_log};
use tamga_core::checkpoint;
use tamga_core::error::ErrorCode;
use tamga_core::keys::SigningKeys;

use crate::{Result, StoreError, io_err, now_ts, random};

pub struct LogFile {
    path: PathBuf,
    ckpt_path: PathBuf,
    witness: Option<PathBuf>,
    file: File,
    writer: LogWriter,
    /// Oxirgi checkpoint qamragan yozuvlar soni.
    checkpointed: u64,
}

/// Ochishda nima bo'lgani (daemon jurnaliga yoziladi).
#[derive(Debug, Default)]
pub struct OpenReport {
    pub records: u64,
    pub recovered_partial_line: bool,
    pub warnings: Vec<String>,
    /// Jurnaldagi `key.rotate` yozuvlari: (seq, yangi kalit identifikatori) — spec §7.5.
    pub rotations: Vec<(u64, String)>,
}

impl LogFile {
    /// Jurnalni ochadi va boshidan tekshiradi. Faqat bitta holat avtomatik tuzatiladi: yozish
    /// paytida uzilib qolgan, `\n` bilan tugamagan oxirgi qator (u hech qachon tasdiqlanmagan).
    /// Boshqa har qanday buzilishda yozish rad etiladi — buzilgan zanjir davom ettirilmaydi.
    pub fn open(
        path: &Path,
        ckpt_path: &Path,
        log: &str,
        witness: Option<PathBuf>,
    ) -> Result<(Self, OpenReport)> {
        let mut report = OpenReport::default();
        let mut text = match std::fs::read(path) {
            Ok(b) => String::from_utf8(b).map_err(|_| {
                StoreError::Corrupt(tamga_core::VerifyError::new(
                    ErrorCode::Parse,
                    0,
                    "jurnal UTF-8 emas",
                ))
            })?,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => String::new(),
            Err(e) => return Err(io_err(path)(e)),
        };
        if !text.is_empty() && !text.ends_with('\n') {
            let cut = text.rfind('\n').map_or(0, |i| i + 1);
            let partial = path.with_extension("partial");
            std::fs::write(&partial, &text[cut..]).map_err(io_err(&partial))?;
            text.truncate(cut);
            let f = OpenOptions::new()
                .write(true)
                .open(path)
                .map_err(io_err(path))?;
            f.set_len(cut as u64).map_err(io_err(path))?;
            f.sync_all().map_err(io_err(path))?;
            report.recovered_partial_line = true;
        }
        let summary = verify_log(&text).map_err(StoreError::Corrupt)?;
        if let Some(existing) = &summary.log
            && existing != log
        {
            return Err(StoreError::Corrupt(tamga_core::VerifyError::new(
                ErrorCode::Log,
                0,
                format!("fayl `{existing}` jurnaliga tegishli"),
            )));
        }
        report.records = summary.len();
        report.warnings = summary.warnings;
        report.rotations = summary
            .rotations
            .iter()
            .map(|r| (r.seq, r.to.key_id()))
            .collect();

        let checkpointed = std::fs::read_to_string(ckpt_path)
            .ok()
            .and_then(|t| t.lines().last().map(str::to_owned))
            .and_then(|l| serde_json::from_str::<Value>(&l).ok())
            .and_then(|v| v.get("size").and_then(Value::as_u64))
            .unwrap_or(0);

        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .map_err(io_err(path))?;
        Ok((
            Self {
                path: path.to_owned(),
                ckpt_path: ckpt_path.to_owned(),
                witness,
                file,
                writer: LogWriter::resume(log, summary.hashes)?,
                checkpointed,
            },
            report,
        ))
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn len(&self) -> u64 {
        self.writer.hashes().len() as u64
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    pub fn log_id(&self) -> &str {
        self.writer.log_id()
    }

    /// Oxirgi checkpoint qamragan yozuvlar soni.
    pub fn checkpointed(&self) -> u64 {
        self.checkpointed
    }

    pub fn uncheckpointed(&self) -> u64 {
        // Checkpoint jurnaldan ko'proq yozuvni qamragan bo'lsa (qisqartirilgan jurnal) — ayirish
        // to'lib ketmasin (M-3). Bunday holat `open` da `verify_checkpoints` orqali rad etiladi.
        self.len().saturating_sub(self.checkpointed)
    }

    /// Yozuv qo'shadi va diskka majburan yozadi (`sync_data`). Qaytadi: `seq`.
    pub fn append(
        &mut self,
        ts: &str,
        session: &str,
        event: &str,
        body: Map<String, Value>,
    ) -> Result<u64> {
        let mut trial = self.writer.clone();
        let line = trial.append(ts, session, event, body)?;
        self.file
            .write_all(line.as_bytes())
            .map_err(io_err(&self.path))?;
        self.file.sync_data().map_err(io_err(&self.path))?;
        // Faqat diskka tushgandan keyin xotiradagi zanjir ilgari suriladi.
        self.writer = trial;
        Ok(self.len() - 1)
    }

    /// Yangi yozuvlar bo'lsa, hedged gibrid imzoli checkpoint yozadi (va guvoh papkasiga nusxalaydi).
    pub fn checkpoint(&mut self, keys: &SigningKeys) -> Result<Option<u64>> {
        if self.uncheckpointed() == 0 {
            return Ok(None);
        }
        let size = self.len();
        let rnd: [u8; 32] = random();
        let line = checkpoint::create_hedged(
            self.writer.log_id(),
            self.writer.hashes(),
            size,
            &now_ts(),
            keys,
            &rnd,
        )?;
        append_synced(&self.ckpt_path, &line)?;
        if let Some(dir) = &self.witness {
            let name = self.ckpt_path.file_name().expect("fayl nomi");
            std::fs::create_dir_all(dir).map_err(io_err(dir))?;
            append_synced(&dir.join(name), &line)?;
        }
        self.checkpointed = size;
        Ok(Some(size))
    }
}

fn append_synced(path: &Path, line: &str) -> Result<()> {
    let mut f = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(io_err(path))?;
    f.write_all(line.as_bytes()).map_err(io_err(path))?;
    f.sync_data().map_err(io_err(path))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tamga_core::checkpoint::verify_all;

    fn tmp(name: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("tamga-logfile-{name}-{}", std::process::id()));
        std::fs::remove_dir_all(&d).ok();
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    fn keys() -> SigningKeys {
        SigningKeys::from_seeds(&[1; 32], &[2; 32])
    }

    #[test]
    fn append_reopen_checkpoint_verify() {
        let d = tmp("basic");
        let (lp, cp, wd) = (
            d.join("l.jsonl"),
            d.join("l.checkpoints"),
            d.join("witness"),
        );
        {
            let (mut f, r) = LogFile::open(&lp, &cp, "t", Some(wd.clone())).unwrap();
            assert_eq!(r.records, 0);
            for _ in 0..3 {
                f.append(&now_ts(), "s", "prompt", Map::new()).unwrap();
            }
            assert_eq!(f.checkpoint(&keys()).unwrap(), Some(3));
            assert_eq!(
                f.checkpoint(&keys()).unwrap(),
                None,
                "yangi yozuvsiz checkpoint yo'q"
            );
        }
        let (mut f, r) = LogFile::open(&lp, &cp, "t", None).unwrap();
        assert_eq!((r.records, f.uncheckpointed()), (3, 0));
        assert_eq!(f.append(&now_ts(), "s", "prompt", Map::new()).unwrap(), 3);
        f.checkpoint(&keys()).unwrap();

        let log = std::fs::read_to_string(&lp).unwrap();
        let cps = std::fs::read_to_string(&cp).unwrap();
        let rep = verify_all(&log, &cps, &keys().public()).unwrap();
        assert_eq!((rep.log.len(), rep.checkpoints.len()), (4, 2));
        let witness = std::fs::read_to_string(wd.join("l.checkpoints")).unwrap();
        assert_eq!(
            witness.lines().count(),
            1,
            "guvohga birinchi checkpoint nusxalangan"
        );
        std::fs::remove_dir_all(d).ok();
    }

    #[test]
    fn partial_last_line_is_recovered_other_damage_is_refused() {
        let d = tmp("recover");
        let (lp, cp) = (d.join("l.jsonl"), d.join("l.checkpoints"));
        {
            let (mut f, _) = LogFile::open(&lp, &cp, "t", None).unwrap();
            f.append(&now_ts(), "s", "prompt", Map::new()).unwrap();
        }
        // Yozish o'rtasida uzilish.
        let mut text = std::fs::read_to_string(&lp).unwrap();
        text.push_str("{\"tamga\":\"0.1\",\"ev");
        std::fs::write(&lp, &text).unwrap();
        let (_, r) = LogFile::open(&lp, &cp, "t", None).unwrap();
        assert!(r.recovered_partial_line);
        assert!(d.join("l.partial").exists());

        // Haqiqiy buzilish: yozuv mazmuni o'zgargan.
        let text = std::fs::read_to_string(&lp)
            .unwrap()
            .replace("prompt", "prompX");
        std::fs::write(&lp, text).unwrap();
        assert!(matches!(
            LogFile::open(&lp, &cp, "t", None),
            Err(StoreError::Corrupt(_))
        ));
        std::fs::remove_dir_all(d).ok();
    }
}
