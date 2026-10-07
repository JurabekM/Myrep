use time::OffsetDateTime;
use uuid::Uuid;

pub trait Clock {
    fn now(&self) -> OffsetDateTime;
}

pub trait IdGen {
    fn new_id(&self) -> String;
}

pub struct SystemClock;

impl Clock for SystemClock {
    fn now(&self) -> OffsetDateTime {
        OffsetDateTime::now_utc()
    }
}

/// UUIDv7 (string). Autoincrement ID'lar ishlatilmaydi.
pub struct UuidV7Gen;

impl IdGen for UuidV7Gen {
    fn new_id(&self) -> String {
        Uuid::now_v7().to_string()
    }
}

/// Har bir jadvalda bo'ladigan umumiy maydonlar (DESKTOP_PROMPT 6.1).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Meta {
    pub id: String,
    pub household_id: String,
    pub created_at: OffsetDateTime,
    pub updated_at: OffsetDateTime,
    pub deleted_at: Option<OffsetDateTime>,
    pub version: i64,
    pub origin_device_id: String,
}

impl Meta {
    /// Yangi yozuv: `version = 1`.
    #[must_use]
    pub fn new(
        ids: &dyn IdGen,
        clock: &dyn Clock,
        household_id: &str,
        origin_device_id: &str,
    ) -> Self {
        let now = clock.now();
        Self {
            id: ids.new_id(),
            household_id: household_id.to_owned(),
            created_at: now,
            updated_at: now,
            deleted_at: None,
            version: 1,
            origin_device_id: origin_device_id.to_owned(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct Fixed;
    impl Clock for Fixed {
        fn now(&self) -> OffsetDateTime {
            OffsetDateTime::UNIX_EPOCH
        }
    }

    #[test]
    fn uuid_v7_ids_are_unique_and_versioned() {
        let g = UuidV7Gen;
        let (a, b) = (g.new_id(), g.new_id());
        assert_ne!(a, b);
        assert_eq!(Uuid::parse_str(&a).unwrap().get_version_num(), 7);
    }

    #[test]
    fn new_meta_starts_at_version_one() {
        let m = Meta::new(&UuidV7Gen, &Fixed, "h1", "dev1");
        assert_eq!((m.version, m.deleted_at), (1, None));
        assert_eq!(m.created_at, m.updated_at);
    }
}
