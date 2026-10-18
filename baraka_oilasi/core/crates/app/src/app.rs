use std::path::Path;
use std::sync::mpsc::Receiver;
use std::sync::Arc;

use baraka_domain_common::{local_date, Clock, IdGen, MemberRole, Necessity, SpaceKind, VaultType};
use baraka_money::{format, format_plain, Currency, Locale, Money};
use baraka_security::DbKey;
use baraka_storage::repo::{assets, categories, household, rules};
use baraka_storage::{Database, Meta, SpaceScope};
use chrono::{NaiveDate, SecondsFormat};
use chrono_tz::Tz;

use crate::catalog::{default_categories, DEFAULT_SHARE_BP};
use crate::events::{EventBus, Topic};
use crate::text::{clean_opt, required};
use crate::{
    AppError, BootstrapInput, CategoryDto, ChangeEvent, HouseholdDto, MemberDto, MoneyDto, SpaceDto,
};

/// Ilova yadrosi: bitta ochilgan (shifrlangan) baza va shu qurilma.
pub struct App {
    pub(crate) db: Database,
    pub(crate) clock: Arc<dyn Clock>,
    pub(crate) ids: Arc<dyn IdGen>,
    pub(crate) device_id: String,
    events: EventBus,
    /// `.baraka` eksportidagi Argon2id parametrlari (sessiya qurilmaga moslab beradi).
    pub(crate) export_kdf: std::sync::Mutex<baraka_interchange::container::Kdf>,
}

/// Joriy xonadon sozlamalari (har bir use-case uchun o'qiladi).
pub(crate) struct Ctx {
    pub household_id: String,
    pub locale: Locale,
    pub currency: Currency,
    pub tz: Tz,
    pub month_start_day: u32,
}

impl App {
    pub fn open(
        path: &Path,
        key: &DbKey,
        device_id: &str,
        clock: Arc<dyn Clock>,
        ids: Arc<dyn IdGen>,
    ) -> Result<Self, AppError> {
        Ok(Self::with_db(
            Database::open(path, key)?,
            device_id,
            clock,
            ids,
        ))
    }

    pub fn open_in_memory(
        key: &DbKey,
        device_id: &str,
        clock: Arc<dyn Clock>,
        ids: Arc<dyn IdGen>,
    ) -> Result<Self, AppError> {
        Ok(Self::with_db(
            Database::open_in_memory(key)?,
            device_id,
            clock,
            ids,
        ))
    }

    fn with_db(db: Database, device_id: &str, clock: Arc<dyn Clock>, ids: Arc<dyn IdGen>) -> Self {
        let app = Self {
            db,
            clock,
            ids,
            device_id: device_id.to_string(),
            events: EventBus::default(),
            export_kdf: std::sync::Mutex::new(baraka_interchange::container::Kdf::STANDARD),
        };
        // Hisobchi qurilmasi — faqat o'qish (K8).
        app.refresh_role();
        app
    }

    /// `.baraka` eksport kaliti uchun Argon2id parametrlari (`keys.bin` dagi bilan bir xil).
    pub fn set_interchange_kdf(&self, m_kib: u32, t_cost: u32, p_cost: u32) {
        if let Ok(mut k) = self.export_kdf.lock() {
            *k = baraka_interchange::container::Kdf::argon2id(m_kib, t_cost, p_cost);
        }
    }

    pub fn device_id(&self) -> &str {
        &self.device_id
    }

    /// UI o'zgarishlarga obuna bo'ladi (FRB `Stream`, Tauri event).
    pub fn subscribe(&self) -> Receiver<ChangeEvent> {
        self.events.subscribe()
    }

    pub(crate) fn publish(&self, space_id: Option<&str>, topics: &[Topic]) {
        self.events.publish(space_id, topics);
    }

    pub(crate) fn meta(&self) -> Meta {
        Meta {
            now: self
                .clock
                .now()
                .to_rfc3339_opts(SecondsFormat::Millis, true),
            device_id: self.device_id.clone(),
        }
    }

    pub(crate) fn new_id(&self) -> String {
        self.ids.new_id().to_string()
    }

    pub(crate) fn ctx(&self) -> Result<Ctx, AppError> {
        let h = self
            .db
            .read(household::get_household)?
            .ok_or(AppError::new("NOT_INITIALIZED"))?;
        // Qurilmaning o'z tili bo'lsa — summa va PDF'lar shu tilda.
        let device_locale = self
            .db
            .read(|c| household::device_locale(c, &self.device_id))?;
        let tag = device_locale.as_deref().unwrap_or(&h.locale);
        Ok(Ctx {
            household_id: h.id,
            locale: Locale::from_tag(tag).unwrap_or(Locale::Uz),
            currency: Currency::from_code(&h.base_currency)?,
            tz: h.tz.parse().unwrap_or(baraka_domain_common::DEFAULT_TZ),
            month_start_day: h.month_start_day,
        })
    }

    /// Makon shu xonadonga tegishli ekanini tekshiradi va `SpaceScope` qaytaradi. Sotuvchi
    /// qurilmasida umumiy use-case'lar yopiq — unga faqat `kk_scope_seller` orqali (K8).
    pub(crate) fn scope(&self, ctx: &Ctx, space_id: &str) -> Result<SpaceScope, AppError> {
        if self.access(ctx)?.role == crate::access::Role::Seller {
            return Err(AppError::new("ROLE_FORBIDDEN"));
        }
        self.space_scope(ctx, space_id)
    }

    /// Rolni tekshirmasdan (rol tekshiruvi chaqiruvchida).
    pub(crate) fn space_scope(&self, ctx: &Ctx, space_id: &str) -> Result<SpaceScope, AppError> {
        let spaces = self
            .db
            .read(|c| household::list_spaces(c, &ctx.household_id))?;
        if spaces.iter().any(|s| s.id == space_id) {
            Ok(SpaceScope {
                household_id: ctx.household_id.clone(),
                space_id: space_id.to_string(),
            })
        } else {
            Err(AppError::on("SPACE_NOT_FOUND", "spaceId"))
        }
    }

    pub(crate) fn today(&self, ctx: &Ctx) -> NaiveDate {
        local_date(self.clock.now(), ctx.tz)
    }

    pub(crate) fn date_or_today(
        &self,
        ctx: &Ctx,
        s: Option<&str>,
        field: &str,
    ) -> Result<NaiveDate, AppError> {
        match s {
            None => Ok(self.today(ctx)),
            Some(t) => NaiveDate::parse_from_str(t, "%Y-%m-%d")
                .map_err(|_| AppError::on("INVALID_DATE", field)),
        }
    }

    pub(crate) fn money_dto(&self, ctx: &Ctx, m: Money) -> MoneyDto {
        MoneyDto {
            minor: m.minor().to_string(),
            currency: m.currency().code().to_string(),
            formatted: format(m, ctx.locale),
            plain: format_plain(m.minor(), m.currency()),
        }
    }

    pub fn is_initialized(&self) -> Result<bool, AppError> {
        Ok(self.db.read(household::get_household)?.is_some())
    }

    /// Birinchi ishga tushirish: xonadon, shu qurilma, makonlar, a'zolar, standart kategoriyalar,
    /// har bir makon uchun QOROVUL jamg'armasi va 5% avto-ulush qoidasi.
    pub fn bootstrap(&self, input: BootstrapInput) -> Result<HouseholdDto, AppError> {
        if self.is_initialized()? {
            return Err(AppError::new("ALREADY_INITIALIZED"));
        }
        let name = required(&input.household_name, "householdName")?;
        let device_name = required(&input.device_name, "deviceName")?;
        Locale::from_tag(&input.locale).ok_or(AppError::on("INVALID_LOCALE", "locale"))?;
        let currency = Currency::from_code(&input.base_currency)?;
        if !(1..=28).contains(&input.month_start_day) {
            return Err(AppError::on("INVALID_MONTH_START_DAY", "monthStartDay"));
        }
        let kinds: Vec<SpaceKind> = input
            .spaces
            .iter()
            .map(|k| SpaceKind::parse(k).ok_or(AppError::on("INVALID_SPACE_KIND", "spaces")))
            .collect::<Result<_, _>>()?;
        if kinds.is_empty() {
            return Err(AppError::on("REQUIRED", "spaces"));
        }
        let mut members = Vec::new();
        for m in &input.members {
            let role = MemberRole::parse(&m.role).ok_or(AppError::on("INVALID_ROLE", "members"))?;
            members.push((self.new_id(), required(&m.display_name, "members")?, role));
        }
        if !members.iter().any(|(_, _, r)| *r == MemberRole::Adult) {
            return Err(AppError::on("ADULT_REQUIRED", "members"));
        }
        let rhythm = crate::settings::parse_rhythm(input.income_rhythm.as_deref())?;

        let hid = self.new_id();
        let meta = self.meta();
        let locale_tag = input.locale.clone();
        let platform = clean_opt(Some(&input.platform)).unwrap_or_else(|| "unknown".to_string());
        let space_rows: Vec<(String, SpaceKind)> =
            kinds.iter().map(|k| (self.new_id(), *k)).collect();
        let cat_ids: Vec<Vec<String>> = space_rows
            .iter()
            .map(|(_, k)| {
                default_categories(*k)
                    .iter()
                    .map(|_| self.new_id())
                    .collect()
            })
            .collect();
        let extra_ids: Vec<(String, String, Vec<String>)> = space_rows
            .iter()
            .map(|_| {
                (
                    self.new_id(),
                    self.new_id(),
                    members.iter().map(|_| self.new_id()).collect(),
                )
            })
            .collect();

        self.db.write(|tx| {
            household::insert_household(
                tx,
                &household::HouseholdRow {
                    id: hid.clone(),
                    name: name.clone(),
                    base_currency: currency.code().to_string(),
                    locale: locale_tag.clone(),
                    tz: baraka_domain_common::DEFAULT_TZ.name().to_string(),
                    month_start_day: input.month_start_day,
                },
                &meta,
            )?;
            household::set_prefs(tx, &hid, rhythm, input.debts_declared, &meta)?;
            household::insert_device(tx, &hid, &device_name, &platform, &meta)?;
            for (id, display_name, role) in &members {
                household::insert_member(
                    tx,
                    &household::MemberRow {
                        id: id.clone(),
                        household_id: hid.clone(),
                        display_name: display_name.clone(),
                        role: role.as_str().to_string(),
                    },
                    &meta,
                )?;
            }
            for (i, (sid, kind)) in space_rows.iter().enumerate() {
                household::insert_space(
                    tx,
                    &household::SpaceRow {
                        id: sid.clone(),
                        household_id: hid.clone(),
                        kind: kind.as_str().to_string(),
                        name: kind.as_str().to_string(),
                    },
                    &meta,
                )?;
                let scope = SpaceScope {
                    household_id: hid.clone(),
                    space_id: sid.clone(),
                };
                for (j, ((key, necessity), cid)) in default_categories(*kind)
                    .iter()
                    .zip(&cat_ids[i])
                    .enumerate()
                {
                    categories::insert(
                        tx,
                        &scope,
                        &categories::CategoryRow {
                            id: cid.clone(),
                            name_key: (*key).to_string(),
                            custom_name: None,
                            default_necessity: necessity.map(str::to_string),
                            is_system: true,
                            sort_order: i64::try_from(j).unwrap_or(i64::MAX),
                            version: 1,
                        },
                        &meta,
                    )?;
                }
                let (vault_id, rule_id, member_link_ids) = &extra_ids[i];
                assets::insert(
                    tx,
                    &scope,
                    &assets::AssetRow {
                        id: vault_id.clone(),
                        asset_type: "VAULT".to_string(),
                        name: "vault.kelajagim".to_string(),
                        unit: currency.code().to_string(),
                        currency: Some(currency.code().to_string()),
                        vault_type: Some(VaultType::Qorovul.as_str().to_string()),
                        owner_member_id: None,
                        visibility: "SHARED".to_string(),
                    },
                    &meta,
                )?;
                rules::insert(
                    tx,
                    &scope,
                    &rules::AllocationRuleRow {
                        id: rule_id.clone(),
                        kind: "PERCENT".to_string(),
                        bp: Some(DEFAULT_SHARE_BP),
                        amount_minor: None,
                        currency: None,
                        progressive: true,
                    },
                    &meta,
                )?;
                for ((mid, _, _), link_id) in members.iter().zip(member_link_ids) {
                    household::add_member_to_space(tx, link_id, &hid, sid, mid, &meta)?;
                }
            }
            Ok(())
        })?;
        self.publish(None, &[Topic::Household]);
        self.household()
    }

    pub fn household(&self) -> Result<HouseholdDto, AppError> {
        let h = self
            .db
            .read(household::get_household)?
            .ok_or(AppError::new("NOT_INITIALIZED"))?;
        let spaces = self.db.read(|c| household::list_spaces(c, &h.id))?;
        let members = self.db.read(|c| household::list_members(c, &h.id))?;
        Ok(HouseholdDto {
            id: h.id,
            name: h.name,
            locale: h.locale,
            base_currency: h.base_currency,
            month_start_day: h.month_start_day,
            spaces: spaces
                .into_iter()
                .map(|s| SpaceDto {
                    id: s.id,
                    kind: s.kind,
                    name: s.name,
                })
                .collect(),
            members: members
                .into_iter()
                .map(|m| MemberDto {
                    id: m.id,
                    display_name: m.display_name,
                    role: m.role,
                })
                .collect(),
        })
    }

    pub fn categories(&self, space_id: &str) -> Result<Vec<CategoryDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let rows = self.db.read(|c| categories::list(c, &scope))?;
        Ok(rows
            .into_iter()
            .map(|r| CategoryDto {
                id: r.id,
                name_key: r.name_key,
                custom_name: r.custom_name,
                default_necessity: r.default_necessity,
                is_system: r.is_system,
            })
            .collect())
    }

    pub fn add_category(
        &self,
        space_id: &str,
        name: &str,
        default_necessity: Option<&str>,
    ) -> Result<CategoryDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let name = required(name, "name")?;
        let necessity = parse_necessity(default_necessity)?;
        let row = categories::CategoryRow {
            id: self.new_id(),
            name_key: "category.custom".to_string(),
            custom_name: Some(name),
            default_necessity: necessity.map(|n| n.as_str().to_string()),
            is_system: false,
            sort_order: 1_000,
            version: 1,
        };
        let meta = self.meta();
        self.db
            .write(|tx| categories::insert(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Categories]);
        Ok(CategoryDto {
            id: row.id,
            name_key: row.name_key,
            custom_name: row.custom_name,
            default_necessity: row.default_necessity,
            is_system: false,
        })
    }

    pub fn rename_category(
        &self,
        space_id: &str,
        category_id: &str,
        name: &str,
    ) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let name = required(name, "name")?;
        let meta = self.meta();
        self.db
            .write(|tx| categories::rename(tx, &scope, category_id, &name, &meta))?;
        self.publish(Some(space_id), &[Topic::Categories]);
        Ok(())
    }

    pub fn set_category_necessity(
        &self,
        space_id: &str,
        category_id: &str,
        necessity: Option<&str>,
    ) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let necessity = parse_necessity(necessity)?;
        let meta = self.meta();
        self.db.write(|tx| {
            categories::set_default_necessity(
                tx,
                &scope,
                category_id,
                necessity.map(Necessity::as_str),
                &meta,
            )
        })?;
        self.publish(Some(space_id), &[Topic::Categories]);
        Ok(())
    }

    pub fn delete_category(&self, space_id: &str, category_id: &str) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let meta = self.meta();
        self.db
            .write(|tx| categories::soft_delete(tx, &scope, category_id, &meta))?;
        self.publish(Some(space_id), &[Topic::Categories]);
        Ok(())
    }
}

pub(crate) fn parse_necessity(s: Option<&str>) -> Result<Option<Necessity>, AppError> {
    match s {
        None => Ok(None),
        Some(t) => Necessity::parse(t)
            .map(Some)
            .ok_or(AppError::on("INVALID_NECESSITY", "necessity")),
    }
}
