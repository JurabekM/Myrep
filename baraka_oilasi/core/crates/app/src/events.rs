use std::sync::mpsc::{channel, Receiver, Sender};
use std::sync::Mutex;

use serde::Serialize;

/// UI qaysi ma'lumotni qayta o'qishi kerakligini bildiradi (4.4).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub enum Topic {
    Household,
    Categories,
    Incomes,
    Expenses,
    Vault,
    AllocationRule,
    Agreements,
    Journal,
    Debts,
    Budget,
    Ceremonies,
    Partnerships,
    Ventures,
    Ideas,
    Governance,
    Devices,
    Sync,
    Kasbkor,
    Musofir,
    /// «O'zimga sarmoya»: soat qiymati, bilim rejalari, «Ilm zakoti».
    Learning,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[cfg_attr(feature = "specta", derive(specta::Type))]
#[serde(rename_all = "camelCase")]
pub struct ChangeEvent {
    pub space_id: Option<String>,
    pub topics: Vec<Topic>,
}

/// Oddiy broadcast: har bir obunachi o'z kanaliga ega; yopilgan kanallar tashlab yuboriladi.
#[derive(Default)]
pub(crate) struct EventBus {
    subscribers: Mutex<Vec<Sender<ChangeEvent>>>,
}

impl EventBus {
    pub(crate) fn subscribe(&self) -> Receiver<ChangeEvent> {
        let (tx, rx) = channel();
        if let Ok(mut subs) = self.subscribers.lock() {
            subs.push(tx);
        }
        rx
    }

    pub(crate) fn publish(&self, space_id: Option<&str>, topics: &[Topic]) {
        let event = ChangeEvent {
            space_id: space_id.map(str::to_string),
            topics: topics.to_vec(),
        };
        if let Ok(mut subs) = self.subscribers.lock() {
            subs.retain(|s| s.send(event.clone()).is_ok());
        }
    }
}
