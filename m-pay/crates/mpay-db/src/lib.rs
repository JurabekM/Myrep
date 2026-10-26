//! Ma'lumotlar bazasi: SQLite (sandbox, bitta instansiya) yoki PostgreSQL (2-faza P2.3, ADR-0018) —
//! `sqlx::Any` orqali, dialekt URL bo'yicha tanlanadi.
//!
//! SQL ikkala dialektga mos yoziladi: parametrlar `$1, $2, …` (birinchi uchrashish tartibida),
//! butun sonlar `BIGINT` (Rust `i64`), yig'indilar `CAST(… AS BIGINT)`. Dialektga xos qismlar
//! ([`Db::for_update`], [`Db::lock`]) shu modulda.
//!
//! Yozish semantikasi:
//! * **SQLite** — bitta yozuvchi: jarayon ichidagi qulf + `BEGIN IMMEDIATE` (WAL'da o'qishdan yozishga
//!   o'tishdagi `SQLITE_BUSY` bo'lmasin), hovuz 1 ulanish.
//! * **PostgreSQL** — parallel tranzaksiyalar (`READ COMMITTED`); poyga xavfi bor joylarda qator
//!   qulflari (`SELECT … FOR UPDATE`) va tranzaksiya advisory qulflari ([`Db::lock`]).
#![forbid(unsafe_code)]

use std::sync::Arc;
use std::time::Duration;

use sqlx::any::AnyPoolOptions;
use sqlx::{Any, Executor, Transaction};
use sqlx::{AnyConnection, AnyPool};
use tokio::sync::{Mutex, OwnedMutexGuard};

/// Commit chidamliligi (SQLite `synchronous`; PostgreSQL'da server sozlamasi).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Durability {
    /// Har commit diskka `fsync` (standart; to'lov ma'lumoti uchun tavsiya etiladi).
    #[default]
    Full,
    /// WAL + `NORMAL`: jarayon yiqilsa ma'lumot yo'qolmaydi, lekin elektr uzilsa oxirgi
    /// commit'lar yo'qolishi mumkin (fayl buzilmaydi). Faqat sandbox / o'lchov uchun.
    Normal,
}

/// SQLite standart hovuz hajmi. Bir vaqtda bitta yozuvchi: ko'p ulanish yozish qulfi uchun
/// busy-handler'da uxlab kutadi — bitta ulanishda navbat jarayon ichida (`docs/load-report.md`).
pub const DEFAULT_MAX_CONNECTIONS: u32 = 1;

/// PostgreSQL standart hovuz hajmi.
pub const DEFAULT_PG_MAX_CONNECTIONS: u32 = 32;

/// SQL dialekti.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Dialect {
    Sqlite,
    Postgres,
}

/// Tranzaksiya advisory qulflari kalitlari (PostgreSQL; SQLite'da yozuvchi baribir bitta).
#[derive(Debug, Clone, Copy)]
pub enum LockKey<'a> {
    /// Audit xesh-zanjiri boshi — tranzaksiyada **oxirgi** olinadigan qulf (deadlock bo'lmasin).
    Audit,
    /// Ixtiyoriy obyekt (masalan karta barmoq izi, qurilma) — `nom ‖ qiymat` xeshi.
    Named(&'static str, &'a [u8]),
}

impl LockKey<'_> {
    fn id(&self) -> i64 {
        use sha2::{Digest, Sha256};
        let mut h = Sha256::new();
        match self {
            LockKey::Audit => h.update(b"mpay.audit"),
            LockKey::Named(n, v) => {
                h.update(n.as_bytes());
                h.update([0u8]);
                h.update(v);
            }
        }
        let d = h.finalize();
        let mut b = [0u8; 8];
        b.copy_from_slice(&d[..8]);
        i64::from_be_bytes(b)
    }
}

/// Ulanishlar hovuzi va dialekt. Arzon klonlanadi (bir xil hovuz va SQLite yozish qulfi).
#[derive(Clone)]
pub struct Db {
    pool: AnyPool,
    dialect: Dialect,
    /// SQLite: jarayon ichidagi yagona yozuvchi qulfi.
    write: Arc<Mutex<()>>,
}

impl std::fmt::Debug for Db {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Db({:?})", self.dialect)
    }
}

/// Yozuvchi tranzaksiya (SQLite'da yozish qulfi bilan). `&mut *tx` — `AnyConnection`.
pub struct WriteTx {
    tx: Transaction<'static, Any>,
    _guard: Option<OwnedMutexGuard<()>>,
}

impl std::ops::Deref for WriteTx {
    type Target = AnyConnection;
    fn deref(&self) -> &AnyConnection {
        &self.tx
    }
}

impl std::ops::DerefMut for WriteTx {
    fn deref_mut(&mut self) -> &mut AnyConnection {
        &mut self.tx
    }
}

impl WriteTx {
    /// Commit; SQLite qulfi commit'dan keyin bo'shaydi.
    pub async fn commit(self) -> Result<(), sqlx::Error> {
        self.tx.commit().await
    }
}

/// SQLite fayl yo'lidan `sqlx::Any` URL'i (Windows yo'llari bilan ham; `?`/`#`/`%` kodlanadi).
pub fn sqlite_url(path: &std::path::Path) -> String {
    let p = path
        .display()
        .to_string()
        .replace('\\', "/")
        .replace('%', "%25")
        .replace('?', "%3F")
        .replace('#', "%23");
    format!("sqlite:{p}?mode=rwc")
}

impl Db {
    /// URL bo'yicha ochadi: `sqlite:…` yoki `postgres://…`. `max_connections` — `None` bo'lsa
    /// dialekt standarti.
    pub async fn open(
        url: &str,
        durability: Durability,
        max_connections: Option<u32>,
    ) -> Result<Self, sqlx::Error> {
        sqlx::any::install_default_drivers();
        let dialect = if url.starts_with("sqlite:") {
            Dialect::Sqlite
        } else if url.starts_with("postgres://") || url.starts_with("postgresql://") {
            Dialect::Postgres
        } else {
            return Err(sqlx::Error::Configuration(
                "database url: sqlite: yoki postgres:// kutilgan".into(),
            ));
        };
        let mut opts = AnyPoolOptions::new();
        opts = match dialect {
            Dialect::Sqlite => {
                let sync = match durability {
                    Durability::Full => "FULL",
                    Durability::Normal => "NORMAL",
                };
                let pragmas = format!(
                    "PRAGMA journal_mode = WAL; PRAGMA synchronous = {sync}; \
                     PRAGMA foreign_keys = ON; PRAGMA busy_timeout = 5000;"
                );
                opts.max_connections(max_connections.unwrap_or(DEFAULT_MAX_CONNECTIONS).max(1))
                    .after_connect(move |conn, _| {
                        let pragmas = pragmas.clone();
                        Box::pin(async move {
                            conn.execute(sqlx::AssertSqlSafe(pragmas)).await?;
                            Ok(())
                        })
                    })
            }
            Dialect::Postgres => opts
                .max_connections(max_connections.unwrap_or(DEFAULT_PG_MAX_CONNECTIONS).max(1))
                .acquire_timeout(Duration::from_secs(10)),
        };
        let pool = opts.connect(url).await?;
        Ok(Self {
            pool,
            dialect,
            write: Arc::new(Mutex::new(())),
        })
    }

    /// SQLite fayli (sandbox va testlar).
    pub async fn open_sqlite(path: &std::path::Path) -> Result<Self, sqlx::Error> {
        Self::open(&sqlite_url(path), Durability::Full, None).await
    }

    pub fn pool(&self) -> &AnyPool {
        &self.pool
    }

    pub fn dialect(&self) -> Dialect {
        self.dialect
    }

    /// Yozuvchi tranzaksiya. SQLite: avval jarayon qulfi, so'ng `BEGIN IMMEDIATE`. Qulf ostida
    /// hovuzdan boshqa so'rov qilinmaydi (bitta ulanishda o'z-o'zini kutish) — faqat `&mut *tx`.
    pub async fn begin_write(&self) -> Result<WriteTx, sqlx::Error> {
        match self.dialect {
            Dialect::Sqlite => {
                let guard = self.write.clone().lock_owned().await;
                let tx = self.pool.begin_with("BEGIN IMMEDIATE").await?;
                Ok(WriteTx {
                    tx,
                    _guard: Some(guard),
                })
            }
            Dialect::Postgres => Ok(WriteTx {
                tx: self.pool.begin().await?,
                _guard: None,
            }),
        }
    }

    /// `SELECT … FOR UPDATE` qo'shimchasi (PostgreSQL'da qatorni tranzaksiya oxirigacha qulflaydi;
    /// SQLite'da yozuvchi bitta — bo'sh).
    pub fn for_update(&self) -> &'static str {
        match self.dialect {
            Dialect::Sqlite => "",
            Dialect::Postgres => " FOR UPDATE",
        }
    }

    /// Tranzaksiya advisory qulfi (PostgreSQL `pg_advisory_xact_lock`; commit/rollback'da bo'shaydi).
    /// SQLite'da hech narsa qilmaydi — yozuvchi tranzaksiya baribir yagona.
    pub async fn lock(&self, tx: &mut AnyConnection, key: LockKey<'_>) -> Result<(), sqlx::Error> {
        if self.dialect == Dialect::Postgres {
            sqlx::query("SELECT pg_advisory_xact_lock($1)")
                .bind(key.id())
                .execute(&mut *tx)
                .await?;
        }
        Ok(())
    }

    /// Bir nechta advisory qulf — deadlock bo'lmasligi uchun doimiy (kalit) tartibda.
    pub async fn lock_all(
        &self,
        tx: &mut AnyConnection,
        keys: &[LockKey<'_>],
    ) -> Result<(), sqlx::Error> {
        let mut ids: Vec<i64> = keys.iter().map(LockKey::id).collect();
        ids.sort_unstable();
        ids.dedup();
        if self.dialect == Dialect::Postgres {
            for id in ids {
                sqlx::query("SELECT pg_advisory_xact_lock($1)")
                    .bind(id)
                    .execute(&mut *tx)
                    .await?;
            }
        }
        Ok(())
    }

    /// Migratsiyalar: `migrations/sqlite` yoki `migrations/postgres`. Boshqa modullar (emitent,
    /// server) ham shu DB'da o'z migratsiyalariga ega — "noma'lum" versiyalar e'tiborsiz.
    pub async fn migrate_with(
        &self,
        sqlite: sqlx::migrate::Migrator,
        postgres: sqlx::migrate::Migrator,
    ) -> Result<(), sqlx::migrate::MigrateError> {
        let mut m = match self.dialect {
            Dialect::Sqlite => sqlite,
            Dialect::Postgres => postgres,
        };
        m.set_ignore_missing(true);
        m.run(&self.pool).await
    }
}

/// Testlar uchun: `admin_url` (PostgreSQL) serverida yangi bo'sh baza yaratadi va unga URL qaytaradi
/// (har test o'z bazasida — parallel testlar bir-biriga xalaqit bermaydi).
#[doc(hidden)]
pub async fn fresh_test_database(admin_url: &str) -> Result<String, sqlx::Error> {
    use std::sync::atomic::{AtomicU64, Ordering};
    static N: AtomicU64 = AtomicU64::new(0);
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(std::process::id().to_be_bytes());
    h.update(N.fetch_add(1, Ordering::Relaxed).to_be_bytes());
    h.update(
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0)
            .to_be_bytes(),
    );
    let d = h.finalize();
    let name: String = d[..8].iter().map(|b| format!("{b:02x}")).collect();
    let name = format!("mpay_t_{name}");
    sqlx::any::install_default_drivers();
    let admin = AnyPoolOptions::new()
        .max_connections(1)
        .connect(admin_url)
        .await?;
    admin
        .execute(sqlx::AssertSqlSafe(format!("CREATE DATABASE {name}")))
        .await?;
    admin.close().await;
    let (base, query) = match admin_url.split_once('?') {
        Some((b, q)) => (b, format!("?{q}")),
        None => (admin_url, String::new()),
    };
    let base = base.rsplit_once('/').map_or(base, |(b, _)| b);
    Ok(format!("{base}/{name}{query}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sqlite_url_escapes() {
        let u = sqlite_url(std::path::Path::new(r"C:\a b\x?y#z%1.db"));
        assert_eq!(u, "sqlite:C:/a b/x%3Fy%23z%251.db?mode=rwc");
    }

    #[test]
    fn lock_ids_are_stable_and_distinct() {
        let a = LockKey::Named("pan", b"1").id();
        assert_eq!(a, LockKey::Named("pan", b"1").id());
        assert_ne!(a, LockKey::Named("dev", b"1").id());
        assert_ne!(a, LockKey::Audit.id());
    }
}
