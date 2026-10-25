//! Token Vault: provisioning, ID&V, LUK, lifecycle, detokenizatsiya.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};

use mpay_common::clock::Clock;
use mpay_common::emv;
use mpay_common::ports::{
    ConsumeOutcome, IdvDecider, IdvDecision, IdvRequest, LukStatus, TokenState, TokenView,
};
use mpay_common::{CardExpiry, DeviceId, Pan, PanFingerprint, PanKind, TokenId};
use mpay_crypto::envelope::{Dek, Sealed, WrappedDek};
use mpay_crypto::index::pan_fingerprint;
use mpay_crypto::keystore::{KeyLabel, KeyStore};
use mpay_crypto::scheme::CryptogramScheme;
use mpay_crypto::{ct_eq, rng};
use serde_json::json;
use sqlx::sqlite::SqliteRow;
use sqlx::{Row, Sqlite, SqlitePool, Transaction};
use time::OffsetDateTime;

use crate::audit::{self, AuditEntry, AuditReport};
use crate::model::{
    DeviceContext, LukGrant, ProvisionOutcome, ProvisionRequest, TokenProfile, TokenSummary,
    VaultConfig,
};
use crate::VaultError;

const ACTOR_DEVICE: &str = "device";

/// Token Vault.
pub struct Vault {
    db: SqlitePool,
    ks: Arc<dyn KeyStore>,
    scheme: Arc<dyn CryptogramScheme>,
    idv: Arc<dyn IdvDecider>,
    clock: Arc<dyn Clock>,
    cfg: VaultConfig,
    kek: KeyLabel,
    imk: KeyLabel,
    pan_idx: KeyLabel,
    active_dek: String,
    deks: RwLock<HashMap<String, Arc<Dek>>>,
    /// SQLite yozuvlarini (va audit zanjirini) ketma-ketlashtiradi.
    write: tokio::sync::Mutex<()>,
}

impl std::fmt::Debug for Vault {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Vault")
            .field("active_dek", &self.active_dek)
            .finish_non_exhaustive()
    }
}

fn new_id(prefix: &str) -> Result<String, VaultError> {
    Ok(format!("{prefix}{}", hex::encode(rng::array::<16>()?)))
}

fn state_of(row: &SqliteRow) -> Result<TokenState, VaultError> {
    let s: String = row.try_get("state")?;
    TokenState::parse(&s).ok_or(VaultError::Db("noma'lum holat".into()))
}

/// Joriy sanaga `months` qo'shadi va karta muddati bilan cheklaydi.
fn token_expiry(now: OffsetDateTime, months: u32, card: CardExpiry) -> CardExpiry {
    let total = u32::from(now.month() as u8) - 1 + months;
    let year = (now.year() as u32 + total / 12).min(2099) as u16;
    let month = (total % 12 + 1) as u8;
    let candidate = CardExpiry { year, month };
    candidate.min(card)
}

impl Vault {
    /// Vault'ni ochadi: migratsiyalar, faol DEK (yo'q bo'lsa yaratiladi).
    pub async fn open(
        db: SqlitePool,
        ks: Arc<dyn KeyStore>,
        scheme: Arc<dyn CryptogramScheme>,
        idv: Arc<dyn IdvDecider>,
        clock: Arc<dyn Clock>,
        cfg: VaultConfig,
    ) -> Result<Self, VaultError> {
        cfg.luk
            .validate()
            .map_err(|_| VaultError::BadRequest("luk siyosati"))?;
        let bin: u32 = cfg
            .token_bin
            .parse()
            .map_err(|_| VaultError::BadRequest("token_bin"))?;
        if cfg.token_bin.len() != 6 || !mpay_common::pan::DPAN_BIN_RANGE.contains(&bin) {
            return Err(VaultError::BadRequest(
                "token_bin DPAN diapazonida emas (990050–990099)",
            ));
        }
        crate::db::migrate(&db).await?;
        let kek = KeyLabel::new(KeyLabel::KEK);
        let mut v = Self {
            db,
            ks,
            scheme,
            idv,
            clock,
            cfg,
            kek,
            imk: KeyLabel::new(KeyLabel::IMK_AC),
            pan_idx: KeyLabel::new(KeyLabel::PAN_INDEX),
            active_dek: String::new(),
            deks: RwLock::new(HashMap::new()),
            write: tokio::sync::Mutex::new(()),
        };
        v.active_dek = v.ensure_active_dek().await?;
        Ok(v)
    }

    pub fn pool(&self) -> &SqlitePool {
        &self.db
    }

    pub fn config(&self) -> &VaultConfig {
        &self.cfg
    }

    async fn ensure_active_dek(&self) -> Result<String, VaultError> {
        if let Some(r) = sqlx::query(
            "SELECT dek_id FROM vault_deks WHERE active = 1 ORDER BY created_at DESC LIMIT 1",
        )
        .fetch_optional(&self.db)
        .await?
        {
            let id: String = r.try_get("dek_id")?;
            self.dek(&id).await?; // KEK bilan ochilishini darhol tekshiramiz
            return Ok(id);
        }
        let dek = Dek::generate(new_id("dek_")?)?;
        let w = dek.wrap(self.ks.as_ref(), &self.kek)?;
        let _g = self.write.lock().await;
        let mut tx = crate::db::begin_write(&self.db).await?;
        sqlx::query("INSERT INTO vault_deks (dek_id, kek_label, nonce, wrapped, created_at, active) VALUES (?, ?, ?, ?, ?, 1)")
            .bind(&w.dek_id)
            .bind(&w.kek_label)
            .bind(w.nonce.as_slice())
            .bind(&w.ciphertext)
            .bind(self.clock.unix())
            .execute(&mut *tx)
            .await?;
        audit::append(
            &mut tx,
            self.clock.unix(),
            &AuditEntry {
                actor: "system",
                action: "DEK_CREATED",
                token_id: None,
                details: json!({ "dek_id": w.dek_id, "kek": w.kek_label }),
            },
        )
        .await?;
        tx.commit().await?;
        let id = dek.id().to_owned();
        self.deks
            .write()
            .map_err(|_| VaultError::Db("lock".into()))?
            .insert(id.clone(), Arc::new(dek));
        tracing::info!(dek_id = %id, "vault: yangi DEK yaratildi");
        Ok(id)
    }

    async fn dek(&self, id: &str) -> Result<Arc<Dek>, VaultError> {
        if let Some(d) = self
            .deks
            .read()
            .map_err(|_| VaultError::Db("lock".into()))?
            .get(id)
        {
            return Ok(d.clone());
        }
        let r = sqlx::query(
            "SELECT dek_id, kek_label, nonce, wrapped FROM vault_deks WHERE dek_id = ?",
        )
        .bind(id)
        .fetch_optional(&self.db)
        .await?
        .ok_or(VaultError::Db("DEK topilmadi".into()))?;
        let nonce: Vec<u8> = r.try_get("nonce")?;
        let w = WrappedDek {
            dek_id: r.try_get("dek_id")?,
            kek_label: r.try_get("kek_label")?,
            nonce: nonce
                .try_into()
                .map_err(|_| VaultError::Db("DEK nonce".into()))?,
            ciphertext: r.try_get("wrapped")?,
        };
        let dek = Arc::new(Dek::unwrap(self.ks.as_ref(), &w)?);
        self.deks
            .write()
            .map_err(|_| VaultError::Db("lock".into()))?
            .insert(id.to_owned(), dek.clone());
        Ok(dek)
    }

    async fn seal_pan(&self, aad: &str, pan: &Pan) -> Result<Sealed, VaultError> {
        let dek = self.dek(&self.active_dek).await?;
        Ok(dek.seal(aad.as_bytes(), pan.expose_digits().as_bytes())?)
    }

    async fn open_pan(
        &self,
        dek_id: String,
        nonce: Vec<u8>,
        ct: Vec<u8>,
        aad: &str,
    ) -> Result<Pan, VaultError> {
        let dek = self.dek(&dek_id).await?;
        let sealed = Sealed {
            dek_id,
            nonce: nonce
                .try_into()
                .map_err(|_| VaultError::Db("nonce".into()))?,
            ciphertext: ct,
        };
        let pt = dek.open(aad.as_bytes(), &sealed)?;
        let s = std::str::from_utf8(&pt).map_err(|_| VaultError::Db("PAN kodlash".into()))?;
        Pan::parse(s).map_err(|_| VaultError::Db("PAN yaroqsiz".into()))
    }

    fn fingerprint(&self, pan: &Pan) -> Result<PanFingerprint, VaultError> {
        Ok(pan_fingerprint(self.ks.as_ref(), &self.pan_idx, pan)?)
    }

    fn otp_for(&self, challenge_id: &str) -> Result<String, VaultError> {
        let mac = self.ks.hmac_sha256(
            &self.pan_idx,
            &[b"MPAY-OTP-V1\x00".as_slice(), challenge_id.as_bytes()].concat(),
        )?;
        let n = u32::from_be_bytes([mac[0], mac[1], mac[2], mac[3]]) % 1_000_000;
        Ok(format!("{n:06}"))
    }

    // ------------------------------------------------------------------ provisioning

    /// `POST /v1/tokens` — ID&V qaroriga ko'ra token yaratadi.
    pub async fn provision(
        &self,
        req: ProvisionRequest,
        dev: DeviceContext,
    ) -> Result<ProvisionOutcome, VaultError> {
        // ID&V hisoblari yozish qulfidan tashqarida o'qiladi (Shield sekin bo'lishi mumkin) va qulf
        // ostida qayta tekshiriladi; bir vaqtdagi so'rov ularni o'zgartirgan bo'lsa — qaror qaytadan.
        for _ in 0..3 {
            if let Some(out) = self.provision_attempt(&req, &dev).await? {
                return Ok(out);
            }
        }
        Err(VaultError::IdvUnavailable(
            "bir vaqtdagi provisioning so'rovlari — qayta urinib ko'ring".into(),
        ))
    }

    /// Kartaning va qurilmaning "tirik" tokenlari: `DELETED` va tashlab ketilgan `PENDING_IDV`
    /// (challenge'i muddati o'tgan, bloklangan yoki ishlatilgan) hisoblanmaydi.
    async fn token_counts<'e, E>(
        &self,
        exec: E,
        pan_fp: &PanFingerprint,
        dev_hex: &str,
        now: i64,
    ) -> Result<(i64, i64), VaultError>
    where
        E: sqlx::Executor<'e, Database = Sqlite>,
    {
        let r = sqlx::query(
            "SELECT \
               COALESCE(SUM(CASE WHEN c.pan_fp = ? THEN 1 ELSE 0 END), 0) AS for_pan, \
               COALESCE(SUM(CASE WHEN t.device_id = ? THEN 1 ELSE 0 END), 0) AS for_dev \
             FROM vault_tokens t JOIN vault_cards c ON c.card_id = t.card_id \
             WHERE (c.pan_fp = ? OR t.device_id = ?) AND t.state != 'DELETED' \
               AND NOT (t.state = 'PENDING_IDV' AND NOT EXISTS ( \
                 SELECT 1 FROM vault_idv_challenges ch WHERE ch.token_id = t.token_id \
                   AND ch.consumed = 0 AND ch.expires_at > ? AND ch.attempts < ?))",
        )
        .bind(pan_fp.0.as_slice())
        .bind(dev_hex)
        .bind(pan_fp.0.as_slice())
        .bind(dev_hex)
        .bind(now)
        .bind(self.cfg.otp_max_attempts)
        .fetch_one(exec)
        .await?;
        Ok((r.try_get("for_pan")?, r.try_get("for_dev")?))
    }

    /// Bitta urinish; `None` — hisoblar ID&V'dan keyin o'zgardi (qayta urinish kerak).
    async fn provision_attempt(
        &self,
        req: &ProvisionRequest,
        dev: &DeviceContext,
    ) -> Result<Option<ProvisionOutcome>, VaultError> {
        if req.fpan.kind() != PanKind::Funding {
            return Err(VaultError::BadRequest("FPAN kutilgan (990000–990049)"));
        }
        let now = self.clock.now();
        if req
            .expiry
            .is_expired_at(now.year() as u16, now.month() as u8)
        {
            return Err(VaultError::BadRequest("karta muddati o'tgan"));
        }
        let pan_fp = self.fingerprint(&req.fpan)?;
        let dev_hex = dev.device_id.to_hex();

        let (existing_for_pan, existing_for_device) = self
            .token_counts(&self.db, &pan_fp, &dev_hex, now.unix_timestamp())
            .await?;
        if existing_for_device >= i64::from(self.cfg.max_tokens_per_device) {
            return Err(VaultError::TooManyTokens);
        }

        let idv = self
            .idv
            .decide(&IdvRequest {
                fpan: req.fpan.clone(),
                pan_fingerprint: pan_fp,
                device_id: dev.device_id,
                attestation_level: dev.security_level,
                existing_tokens_for_pan: existing_for_pan as u32,
                existing_tokens_for_device: existing_for_device as u32,
                at: now,
            })
            .await
            .map_err(|e| VaultError::IdvUnavailable(e.to_string()))?;
        tracing::info!(fpan = %req.fpan.masked(), device = %dev.device_id, decision = ?idv.decision, score = idv.score, "vault: ID&V qarori");

        if idv.decision == IdvDecision::Red {
            let _g = self.write.lock().await;
            let mut tx = crate::db::begin_write(&self.db).await?;
            audit::append(
                &mut tx,
                now.unix_timestamp(),
                &AuditEntry {
                    actor: ACTOR_DEVICE,
                    action: "PROVISION_DECLINED",
                    token_id: None,
                    details: json!({ "fpan": req.fpan.masked(), "device_id": dev_hex, "score": idv.score, "reasons": idv.reasons }),
                },
            )
            .await?;
            tx.commit().await?;
            return Ok(Some(ProvisionOutcome::Declined { idv }));
        }

        // Kriptografik tayyorgarlik yozish qulfidan tashqarida.
        let dpan = self.generate_dpan().await?;
        let dpan_fp = self.fingerprint(&dpan)?;
        let token_id = TokenId::from_random(rng::array::<16>()?);
        let dpan_exp = token_expiry(now, self.cfg.token_validity_months, req.expiry);
        let psn = 0u8;
        let dpan_sealed = self
            .seal_pan(&format!("token:{token_id}:dpan"), &dpan)
            .await?;
        let state = if idv.decision == IdvDecision::Green {
            TokenState::Active
        } else {
            TokenState::PendingIdv
        };
        let ts = now.unix_timestamp();

        let _g = self.write.lock().await;
        let mut tx = crate::db::begin_write(&self.db).await?;
        // Qulf ostida qayta sanash: ID&V ko'rgan holat o'zgargan bo'lsa (bir vaqtdagi so'rov) — qaytadan.
        if self.token_counts(&mut *tx, &pan_fp, &dev_hex, ts).await?
            != (existing_for_pan, existing_for_device)
        {
            tracing::info!(fpan = %req.fpan.masked(), "vault: bir vaqtdagi provisioning — ID&V qaytadan");
            return Ok(None);
        }
        let card_id = self.upsert_card(&mut tx, req, &pan_fp, ts).await?;
        sqlx::query(
            "INSERT INTO vault_tokens (token_id, card_id, device_id, dpan_fp, dpan_dek, dpan_nonce, dpan_ct, dpan_masked, \
             dpan_expiry, psn, state, idv_decision, idv_score, last_atc, next_luk_seq, created_at, updated_at) \
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 1, ?, ?)",
        )
        .bind(token_id.as_str())
        .bind(&card_id)
        .bind(&dev_hex)
        .bind(dpan_fp.0.as_slice())
        .bind(&dpan_sealed.dek_id)
        .bind(dpan_sealed.nonce.as_slice())
        .bind(&dpan_sealed.ciphertext)
        .bind(dpan.masked())
        .bind(dpan_exp.to_yymm())
        .bind(i64::from(psn))
        .bind(state.as_str())
        .bind(format!("{:?}", idv.decision).to_uppercase())
        .bind(i64::from(idv.score))
        .bind(ts)
        .bind(ts)
        .execute(&mut *tx)
        .await?;
        audit::append(
            &mut tx,
            ts,
            &AuditEntry {
                actor: ACTOR_DEVICE,
                action: "TOKEN_CREATED",
                token_id: Some(token_id.as_str()),
                details: json!({
                    "fpan": req.fpan.masked(), "dpan": dpan.masked(), "device_id": dev_hex,
                    "state": state.as_str(), "idv": idv.decision, "score": idv.score, "reasons": idv.reasons,
                }),
            },
        )
        .await?;

        let outcome = if state == TokenState::Active {
            let luks = self
                .issue_luks_tx(&mut tx, &token_id, &dpan, psn, self.cfg.luk.batch_size, ts)
                .await?;
            ProvisionOutcome::Active {
                profile: self.profile(token_id.clone(), dpan.clone(), dpan_exp, psn, luks),
                idv,
            }
        } else {
            let challenge_id = new_id("chl_")?;
            let exp = ts + self.cfg.otp_ttl_secs;
            sqlx::query("INSERT INTO vault_idv_challenges (challenge_id, token_id, expires_at) VALUES (?, ?, ?)")
                .bind(&challenge_id)
                .bind(token_id.as_str())
                .bind(exp)
                .execute(&mut *tx)
                .await?;
            audit::append(
                &mut tx,
                ts,
                &AuditEntry {
                    actor: ACTOR_DEVICE,
                    action: "IDV_CHALLENGE_CREATED",
                    token_id: Some(token_id.as_str()),
                    details: json!({ "challenge_id": challenge_id, "expires_at": exp }),
                },
            )
            .await?;
            ProvisionOutcome::PendingIdv {
                token_id: token_id.clone(),
                challenge_id,
                otp_expires_at: exp,
                idv,
            }
        };
        tx.commit().await?;
        tracing::info!(token_id = %token_id, dpan = %dpan.masked(), state = state.as_str(), "vault: token yaratildi");
        Ok(Some(outcome))
    }

    async fn upsert_card(
        &self,
        tx: &mut Transaction<'_, Sqlite>,
        req: &ProvisionRequest,
        pan_fp: &PanFingerprint,
        ts: i64,
    ) -> Result<String, VaultError> {
        if let Some(r) = sqlx::query("SELECT card_id FROM vault_cards WHERE pan_fp = ?")
            .bind(pan_fp.0.as_slice())
            .fetch_optional(&mut **tx)
            .await?
        {
            return Ok(r.try_get("card_id")?);
        }
        let card_id = new_id("crd_")?;
        let sealed = self
            .seal_pan(&format!("card:{card_id}:pan"), &req.fpan)
            .await?;
        sqlx::query(
            "INSERT INTO vault_cards (card_id, pan_fp, pan_dek, pan_nonce, pan_ct, pan_masked, expiry, created_at) \
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        )
        .bind(&card_id)
        .bind(pan_fp.0.as_slice())
        .bind(&sealed.dek_id)
        .bind(sealed.nonce.as_slice())
        .bind(&sealed.ciphertext)
        .bind(req.fpan.masked())
        .bind(req.expiry.to_yymm())
        .bind(ts)
        .execute(&mut **tx)
        .await?;
        Ok(card_id)
    }

    async fn generate_dpan(&self) -> Result<Pan, VaultError> {
        for _ in 0..8 {
            let acct = rng::below(1_000_000_000)?;
            let dpan = Pan::from_prefix(&format!("{}{acct:09}", self.cfg.token_bin))
                .map_err(|_| VaultError::BadRequest("DPAN generatsiyasi"))?;
            let fp = self.fingerprint(&dpan)?;
            let taken = sqlx::query("SELECT 1 FROM vault_tokens WHERE dpan_fp = ?")
                .bind(fp.0.as_slice())
                .fetch_optional(&self.db)
                .await?
                .is_some();
            if !taken {
                return Ok(dpan);
            }
        }
        Err(VaultError::Db("DPAN to'qnashuvi".into()))
    }

    fn profile(
        &self,
        token_id: TokenId,
        dpan: Pan,
        exp: CardExpiry,
        psn: u8,
        luks: Vec<LukGrant>,
    ) -> TokenProfile {
        TokenProfile {
            token_id,
            dpan,
            dpan_expiry: exp.to_yymm(),
            psn,
            aid: hex::encode_upper(emv::AID),
            scheme: self.scheme.name().to_owned(),
            luks,
        }
    }

    async fn issue_luks_tx(
        &self,
        tx: &mut Transaction<'_, Sqlite>,
        token_id: &TokenId,
        dpan: &Pan,
        psn: u8,
        count: u32,
        ts: i64,
    ) -> Result<Vec<LukGrant>, VaultError> {
        let next: i64 = sqlx::query("SELECT next_luk_seq FROM vault_tokens WHERE token_id = ?")
            .bind(token_id.as_str())
            .fetch_one(&mut **tx)
            .await?
            .try_get("next_luk_seq")?;
        let first = u32::try_from(next).map_err(|_| VaultError::Db("LUK seq".into()))?;
        let last = first.checked_add(count).ok_or(VaultError::TooManyLuks)?;
        let mk = self
            .scheme
            .token_master_key(self.ks.as_ref(), &self.imk, dpan, psn)?;
        let expires = ts + self.cfg.luk.ttl_secs as i64;
        let mut out = Vec::with_capacity(count as usize);
        for seq in first..last {
            sqlx::query("INSERT INTO vault_luks (token_id, seq, issued_at, expires_at, max_uses) VALUES (?, ?, ?, ?, ?)")
                .bind(token_id.as_str())
                .bind(i64::from(seq))
                .bind(ts)
                .bind(expires)
                .bind(i64::from(self.cfg.luk.max_uses))
                .execute(&mut **tx)
                .await?;
            out.push(LukGrant {
                seq,
                key: self.scheme.luk(&mk, seq),
                issued_at: ts,
                expires_at: expires,
                max_uses: self.cfg.luk.max_uses,
            });
        }
        drop(mk);
        sqlx::query("UPDATE vault_tokens SET next_luk_seq = ?, updated_at = ? WHERE token_id = ?")
            .bind(i64::from(last))
            .bind(ts)
            .bind(token_id.as_str())
            .execute(&mut **tx)
            .await?;
        audit::append(
            tx,
            ts,
            &AuditEntry {
                actor: "vault",
                action: "LUKS_ISSUED",
                token_id: Some(token_id.as_str()),
                details: json!({ "from_seq": first, "to_seq": last - 1, "expires_at": expires, "max_uses": self.cfg.luk.max_uses }),
            },
        )
        .await?;
        Ok(out)
    }

    async fn token_row(&self, token_id: &TokenId) -> Result<SqliteRow, VaultError> {
        sqlx::query(
            "SELECT t.*, c.pan_masked, c.expiry AS card_expiry, c.pan_fp, c.pan_dek, c.pan_nonce, c.pan_ct \
             FROM vault_tokens t JOIN vault_cards c ON c.card_id = t.card_id WHERE t.token_id = ?",
        )
        .bind(token_id.as_str())
        .fetch_optional(&self.db)
        .await?
        .ok_or(VaultError::TokenNotFound)
    }

    async fn dpan_of(&self, row: &SqliteRow) -> Result<Pan, VaultError> {
        let token_id: String = row.try_get("token_id")?;
        self.open_pan(
            row.try_get("dpan_dek")?,
            row.try_get("dpan_nonce")?,
            row.try_get("dpan_ct")?,
            &format!("token:{token_id}:dpan"),
        )
        .await
    }

    fn check_device(row: &SqliteRow, dev: &DeviceContext) -> Result<(), VaultError> {
        let bound: String = row.try_get("device_id")?;
        if !ct_eq(bound.as_bytes(), dev.device_id.to_hex().as_bytes()) {
            return Err(VaultError::DeviceMismatch);
        }
        Ok(())
    }

    /// YELLOW: OTP'ni tekshiradi va tokenni faollashtiradi.
    pub async fn verify_otp(
        &self,
        token_id: &TokenId,
        challenge_id: &str,
        otp: &str,
        dev: DeviceContext,
    ) -> Result<TokenProfile, VaultError> {
        let row = self.token_row(token_id).await?;
        Self::check_device(&row, &dev)?;
        let st = state_of(&row)?;
        if st != TokenState::PendingIdv {
            return Err(VaultError::InvalidState {
                from: st.as_str(),
                to: TokenState::Active.as_str(),
            });
        }
        let dpan = self.dpan_of(&row).await?;
        let psn = row.try_get::<i64, _>("psn")? as u8;
        let exp = CardExpiry::parse_yymm(&row.try_get::<String, _>("dpan_expiry")?)
            .ok_or(VaultError::Db("muddat".into()))?;
        let expected = self.otp_for(challenge_id)?;
        let ts = self.clock.unix();

        let _g = self.write.lock().await;
        let mut tx = crate::db::begin_write(&self.db).await?;
        let ch = sqlx::query(
            "SELECT * FROM vault_idv_challenges WHERE challenge_id = ? AND token_id = ?",
        )
        .bind(challenge_id)
        .bind(token_id.as_str())
        .fetch_optional(&mut *tx)
        .await?
        .ok_or(VaultError::ChallengeNotFound)?;
        let attempts: i64 = ch.try_get("attempts")?;
        if ch.try_get::<i64, _>("consumed")? != 0 {
            return Err(VaultError::ChallengeNotFound);
        }
        if attempts >= self.cfg.otp_max_attempts {
            return Err(VaultError::OtpLocked);
        }
        if ch.try_get::<i64, _>("expires_at")? <= ts {
            return Err(VaultError::OtpExpired);
        }
        if !ct_eq(expected.as_bytes(), otp.as_bytes()) {
            sqlx::query(
                "UPDATE vault_idv_challenges SET attempts = attempts + 1 WHERE challenge_id = ?",
            )
            .bind(challenge_id)
            .execute(&mut *tx)
            .await?;
            audit::append(
                &mut tx,
                ts,
                &AuditEntry {
                    actor: ACTOR_DEVICE,
                    action: "IDV_OTP_FAILED",
                    token_id: Some(token_id.as_str()),
                    details: json!({ "challenge_id": challenge_id, "attempt": attempts + 1 }),
                },
            )
            .await?;
            tx.commit().await?;
            return Err(if attempts + 1 >= self.cfg.otp_max_attempts {
                VaultError::OtpLocked
            } else {
                VaultError::OtpInvalid
            });
        }
        sqlx::query("UPDATE vault_idv_challenges SET consumed = 1 WHERE challenge_id = ?")
            .bind(challenge_id)
            .execute(&mut *tx)
            .await?;
        self.set_state_tx(
            &mut tx,
            token_id,
            TokenState::Active,
            ACTOR_DEVICE,
            "IDV_OTP_VERIFIED",
            ts,
        )
        .await?;
        let luks = self
            .issue_luks_tx(&mut tx, token_id, &dpan, psn, self.cfg.luk.batch_size, ts)
            .await?;
        tx.commit().await?;
        Ok(self.profile(token_id.clone(), dpan, exp, psn, luks))
    }

    /// Sandbox: simulyatsiya qilingan OTP (haqiqiy tizimda SMS/push orqali yuboriladi).
    pub async fn sandbox_otp(&self, challenge_id: &str) -> Result<String, VaultError> {
        sqlx::query("SELECT 1 FROM vault_idv_challenges WHERE challenge_id = ? AND consumed = 0")
            .bind(challenge_id)
            .fetch_optional(&self.db)
            .await?
            .ok_or(VaultError::ChallengeNotFound)?;
        self.otp_for(challenge_id)
    }

    /// Qurilma so'rovi bilan LUK to'ldirish.
    /// Qurilma kalitini almashtirish (ADR-0015): eski qurilmaga bog'langan tokenlar yangisiga o'tadi.
    pub async fn rebind_device(&self, old: &DeviceId, new: &DeviceId) -> Result<u64, VaultError> {
        let ts = self.clock.unix();
        let _g = self.write.lock().await;
        let mut tx = crate::db::begin_write(&self.db).await?;
        let n = sqlx::query("UPDATE vault_tokens SET device_id = ? WHERE device_id = ?")
            .bind(new.to_hex())
            .bind(old.to_hex())
            .execute(&mut *tx)
            .await?
            .rows_affected();
        audit::append(
            &mut tx,
            ts,
            &AuditEntry {
                actor: ACTOR_DEVICE,
                action: "DEVICE_REKEY",
                token_id: None,
                details: json!({ "old_device": old.to_hex(), "new_device": new.to_hex(), "tokens": n }),
            },
        )
        .await?;
        tx.commit().await?;
        tracing::info!(old = %old, new = %new, tokens = n, "vault: qurilma kaliti almashtirildi");
        Ok(n)
    }

    pub async fn replenish_luks(
        &self,
        token_id: &TokenId,
        dev: DeviceContext,
    ) -> Result<Vec<LukGrant>, VaultError> {
        let row = self.token_row(token_id).await?;
        Self::check_device(&row, &dev)?;
        let st = state_of(&row)?;
        if st != TokenState::Active {
            return Err(VaultError::InvalidState {
                from: st.as_str(),
                to: "LUK_REPLENISH",
            });
        }
        let dpan = self.dpan_of(&row).await?;
        let psn = row.try_get::<i64, _>("psn")? as u8;
        let ts = self.clock.unix();
        let _g = self.write.lock().await;
        let mut tx = crate::db::begin_write(&self.db).await?;
        let active: i64 = sqlx::query(
            "SELECT COUNT(*) AS n FROM vault_luks WHERE token_id = ? AND revoked = 0 AND expires_at > ? AND used < max_uses",
        )
        .bind(token_id.as_str())
        .bind(ts)
        .fetch_one(&mut *tx)
        .await?
        .try_get("n")?;
        if active >= i64::from(self.cfg.luk.batch_size) * 2 {
            return Err(VaultError::TooManyLuks);
        }
        let luks = self
            .issue_luks_tx(&mut tx, token_id, &dpan, psn, self.cfg.luk.batch_size, ts)
            .await?;
        tx.commit().await?;
        Ok(luks)
    }

    async fn set_state_tx(
        &self,
        tx: &mut Transaction<'_, Sqlite>,
        token_id: &TokenId,
        to: TokenState,
        actor: &str,
        action: &str,
        ts: i64,
    ) -> Result<TokenState, VaultError> {
        let r = sqlx::query("SELECT state FROM vault_tokens WHERE token_id = ?")
            .bind(token_id.as_str())
            .fetch_optional(&mut **tx)
            .await?
            .ok_or(VaultError::TokenNotFound)?;
        let from = state_of(&r)?;
        let allowed = matches!(
            (from, to),
            (TokenState::Active, TokenState::Suspended)
                | (TokenState::Suspended, TokenState::Active)
                | (TokenState::PendingIdv, TokenState::Active)
                | (
                    TokenState::Active | TokenState::Suspended | TokenState::PendingIdv,
                    TokenState::Deleted
                )
        );
        if !allowed {
            return Err(VaultError::InvalidState {
                from: from.as_str(),
                to: to.as_str(),
            });
        }
        sqlx::query("UPDATE vault_tokens SET state = ?, updated_at = ? WHERE token_id = ?")
            .bind(to.as_str())
            .bind(ts)
            .bind(token_id.as_str())
            .execute(&mut **tx)
            .await?;
        if to == TokenState::Deleted {
            sqlx::query("UPDATE vault_luks SET revoked = 1 WHERE token_id = ?")
                .bind(token_id.as_str())
                .execute(&mut **tx)
                .await?;
        }
        audit::append(
            tx,
            ts,
            &AuditEntry {
                actor,
                action,
                token_id: Some(token_id.as_str()),
                details: json!({ "from": from.as_str(), "to": to.as_str() }),
            },
        )
        .await?;
        tracing::info!(token_id = %token_id, from = from.as_str(), to = to.as_str(), actor, "vault: holat o'zgardi");
        Ok(from)
    }

    async fn transition(
        &self,
        token_id: &TokenId,
        to: TokenState,
        actor: &str,
        action: &str,
    ) -> Result<TokenSummary, VaultError> {
        let ts = self.clock.unix();
        {
            let _g = self.write.lock().await;
            let mut tx = crate::db::begin_write(&self.db).await?;
            self.set_state_tx(&mut tx, token_id, to, actor, action, ts)
                .await?;
            tx.commit().await?;
        }
        self.summary(token_id).await
    }

    pub async fn suspend(
        &self,
        token_id: &TokenId,
        actor: &str,
    ) -> Result<TokenSummary, VaultError> {
        self.transition(token_id, TokenState::Suspended, actor, "TOKEN_SUSPENDED")
            .await
    }

    pub async fn resume(
        &self,
        token_id: &TokenId,
        actor: &str,
    ) -> Result<TokenSummary, VaultError> {
        self.transition(token_id, TokenState::Active, actor, "TOKEN_RESUMED")
            .await
    }

    pub async fn delete(
        &self,
        token_id: &TokenId,
        actor: &str,
    ) -> Result<TokenSummary, VaultError> {
        self.transition(token_id, TokenState::Deleted, actor, "TOKEN_DELETED")
            .await
    }

    /// Operator ko'rinishi (maskalangan).
    pub async fn summary(&self, token_id: &TokenId) -> Result<TokenSummary, VaultError> {
        let r = self.token_row(token_id).await?;
        let ts = self.clock.unix();
        let counts = sqlx::query(
            "SELECT COUNT(*) AS issued, \
             COALESCE(SUM(CASE WHEN revoked = 0 AND expires_at > ? AND used < max_uses THEN 1 ELSE 0 END), 0) AS active \
             FROM vault_luks WHERE token_id = ?",
        )
        .bind(ts)
        .bind(token_id.as_str())
        .fetch_one(&self.db)
        .await?;
        Ok(TokenSummary {
            token_id: token_id.clone(),
            state: state_of(&r)?,
            dpan_masked: r.try_get("dpan_masked")?,
            fpan_masked: r.try_get("pan_masked")?,
            dpan_expiry: r.try_get("dpan_expiry")?,
            device_id: r.try_get("device_id")?,
            idv_decision: r.try_get("idv_decision")?,
            luks_active: counts.try_get("active")?,
            luks_issued: counts.try_get("issued")?,
            last_atc: r.try_get("last_atc")?,
            created_at: r.try_get("created_at")?,
            updated_at: r.try_get("updated_at")?,
        })
    }

    /// Audit zanjirini tekshiradi.
    pub async fn verify_audit(&self) -> Result<AuditReport, VaultError> {
        audit::verify(&self.db).await
    }

    // ------------------------------------------------------------------ detokenizatsiya (ichki)

    fn luk_status(row: Option<&SqliteRow>, now: i64) -> Result<LukStatus, VaultError> {
        let Some(r) = row else {
            return Ok(LukStatus::Unknown);
        };
        if r.try_get::<i64, _>("revoked")? != 0 {
            return Ok(LukStatus::Unknown);
        }
        if r.try_get::<i64, _>("expires_at")? <= now {
            return Ok(LukStatus::Expired);
        }
        let used: i64 = r.try_get("used")?;
        let max: i64 = r.try_get("max_uses")?;
        if used >= max {
            return Ok(LukStatus::Exhausted);
        }
        Ok(LukStatus::Valid {
            remaining_uses: (max - used) as u32,
        })
    }

    pub(crate) async fn detok_lookup(
        &self,
        dpan: &Pan,
        luk_seq: u32,
        actor: &str,
    ) -> Result<Option<TokenView>, VaultError> {
        if dpan.kind() != PanKind::Device {
            return Ok(None);
        }
        let fp = self.fingerprint(dpan)?;
        let Some(row) = sqlx::query(
            "SELECT t.*, c.expiry AS card_expiry, c.pan_fp, c.pan_dek, c.pan_nonce, c.pan_ct, c.card_id AS cid \
             FROM vault_tokens t JOIN vault_cards c ON c.card_id = t.card_id WHERE t.dpan_fp = ?",
        )
        .bind(fp.0.as_slice())
        .fetch_optional(&self.db)
        .await?
        else {
            return Ok(None);
        };
        let token_id = TokenId::parse(&row.try_get::<String, _>("token_id")?)
            .ok_or(VaultError::Db("token_id".into()))?;
        let card_id: String = row.try_get("cid")?;
        let fpan = self
            .open_pan(
                row.try_get("pan_dek")?,
                row.try_get("pan_nonce")?,
                row.try_get("pan_ct")?,
                &format!("card:{card_id}:pan"),
            )
            .await?;
        let now = self.clock.unix();
        let luk_row = sqlx::query("SELECT * FROM vault_luks WHERE token_id = ? AND seq = ?")
            .bind(token_id.as_str())
            .bind(i64::from(luk_seq))
            .fetch_optional(&self.db)
            .await?;
        let luk = Self::luk_status(luk_row.as_ref(), now)?;
        let pan_fp: Vec<u8> = row.try_get("pan_fp")?;
        let parse_exp = |col: &str| -> Result<CardExpiry, VaultError> {
            CardExpiry::parse_yymm(&row.try_get::<String, _>(col)?)
                .ok_or(VaultError::Db("muddat".into()))
        };
        let view = TokenView {
            token_id: token_id.clone(),
            state: state_of(&row)?,
            fpan,
            fpan_expiry: parse_exp("card_expiry")?,
            dpan_expiry: parse_exp("dpan_expiry")?,
            psn: row.try_get::<i64, _>("psn")? as u8,
            device_id: DeviceId::from_hex(&row.try_get::<String, _>("device_id")?)
                .ok_or(VaultError::Db("device_id".into()))?,
            pan_fingerprint: PanFingerprint(
                pan_fp
                    .try_into()
                    .map_err(|_| VaultError::Db("pan_fp".into()))?,
            ),
            last_atc: row.try_get::<Option<i64>, _>("last_atc")?.map(|v| v as u16),
            luk,
        };
        // Audit yozuvi alohida yozish tranzaksiyasida emas: muvaffaqiyatli detokenizatsiya `detok_consume`
        // tranzaksiyasida (`DETOKENIZED` + LUK ishlatildi) qayd etiladi — har avtorizatsiya bitta commit.
        // Rad etilgan so'rovlar (noma'lum LUK, ARQC mos emas) emitentning `issuer_authorizations` jadvalida.
        tracing::debug!(actor, token_id = %token_id, dpan = %dpan.masked(), luk_seq, "vault: detokenizatsiya");
        Ok(Some(view))
    }

    pub(crate) async fn detok_consume(
        &self,
        token_id: &TokenId,
        luk_seq: u32,
        atc: u16,
        actor: &str,
    ) -> Result<ConsumeOutcome, VaultError> {
        let now = self.clock.unix();
        let _g = self.write.lock().await;
        let mut tx = crate::db::begin_write(&self.db).await?;
        let Some(t) = sqlx::query("SELECT state, last_atc FROM vault_tokens WHERE token_id = ?")
            .bind(token_id.as_str())
            .fetch_optional(&mut *tx)
            .await?
        else {
            return Ok(ConsumeOutcome::TokenNotActive);
        };
        if state_of(&t)? != TokenState::Active {
            return Ok(ConsumeOutcome::TokenNotActive);
        }
        let luk_row = sqlx::query("SELECT * FROM vault_luks WHERE token_id = ? AND seq = ?")
            .bind(token_id.as_str())
            .bind(i64::from(luk_seq))
            .fetch_optional(&mut *tx)
            .await?;
        match Self::luk_status(luk_row.as_ref(), now)? {
            LukStatus::Valid { .. } => {}
            LukStatus::Unknown => return Ok(ConsumeOutcome::LukUnknown),
            LukStatus::Expired => return Ok(ConsumeOutcome::LukExpired),
            LukStatus::Exhausted => return Ok(ConsumeOutcome::LukExhausted),
        }
        if let Some(last) = t.try_get::<Option<i64>, _>("last_atc")? {
            if i64::from(atc) <= last {
                return Ok(ConsumeOutcome::AtcReplay);
            }
        }
        let updated = sqlx::query("UPDATE vault_luks SET used = used + 1 WHERE token_id = ? AND seq = ? AND used < max_uses")
            .bind(token_id.as_str())
            .bind(i64::from(luk_seq))
            .execute(&mut *tx)
            .await?;
        if updated.rows_affected() != 1 {
            return Ok(ConsumeOutcome::LukExhausted);
        }
        sqlx::query("UPDATE vault_tokens SET last_atc = ?, updated_at = ? WHERE token_id = ?")
            .bind(i64::from(atc))
            .bind(now)
            .bind(token_id.as_str())
            .execute(&mut *tx)
            .await?;
        audit::append(
            &mut tx,
            now,
            &AuditEntry {
                actor,
                // Detokenizatsiya va LUK ishlatilishi bitta yozuvda (avval ikki alohida commit edi).
                action: "DETOKENIZED_LUK_USED",
                token_id: Some(token_id.as_str()),
                details: json!({ "luk_seq": luk_seq, "atc": atc }),
            },
        )
        .await?;
        tx.commit().await?;
        Ok(ConsumeOutcome::Consumed)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use time::macros::datetime;

    #[test]
    fn token_expiry_is_capped_by_card() {
        let now = datetime!(2026-10-23 0:00 UTC);
        let card = CardExpiry::new(2031, 1).unwrap();
        assert_eq!(
            token_expiry(now, 36, card),
            CardExpiry::new(2029, 10).unwrap()
        );
        let short = CardExpiry::new(2027, 5).unwrap();
        assert_eq!(token_expiry(now, 36, short), short);
        assert_eq!(
            token_expiry(datetime!(2026-12-01 0:00 UTC), 1, card),
            CardExpiry::new(2027, 1).unwrap()
        );
    }
}
