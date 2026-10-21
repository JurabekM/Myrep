//! Birlashtirish qarori (8.4). Har bir yozuv uchun uchta xesh: mahalliy, kelgan va `base` —
//! shu ikki qurilma oxirgi marta kelishgan holat. Soat ishlatilmaydi (qurilmalar soati farq
//! qilishi mumkin), «oxirgi yozgan yutadi» (LWW) yo'q.
use serde_json::Value;

use crate::canon::Row;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Decision {
    /// Mahalliy bazada yo'q — qo'shiladi.
    Insert,
    /// Faqat kelgan tomonda o'zgargan — qabul qilinadi.
    Update,
    /// Ikkala tomonda bir xil.
    Same,
    /// Kelgan tomon oxirgi kelishuvdan beri o'zgartirmagan — mahalliy nusxa qoladi.
    KeepLocal,
    /// Ikkala tomonda o'zgargan (yoki umumiy `base` yo'q) — foydalanuvchi tanlaydi.
    Conflict,
    /// O'zgarmas (yopilgan) yozuvni import orqali o'zgartirishga urinish — rad etiladi.
    Protected,
}

/// Bitta yozuv uchun qaror. `append_only` — DB darajasida o'zgarmas jadvallar (jurnal,
/// imzolangan versiyalar, yopilgan davrlar, bayonnomalar va h.k.).
pub fn decide(
    local: Option<&str>,
    base: Option<&str>,
    remote: &str,
    append_only: bool,
) -> Decision {
    let Some(local) = local else {
        return Decision::Insert;
    };
    if local == remote {
        return Decision::Same;
    }
    if append_only {
        return Decision::Protected;
    }
    match base {
        Some(b) if remote == b => Decision::KeepLocal,
        Some(b) if local == b => Decision::Update,
        _ => Decision::Conflict,
    }
}

/// Ziddiyat ekrani uchun: farq qiladigan ustunlar (nomi bo'yicha saralangan).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FieldDiff {
    pub field: String,
    pub local: Value,
    pub remote: Value,
}

pub fn diff(local: &Row, remote: &Row) -> Vec<FieldDiff> {
    let mut keys: Vec<&String> = local.keys().chain(remote.keys()).collect();
    keys.sort();
    keys.dedup();
    keys.into_iter()
        .filter_map(|k| {
            let l = local.get(k).cloned().unwrap_or(Value::Null);
            let r = remote.get(k).cloned().unwrap_or(Value::Null);
            (l != r).then(|| FieldDiff {
                field: k.clone(),
                local: l,
                remote: r,
            })
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use Decision::*;

    #[test]
    fn three_way_table() {
        // (mahalliy, base, kelgan, append_only) → qaror
        let cases = [
            (None, None, "r", false, Insert),
            (None, Some("b"), "r", true, Insert),
            (Some("x"), None, "x", false, Same),
            (Some("b"), Some("b"), "r", false, Update),
            (Some("l"), Some("b"), "b", false, KeepLocal),
            (Some("l"), Some("b"), "r", false, Conflict),
            (Some("l"), None, "r", false, Conflict),
            (Some("l"), Some("l"), "r", true, Protected),
            (Some("x"), Some("b"), "x", true, Same),
        ];
        for (l, b, r, a, want) in cases {
            assert_eq!(decide(l, b, r, a), want, "{l:?} {b:?} {r} {a}");
        }
    }

    #[test]
    fn diff_lists_changed_fields() {
        let l = json!({"id": "1", "amount_minor": 100, "note": "a"});
        let r = json!({"id": "1", "amount_minor": 150, "deleted_at": "2026-12-01"});
        let d = diff(l.as_object().unwrap(), r.as_object().unwrap());
        let names: Vec<&str> = d.iter().map(|x| x.field.as_str()).collect();
        assert_eq!(names, ["amount_minor", "deleted_at", "note"]);
    }
}
