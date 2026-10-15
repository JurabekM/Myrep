use std::sync::atomic::{AtomicU64, Ordering};

use uuid::Uuid;

/// ID yaratuvchi. Domen tasodifiylikka bog'liq bo'lmasligi uchun trait orqali beriladi.
pub trait IdGen: Send + Sync {
    fn new_id(&self) -> Uuid;
}

/// Ishlab chiqarishdagi UUIDv7 generatori.
#[derive(Debug, Default)]
pub struct UuidV7Gen;

impl IdGen for UuidV7Gen {
    fn new_id(&self) -> Uuid {
        Uuid::now_v7()
    }
}

/// Testlar uchun: `00000000-0000-7000-8000-000000000001`, `…002`, …
#[derive(Debug, Default)]
pub struct SequentialIdGen {
    next: AtomicU64,
}

impl IdGen for SequentialIdGen {
    fn new_id(&self) -> Uuid {
        let n = self.next.fetch_add(1, Ordering::Relaxed) + 1;
        Uuid::from_u128(0x0000_0000_0000_7000_8000_0000_0000_0000_u128 | u128::from(n))
    }
}
