//! Qurilma rollari (K8, ADR-0003): `OWNER` (rolsiz qurilma), `SELLER`, `ACCOUNTANT`.
//!
//! * Rolli qurilmaga eksport kamaytiriladi — kerak bo'lmagan yozuv u qurilmaga umuman bormaydi
//!   ([`Audience::filter`]).
//! * Egasining qurilmasi rolli qurilmadan faqat ruxsat etilgan yozuvlarni qabul qiladi
//!   ([`Audience::verdict`]); qolganlari e'tiborsiz yoki rad etiladi.
//! * Rolni faqat egasi yozadi (`device_access`); yangi qurilma egasining yozuvi kelguncha rolini
//!   ulash faylidan biladi (`local_device_role`).
use std::collections::HashSet;

use baraka_interchange::canon::Row;
use baraka_storage::repo::{household, roles};
use serde_json::Value;

use crate::app::Ctx;
use crate::{App, AppError, DeviceRoleDto};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Role {
    Owner,
    Seller,
    Accountant,
}

impl Role {
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "OWNER" => Some(Self::Owner),
            "SELLER" => Some(Self::Seller),
            "ACCOUNTANT" => Some(Self::Accountant),
            _ => None,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Owner => "OWNER",
            Self::Seller => "SELLER",
            Self::Accountant => "ACCOUNTANT",
        }
    }
}

/// Shu qurilmaning roli va (rolli bo'lsa) bog'langan makon.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct Access {
    pub role: Role,
    pub space_id: Option<String>,
}

/// Rolli qurilma ko'ra oladigan tushum va nasiya yozuvlari: sotuvchi ishlaydigan jadvallar.
const SELLER_SPACE_TABLES: [&str; 3] = ["kk_customers", "kk_credit_sales", "kk_credit_events"];
/// Sotuvchiga yuborilmaydigan ustunlar (qiymati `null` bo'ladi): tannarx ma'lumoti.
const SELLER_REDACTED: [(&str, &str); 1] = [("kk_items", "replacement_price_minor")];

fn text<'a>(row: &'a Row, k: &str) -> Option<&'a str> {
    row.get(k).and_then(Value::as_str)
}

/// Eksport kim uchun: rol, makon va (ulash taklifida hali noma'lum) qurilma.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct Audience {
    pub role: Role,
    pub space_id: String,
    pub device_id: Option<String>,
}

/// Rolli qurilmadan kelgan yozuv bo'yicha egasining qarori.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum Verdict {
    Accept,
    /// Egasining o'z yozuvi qaytib kelgan (yoki boshqa qurilmaniki) — e'tibor berilmaydi.
    Ignore,
    /// Rolli qurilma yaratgan, lekin unga ruxsat etilmagan yozuv.
    Reject(&'static str),
}

impl Audience {
    fn in_space(&self, row: &Row) -> bool {
        text(row, "space_id") == Some(self.space_id.as_str())
    }

    fn own(&self, row: &Row, column: &str) -> bool {
        self.device_id.is_some() && text(row, column) == self.device_id.as_deref()
    }

    /// Kamaytirilgan eksport. `tables` — sinxronlash tartibidagi (jadval, yozuvlar).
    pub fn filter(&self, tables: Vec<(String, Vec<Row>)>) -> Vec<(String, Vec<Row>)> {
        match self.role {
            Role::Owner => tables,
            Role::Seller => {
                // Nasiya to'lovlari tushumlari — nasiya daftari ishlashi uchun (tashqi kalit).
                let credit_incomes: HashSet<String> = tables
                    .iter()
                    .filter(|(t, _)| t == "kk_credit_events")
                    .flat_map(|(_, rows)| rows.iter())
                    .filter(|r| self.in_space(r))
                    .filter_map(|r| text(r, "income_id").map(str::to_string))
                    .collect();
                tables
                    .into_iter()
                    .map(|(t, rows)| {
                        let kept = rows
                            .into_iter()
                            .filter_map(|r| self.seller_row(&t, r, &credit_incomes))
                            .collect();
                        (t, kept)
                    })
                    .collect()
            }
            Role::Accountant => {
                let mut out: Vec<(String, Vec<Row>)> = tables
                    .into_iter()
                    .map(|(t, rows)| {
                        let kept = rows
                            .into_iter()
                            .filter(|r| self.accountant_keeps(&t, r))
                            .collect();
                        (t, kept)
                    })
                    .collect();
                // A'zolar — faqat yuborilgan yozuvlar bog'langanlari (tashqi kalit).
                let members: HashSet<String> = out
                    .iter()
                    .flat_map(|(_, rows)| rows.iter())
                    .flat_map(|r| [text(r, "member_id"), text(r, "owner_member_id")])
                    .flatten()
                    .map(str::to_string)
                    .collect();
                for (t, rows) in &mut out {
                    if t == "members" {
                        rows.retain(|r| text(r, "id").is_some_and(|id| members.contains(id)));
                    }
                }
                out
            }
        }
    }

    fn seller_row(
        &self,
        table: &str,
        mut row: Row,
        credit_incomes: &HashSet<String>,
    ) -> Option<Row> {
        let keep = match table {
            "households" | "devices" => true,
            "spaces" => text(&row, "id") == Some(self.space_id.as_str()),
            "device_access" => self.own(&row, "device_id"),
            "kk_items" => self.in_space(&row),
            t if SELLER_SPACE_TABLES.contains(&t) => self.in_space(&row),
            "incomes" => {
                self.in_space(&row)
                    && (self.own(&row, "origin_device_id")
                        || text(&row, "id").is_some_and(|id| credit_incomes.contains(id)))
            }
            "kk_stock_moves" => {
                self.in_space(&row)
                    && text(&row, "kind") == Some("SALE")
                    && self.own(&row, "origin_device_id")
            }
            "kk_shifts" => self.in_space(&row) && self.own(&row, "device_id"),
            _ => false,
        };
        if !keep {
            return None;
        }
        for (t, col) in SELLER_REDACTED {
            if t == table {
                if let Some(v) = row.get_mut(col) {
                    *v = Value::Null;
                }
            }
        }
        Some(row)
    }

    fn accountant_keeps(&self, table: &str, row: &Row) -> bool {
        match table {
            "households" | "devices" | "members" => true,
            "spaces" => text(row, "id") == Some(self.space_id.as_str()),
            "device_access" => self.own(row, "device_id"),
            _ => self.in_space(row),
        }
    }

    /// Rolli qurilma (`source`) faylidagi yozuv qabul qilinadimi.
    pub fn verdict(&self, source: &str, table: &str, row: &Row) -> Verdict {
        if table == "devices" {
            return if text(row, "id") == Some(source) {
                Verdict::Accept
            } else {
                Verdict::Ignore
            };
        }
        if text(row, "origin_device_id") != Some(source) {
            return Verdict::Ignore;
        }
        let allowed = self.role == Role::Seller
            && self.in_space(row)
            && match table {
                "incomes" => true,
                "kk_stock_moves" => text(row, "kind") == Some("SALE"),
                "kk_credit_events" => text(row, "kind") == Some("PAYMENT"),
                "kk_shifts" => text(row, "device_id") == Some(source),
                _ => false,
            };
        if allowed {
            Verdict::Accept
        } else {
            Verdict::Reject("ROLE_FORBIDDEN")
        }
    }
}

impl App {
    /// Shu qurilmaning roli: egasining yozuvi, bo'lmasa ulash faylidagisi, bo'lmasa — egasi.
    pub(crate) fn access_in(&self, household_id: &str) -> Result<Access, AppError> {
        if let Some(a) = self
            .db
            .read(|c| roles::access_of(c, household_id, &self.device_id))?
        {
            return Ok(Access {
                role: Role::parse(&a.role).ok_or(AppError::new("DB_ERROR"))?,
                space_id: Some(a.space_id),
            });
        }
        if let Some((role, space)) = self.db.read(|c| roles::local_role(c, household_id))? {
            return Ok(Access {
                role: Role::parse(&role).ok_or(AppError::new("DB_ERROR"))?,
                space_id: Some(space),
            });
        }
        Ok(Access {
            role: Role::Owner,
            space_id: None,
        })
    }

    pub(crate) fn access(&self, ctx: &Ctx) -> Result<Access, AppError> {
        self.access_in(&ctx.household_id)
    }

    /// Hisobchi qurilmasida baza faqat o'qish uchun (sinxronlash importidan tashqari).
    pub(crate) fn refresh_role(&self) {
        let role = self
            .db
            .read(household::get_household)
            .ok()
            .flatten()
            .and_then(|h| self.access_in(&h.id).ok())
            .map_or(Role::Owner, |a| a.role);
        self.db.set_read_only(role == Role::Accountant);
    }

    /// Faqat egasining qurilmasida (ulash, rol berish, bekor qilish).
    pub(crate) fn ensure_owner(&self, ctx: &Ctx) -> Result<(), AppError> {
        if self.access(ctx)?.role == Role::Owner {
            Ok(())
        } else {
            Err(AppError::new("ROLE_FORBIDDEN"))
        }
    }

    /// UI uchun: shu qurilmaning roli va bog'langan makon.
    pub fn device_role(&self) -> Result<DeviceRoleDto, AppError> {
        let ctx = self.ctx()?;
        let a = self.access(&ctx)?;
        let space_name = match &a.space_id {
            Some(id) => self
                .db
                .read(|c| household::list_spaces(c, &ctx.household_id))?
                .into_iter()
                .find(|s| &s.id == id)
                .map(|s| s.name),
            None => None,
        };
        Ok(DeviceRoleDto {
            role: a.role.as_str().to_string(),
            space_id: a.space_id,
            space_name,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn row(v: Value) -> Row {
        v.as_object().cloned().unwrap_or_default()
    }

    fn seller() -> Audience {
        Audience {
            role: Role::Seller,
            space_id: "kk".into(),
            device_id: Some("d2".into()),
        }
    }

    #[test]
    fn seller_gets_catalog_credit_and_own_records_only() {
        let tables = vec![
            (
                "spaces".to_string(),
                vec![row(json!({"id": "kk"})), row(json!({"id": "uy"}))],
            ),
            (
                "incomes".to_string(),
                vec![
                    row(json!({"id": "i1", "space_id": "kk", "origin_device_id": "d1"})),
                    row(json!({"id": "i2", "space_id": "kk", "origin_device_id": "d2"})),
                    row(json!({"id": "i3", "space_id": "kk", "origin_device_id": "d1"})),
                ],
            ),
            (
                "expenses".to_string(),
                vec![row(
                    json!({"id": "e1", "space_id": "kk", "origin_device_id": "d1"}),
                )],
            ),
            (
                "kk_moves".to_string(),
                vec![row(
                    json!({"id": "m1", "space_id": "kk", "kind": "OWNER_DRAW"}),
                )],
            ),
            (
                "kk_credit_events".to_string(),
                vec![row(
                    json!({"id": "c1", "space_id": "kk", "income_id": "i3"}),
                )],
            ),
            (
                "kk_items".to_string(),
                vec![row(
                    json!({"id": "s", "space_id": "kk", "replacement_price_minor": 1350000}),
                )],
            ),
            (
                "kk_stock_moves".to_string(),
                vec![
                    row(
                        json!({"id": "p", "space_id": "kk", "kind": "PURCHASE", "origin_device_id": "d1"}),
                    ),
                    row(
                        json!({"id": "q", "space_id": "kk", "kind": "SALE", "origin_device_id": "d2"}),
                    ),
                ],
            ),
        ];
        let out = seller().filter(tables);
        let ids = |t: &str| -> Vec<String> {
            out.iter()
                .find(|x| x.0 == t)
                .map(|x| {
                    x.1.iter()
                        .filter_map(|r| text(r, "id").map(str::to_string))
                        .collect()
                })
                .unwrap_or_default()
        };
        assert_eq!(ids("spaces"), ["kk"]);
        // Egasining savdosi (i1) yo'q; nasiya to'lovi tushumi (i3) bor.
        assert_eq!(ids("incomes"), ["i2", "i3"]);
        assert!(ids("expenses").is_empty());
        assert!(ids("kk_moves").is_empty());
        assert_eq!(ids("kk_stock_moves"), ["q"]);
        let item = &out.iter().find(|x| x.0 == "kk_items").unwrap().1[0];
        assert_eq!(item.get("replacement_price_minor"), Some(&Value::Null));
    }

    #[test]
    fn owner_accepts_only_seller_own_allowed_rows() {
        let a = seller();
        let v = |t: &str, r: Value| a.verdict("d2", t, &row(r));
        assert_eq!(v("devices", json!({"id": "d2"})), Verdict::Accept);
        assert_eq!(v("devices", json!({"id": "d1"})), Verdict::Ignore);
        assert_eq!(
            v(
                "incomes",
                json!({"space_id": "kk", "origin_device_id": "d2"})
            ),
            Verdict::Accept
        );
        assert_eq!(
            v(
                "incomes",
                json!({"space_id": "kk", "origin_device_id": "d1"})
            ),
            Verdict::Ignore
        );
        assert_eq!(
            v(
                "expenses",
                json!({"space_id": "kk", "origin_device_id": "d2"})
            ),
            Verdict::Reject("ROLE_FORBIDDEN")
        );
        assert_eq!(
            v(
                "kk_stock_moves",
                json!({"space_id": "kk", "kind": "PURCHASE", "origin_device_id": "d2"})
            ),
            Verdict::Reject("ROLE_FORBIDDEN")
        );
        assert_eq!(
            v(
                "device_access",
                json!({"id": "d2", "origin_device_id": "d2"})
            ),
            Verdict::Reject("ROLE_FORBIDDEN")
        );
        let acc = Audience {
            role: Role::Accountant,
            ..seller()
        };
        assert_eq!(
            acc.verdict(
                "d2",
                "incomes",
                &row(json!({"space_id": "kk", "origin_device_id": "d2"}))
            ),
            Verdict::Reject("ROLE_FORBIDDEN")
        );
    }
}
