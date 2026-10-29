//! Emitent emulyatori: ISO 8583 `0100` → tekshiruvlar → `0110`.
//!
//! Tartib (`docs/specs/emv-profile.md` §7–§8, ADR-0007):
//! 1. format: majburiy maydonlar, Track 2 ↔ maydon 2/14, ICC ma'lumoti, CDOL ↔ maydon 4/49;
//! 2. detokenizatsiya (`Detokenizer::lookup`) — noma'lum token `05`;
//! 3. LUK holati — noma'lum/muddati o'tgan/limiti tugagan `Q1`;
//! 4. ARQC (constant-time) — `Q1`;
//! 5. token holati — `05`; `Detokenizer::consume` (ATC replay `Q1`);
//! 6. emitent mavjudligi — `91`; 7. Shield — `59`; 8. hisob va qoldiq — `05`/`51`; aks holda `00`.
//!
//! ARPC faqat ARQC to'g'ri tekshirilgandan keyin hisoblanadi va maydon 55 da qaytariladi
//! (`91` = ARPC ‖ ARC, `8A` = ARC).

use std::sync::Arc;

use mpay_common::clock::Clock;
use mpay_common::emv::{self, tag, Iad, TerminalData, Track2};
use mpay_common::iso8583::{IsoMessage, Mti};
use mpay_common::ports::{
    ConsumeOutcome, Detokenizer, LukStatus, RiskDecision, RiskRequest, RiskScorer, TokenState,
};
use mpay_common::tlv::{self, Tlv};
use mpay_common::{Pan, PanFingerprint, PanKind, TokenId};
use mpay_crypto::index::pan_fingerprint;
use mpay_crypto::keystore::{KeyLabel, KeyStore};
use mpay_crypto::scheme::CryptogramScheme;
use mpay_crypto::{rng, SecretKey16};
use mpay_db::Db;
use serde::{Deserialize, Serialize};
use sqlx::Row;

use crate::codes::{Reason, ResponseCode};
use crate::IssuerError;

/// Sandbox test hisobi (konfiguratsiyadan).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TestAccount {
    /// Test FPAN (990000–990049).
    pub pan: String,
    pub balance_minor: i64,
    #[serde(default = "default_label")]
    pub label: String,
    /// Karta egasining telefoni (E.164, sandbox'da fiktiv) — OTP SMS uchun (2-faza P2.1).
    #[serde(default)]
    pub phone: Option<String>,
}

fn default_label() -> String {
    "Sandbox hisob".into()
}

/// Shield REVIEW qarorida nima qilish (ADR-0022).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ReviewAction {
    /// Tasdiqlanadi (`APPROVED_AFTER_REVIEW`).
    Approve,
    /// Rad (`05 RISK_REVIEW`).
    Decline,
    /// Karta egasi qurilmada tasdiqlagan (CDCVM) bo'lsa — tasdiq, aks holda `Q2`: telefonda tasdiqlab
    /// qayta tap qiladi. Firibgar o'g'irlangan/bloklanmagan telefondan biometriyasiz o'tolmaydi.
    #[default]
    StepUp,
}

/// Qurilmada tasdiqlashsiz (CDCVM'siz) ruxsat etilgan eng katta summa (tiyin): 1 000 000,00 UZS.
/// `TODO(spec):` bank mahsulot siyosati.
pub const DEFAULT_CVM_LIMIT_MINOR: u64 = 100_000_000;

/// Emitent sozlamalari.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct IssuerConfig {
    /// Shu BIN'lar "ishlamayotgan emitent" (javob `91`).
    pub offline_bins: Vec<String>,
    pub review_action: ReviewAction,
    /// Shu summadan yuqori to'lov faqat CDCVM bilan (aks holda `Q2`). Chegara tokenga ham beriladi —
    /// qurilma o'zi so'raydi; emitent tekshiruvi o'zgartirilgan hamyonga qarshi. 0 — har doim CDCVM.
    pub cvm_limit_minor: u64,
    /// Ishga tushganda yaratiladigan test hisoblar (mavjudlari o'zgartirilmaydi).
    pub accounts: Vec<TestAccount>,
    /// Sandbox: `0110` javobini shuncha ms kechiktirish (yechim commit qilingandan keyin) — sekin
    /// tarmoqni va acquirer timeout'i → reversal yo'lini sinash uchun (ADR-0024). 0 — kechikishsiz.
    pub response_delay_ms: u64,
}

impl Default for IssuerConfig {
    fn default() -> Self {
        Self {
            offline_bins: Vec::new(),
            review_action: ReviewAction::default(),
            cvm_limit_minor: DEFAULT_CVM_LIMIT_MINOR,
            accounts: Vec::new(),
            response_delay_ms: 0,
        }
    }
}

/// Avtorizatsiya natijasi (terminal javobi va audit uchun).
#[derive(Debug, Clone, Serialize)]
pub struct AuthOutcome {
    pub code: ResponseCode,
    pub reason: Reason,
    pub token_id: Option<TokenId>,
    pub dpan_masked: Option<String>,
    pub risk_score: Option<u16>,
    /// `ARPC ‖ ARC` (6 bayt, hex) — ARQC to'g'ri bo'lganda.
    pub issuer_auth_data: Option<String>,
    pub amount_minor: u64,
    pub currency: u16,
}

/// Hisob ko'rinishi (maskalangan).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountView {
    pub account_id: String,
    pub pan_masked: String,
    pub label: String,
    pub currency: u16,
    pub balance_minor: i64,
}

struct Parsed {
    dpan: Pan,
    stan: String,
    rrn: String,
    terminal_id: String,
    merchant_id: String,
    amount: u64,
    currency: u16,
    td: TerminalData,
    pdol: [u8; emv::PDOL_DATA_LEN],
    aip: [u8; 2],
    atc: u16,
    iad: Iad,
    arqc: [u8; 8],
}

/// Emitent emulyatori.
pub struct Issuer {
    pub(crate) db: Db,
    ks: Arc<dyn KeyStore>,
    scheme: Arc<dyn CryptogramScheme>,
    detok: Arc<dyn Detokenizer>,
    risk: Arc<dyn RiskScorer>,
    pub(crate) clock: Arc<dyn Clock>,
    cfg: IssuerConfig,
    imk: KeyLabel,
    pan_idx: KeyLabel,
}

impl std::fmt::Debug for Issuer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Issuer")
            .field("offline_bins", &self.cfg.offline_bins)
            .finish_non_exhaustive()
    }
}

fn reject(reason: Reason) -> Result<(), Reason> {
    Err(reason)
}

impl Issuer {
    /// Migratsiyalar va test hisoblarini tayyorlaydi.
    pub async fn open(
        db: Db,
        ks: Arc<dyn KeyStore>,
        scheme: Arc<dyn CryptogramScheme>,
        detok: Arc<dyn Detokenizer>,
        risk: Arc<dyn RiskScorer>,
        clock: Arc<dyn Clock>,
        cfg: IssuerConfig,
    ) -> Result<Self, IssuerError> {
        db.migrate_with(
            sqlx::migrate!("./migrations/sqlite"),
            sqlx::migrate!("./migrations/postgres"),
        )
        .await?;
        let issuer = Self {
            db,
            ks,
            scheme,
            detok,
            risk,
            clock,
            cfg,
            imk: KeyLabel::new(KeyLabel::IMK_AC),
            pan_idx: KeyLabel::new(KeyLabel::PAN_INDEX),
        };
        for a in issuer.cfg.accounts.clone() {
            let pan = Pan::parse_kind(&a.pan, PanKind::Funding)
                .map_err(|_| IssuerError::Config("issuer.accounts: FPAN noto'g'ri"))?;
            issuer
                .ensure_account(&pan, a.balance_minor, &a.label)
                .await?;
            // Konfiguratsiya — manba: raqam olib tashlansa bazadagi eskisi ham o'chadi (kod eski egaga ketmasin).
            issuer.set_phone(&pan, a.phone.as_deref()).await?;
        }
        Ok(issuer)
    }

    fn fp(&self, pan: &Pan) -> Result<PanFingerprint, IssuerError> {
        Ok(pan_fingerprint(self.ks.as_ref(), &self.pan_idx, pan)?)
    }

    /// Karta egasining telefonini yozadi (E.164: `+` va 7–15 raqam).
    /// `None` — raqamni o'chiradi.
    pub async fn set_phone(&self, pan: &Pan, phone: Option<&str>) -> Result<(), IssuerError> {
        if phone.is_some_and(|p| !mpay_common::phone::is_e164(p)) {
            return Err(IssuerError::Config(
                "issuer.accounts.phone: E.164 (+998…) kutilgan",
            ));
        }
        sqlx::query("UPDATE issuer_accounts SET phone = $1, updated_at = $2 WHERE pan_fp = $3")
            .bind(phone)
            .bind(self.clock.unix())
            .bind(self.fp(pan)?.0.as_slice())
            .execute(self.db.pool())
            .await?;
        Ok(())
    }

    /// OTP yuborish uchun karta egasining telefoni (bo'lmasa `None`). Faqat emitent biladi.
    pub async fn contact_phone(&self, pan: &Pan) -> Result<Option<String>, IssuerError> {
        use sqlx::Row;
        Ok(
            sqlx::query("SELECT phone FROM issuer_accounts WHERE pan_fp = $1")
                .bind(self.fp(pan)?.0.as_slice())
                .fetch_optional(self.db.pool())
                .await?
                .and_then(|r| r.try_get::<Option<String>, _>("phone").ok().flatten()),
        )
    }

    /// Test hisobini yaratadi (mavjud bo'lsa o'zgartirmaydi) va uning ko'rinishini qaytaradi.
    pub async fn ensure_account(
        &self,
        pan: &Pan,
        balance_minor: i64,
        label: &str,
    ) -> Result<AccountView, IssuerError> {
        if balance_minor < 0 {
            return Err(IssuerError::Config("balance_minor manfiy"));
        }
        let fp = self.fp(pan)?;
        let ts = self.clock.unix();
        let id = format!("acc_{}", hex::encode(rng::array::<8>()?));
        sqlx::query(
            "INSERT INTO issuer_accounts (account_id, pan_fp, pan_masked, label, currency, balance_minor, created_at, updated_at) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8) ON CONFLICT(pan_fp) DO NOTHING",
        )
        .bind(&id)
        .bind(fp.0.as_slice())
        .bind(pan.masked())
        .bind(label)
        .bind(i64::from(emv::UZ_NUMERIC))
        .bind(balance_minor)
        .bind(ts)
        .bind(ts)
        .execute(self.db.pool())
        .await?;
        self.account_by_fp(&fp)
            .await?
            .ok_or(IssuerError::Config("hisob yaratilmadi"))
    }

    async fn account_by_fp(&self, fp: &PanFingerprint) -> Result<Option<AccountView>, IssuerError> {
        let r = sqlx::query("SELECT * FROM issuer_accounts WHERE pan_fp = $1")
            .bind(fp.0.as_slice())
            .fetch_optional(self.db.pool())
            .await?;
        r.map(|r| -> Result<AccountView, IssuerError> {
            Ok(AccountView {
                account_id: r.try_get("account_id")?,
                pan_masked: r.try_get("pan_masked")?,
                label: r.try_get("label")?,
                currency: r.try_get::<i64, _>("currency")? as u16,
                balance_minor: r.try_get("balance_minor")?,
            })
        })
        .transpose()
    }

    /// Barcha hisoblar (sandbox operator ko'rinishi).
    pub async fn accounts(&self) -> Result<Vec<AccountView>, IssuerError> {
        let rows = sqlx::query("SELECT * FROM issuer_accounts ORDER BY created_at, account_id")
            .fetch_all(self.db.pool())
            .await?;
        rows.iter()
            .map(|r| {
                Ok(AccountView {
                    account_id: r.try_get("account_id")?,
                    pan_masked: r.try_get("pan_masked")?,
                    label: r.try_get("label")?,
                    currency: r.try_get::<i64, _>("currency")? as u16,
                    balance_minor: r.try_get("balance_minor")?,
                })
            })
            .collect()
    }

    /// Ikkilik ISO 8583 `0100` → `0110`. Xabarni umuman o'qib bo'lmasa — xato (shlyuz 400 qaytaradi).
    pub async fn process_bytes(
        &self,
        request: &[u8],
    ) -> Result<(Vec<u8>, AuthOutcome), IssuerError> {
        let msg = IsoMessage::unpack(request)?;
        let (resp, out) = self.authorize(&msg).await?;
        if self.cfg.response_delay_ms > 0 {
            tokio::time::sleep(std::time::Duration::from_millis(self.cfg.response_delay_ms)).await;
        }
        Ok((resp.pack(), out))
    }

    /// `0100` ni qayta ishlaydi.
    pub async fn authorize(
        &self,
        req: &IsoMessage,
    ) -> Result<(IsoMessage, AuthOutcome), IssuerError> {
        if req.mti != Mti::AUTH_REQUEST {
            return Err(IssuerError::Format("MTI 0100 kutilgan"));
        }
        // Javobda qaytariladigan maydonlar so'rovdan aks ettiriladi.
        let mut resp = IsoMessage::new(req.mti.response());
        for f in [2u8, 3, 4, 7, 11, 37, 41, 42, 49] {
            if let Some(v) = req.get(f) {
                resp.set(f, v.to_vec())?;
            }
        }
        let amount = req
            .get(4)
            .and_then(|_| req.require_num(4).ok())
            .unwrap_or(0);
        let currency = req
            .get(49)
            .and_then(|_| req.require_num(49).ok())
            .unwrap_or(0) as u16;

        let mut out = AuthOutcome {
            code: ResponseCode::DoNotHonor,
            reason: Reason::IccDataMissing,
            token_id: None,
            dpan_masked: None,
            risk_score: None,
            issuer_auth_data: None,
            amount_minor: amount,
            currency,
        };

        let parsed = match parse_request(req) {
            Ok(p) => p,
            Err(reason) => {
                out.reason = reason;
                out.code = reason.code();
                let mut tx = self.db.begin_write().await?;
                self.finish(&mut tx, &mut resp, &out, None, None).await?;
                tx.commit().await?;
                return Ok((resp, out));
            }
        };
        out.dpan_masked = Some(parsed.dpan.masked());

        let mut sk: Option<SecretKey16> = None;
        let mut debit: Option<(String, i64)> = None;
        let result = self.decide(&parsed, &mut out, &mut sk, &mut debit).await;
        let mut reason = result.unwrap_or_else(|r| r);
        // Pul yechish va avtorizatsiya yozuvi — bitta tranzaksiya: biri yozilib, ikkinchisi yozilmay
        // qolmasin (aks holda pul yechilgan-u, yozuv yo'q yoki aksincha). `BEGIN IMMEDIATE` — SQLite'da
        // o'qishdan yozishga o'tishdagi `SQLITE_BUSY` bo'lmasin.
        let mut tx = self.db.begin_write().await?;
        // Yechilgan hisob avtorizatsiya qatoriga yoziladi — reversal shu hisobga qaytaradi (ADR-0024).
        let mut debited: Option<&str> = None;
        if let Some((account_id, amount)) = &debit {
            let n = sqlx::query(
                "UPDATE issuer_accounts SET balance_minor = balance_minor - $1, updated_at = $2 \
                 WHERE account_id = $3 AND balance_minor >= $4",
            )
            .bind(amount)
            .bind(self.clock.unix())
            .bind(account_id)
            .bind(amount)
            .execute(&mut *tx)
            .await?
            .rows_affected();
            if n == 1 {
                debited = Some(account_id.as_str());
            } else {
                reason = Reason::InsufficientFunds;
            }
        }
        out.reason = reason;
        out.code = reason.code();
        if let Some(sk) = &sk {
            let arpc = self.scheme.arpc(sk, &parsed.arqc, out.code.arc());
            let mut iad91 = arpc.to_vec();
            iad91.extend_from_slice(&out.code.arc());
            out.issuer_auth_data = Some(hex::encode(&iad91));
        }
        self.finish(&mut tx, &mut resp, &out, Some(&parsed), debited)
            .await?;
        tx.commit().await?;
        tracing::info!(
            token_id = ?out.token_id.as_ref().map(TokenId::as_str),
            dpan = ?out.dpan_masked,
            code = out.code.as_str(),
            reason = out.reason.as_str(),
            stan = %parsed.stan,
            "issuer: avtorizatsiya"
        );
        Ok((resp, out))
    }

    /// Qaror zanjiri. `Err(reason)` — rad; `Ok(reason)` — tasdiq. `sk` faqat ARQC to'g'ri bo'lsa to'ldiriladi.
    /// Tasdiqda yechiladigan summa `debit` ga yoziladi — yechish va yozuv `authorize` da bitta tranzaksiyada.
    async fn decide(
        &self,
        p: &Parsed,
        out: &mut AuthOutcome,
        sk_out: &mut Option<SecretKey16>,
        debit: &mut Option<(String, i64)>,
    ) -> Result<Reason, Reason> {
        if p.iad.scheme_id != self.scheme.scheme_id() {
            reject(Reason::UnsupportedScheme)?;
        }
        let view = match self.detok.lookup(&p.dpan, p.iad.luk_seq).await {
            Ok(Some(v)) => v,
            Ok(None) => return Err(Reason::UnknownToken),
            Err(e) => {
                tracing::error!(error = %e, "issuer: detokenizatsiya xatosi");
                return Err(Reason::IssuerOffline);
            }
        };
        out.token_id = Some(view.token_id.clone());
        // ADR-0022: muddati o'tgan token (DPAN muddati oyning oxirigacha amal qiladi) — LUK holatidan
        // oldin: LUK muddati token muddatidan oshmaydi, aks holda mijoz `Q1` ko'rardi, `54` emas.
        // DPAN muddati sir emas (track2'da bor), ARQC tekshiruvisiz aytish xavfsiz.
        let now = self.clock.now();
        if view.dpan_expiry.is_expired(now) {
            return Err(Reason::TokenExpired);
        }
        match view.luk {
            LukStatus::Valid { .. } => {}
            LukStatus::Unknown => reject(Reason::LukUnknown)?,
            LukStatus::Expired => reject(Reason::LukExpired)?,
            LukStatus::Exhausted => reject(Reason::LukExhausted)?,
        }

        let luk = self
            .scheme
            .luk_from_imk(
                self.ks.as_ref(),
                &self.imk,
                &p.dpan,
                view.psn,
                p.iad.luk_seq,
            )
            .map_err(|_| Reason::IssuerOffline)?;
        let sk = self.scheme.session_key(&luk, p.atc);
        let cdol = emv::cdol_data(&p.pdol, p.aip, p.atc, &p.iad);
        if !self.scheme.verify_arqc(&sk, &cdol, &p.arqc) {
            return Err(Reason::ArqcMismatch);
        }
        *sk_out = Some(sk);

        if view.state != TokenState::Active {
            reject(Reason::TokenNotActive)?;
        }
        match self
            .detok
            .consume(&view.token_id, p.iad.luk_seq, p.atc)
            .await
        {
            Ok(ConsumeOutcome::Consumed) => {}
            Ok(ConsumeOutcome::AtcReplay) => {
                // Takroriy kriptogramma — ARPC berilmaydi (replay orakuli bo'lmasin).
                *sk_out = None;
                return Err(Reason::AtcReplay);
            }
            Ok(ConsumeOutcome::TokenNotActive) => reject(Reason::TokenNotActive)?,
            Ok(ConsumeOutcome::LukExhausted) => reject(Reason::LukExhausted)?,
            Ok(ConsumeOutcome::LukExpired) => reject(Reason::LukExpired)?,
            Ok(ConsumeOutcome::LukUnknown) => reject(Reason::LukUnknown)?,
            Err(e) => {
                tracing::error!(error = %e, "issuer: LUK qayd xatosi");
                return Err(Reason::IssuerOffline);
            }
        }

        if self
            .cfg
            .offline_bins
            .iter()
            .any(|b| view.fpan.expose_digits().starts_with(b.as_str()))
        {
            reject(Reason::IssuerOffline)?;
        }

        // CVM siyosati: katta summa faqat qurilmada tasdiqlangan bo'lsa (CVR ARQC bilan himoyalangan).
        let cdcvm = p.iad.cvr & emv::cvr::CDCVM_PERFORMED != 0;
        if p.amount > self.cfg.cvm_limit_minor && !cdcvm {
            reject(Reason::CvmRequired)?;
        }

        let risk = self
            .risk
            .score(&RiskRequest {
                token_id: view.token_id.clone(),
                device_id: view.device_id,
                pan_fingerprint: view.pan_fingerprint,
                amount_minor: p.amount,
                currency: p.currency,
                merchant_id: p.merchant_id.clone(),
                terminal_id: p.terminal_id.clone(),
                country: p.td.country,
                atc: p.atc,
                cdcvm_performed: cdcvm,
                at: self.clock.now(),
            })
            .await
            .map_err(|_| Reason::IssuerOffline)?;
        out.risk_score = Some(risk.score);
        let mut reviewed = false;
        match risk.decision {
            RiskDecision::Approve => {}
            RiskDecision::Decline => reject(Reason::RiskDecline)?,
            RiskDecision::Review => match self.cfg.review_action {
                ReviewAction::Approve => reviewed = true,
                ReviewAction::Decline => reject(Reason::RiskReview)?,
                ReviewAction::StepUp if cdcvm => reviewed = true,
                ReviewAction::StepUp => reject(Reason::ReviewStepUp)?,
            },
        }

        let acct = self
            .account_by_fp(&view.pan_fingerprint)
            .await
            .map_err(|_| Reason::IssuerOffline)?
            .ok_or(Reason::AccountNotFound)?;
        if acct.currency != p.currency {
            reject(Reason::CurrencyMismatch)?;
        }
        let amount = i64::try_from(p.amount).map_err(|_| Reason::InsufficientFunds)?;
        if acct.balance_minor < amount {
            reject(Reason::InsufficientFunds)?;
        }
        *debit = Some((acct.account_id, amount));
        Ok(if reviewed {
            Reason::ApprovedAfterReview
        } else {
            Reason::Approved
        })
    }

    async fn finish(
        &self,
        tx: &mut sqlx::AnyConnection,
        resp: &mut IsoMessage,
        out: &AuthOutcome,
        p: Option<&Parsed>,
        account_id: Option<&str>,
    ) -> Result<(), IssuerError> {
        resp.set_str(39, out.code.as_str())?;
        if let Some(iad) = &out.issuer_auth_data {
            let raw = hex::decode(iad).map_err(|_| IssuerError::Format("ARPC"))?;
            let icc = tlv::encode_all(&[
                Tlv::primitive(tag::ISSUER_AUTH_DATA, raw),
                Tlv::primitive(tag::ARC, out.code.arc().to_vec()),
            ]);
            resp.set(55, icc)?;
        }
        let auth_id = format!("ath_{}", hex::encode(rng::array::<8>()?));
        sqlx::query(
            "INSERT INTO issuer_authorizations (auth_id, ts, stan, rrn, token_id, account_id, dpan_masked, amount_minor, currency, \
             terminal_id, merchant_id, atc, luk_seq, response_code, reason, risk_score, risk_decision) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, NULL)",
        )
        .bind(&auth_id)
        .bind(self.clock.unix())
        .bind(p.map(|p| p.stan.as_str()).unwrap_or(""))
        .bind(p.map(|p| p.rrn.as_str()).unwrap_or(""))
        .bind(out.token_id.as_ref().map(TokenId::as_str))
        .bind(account_id)
        .bind(out.dpan_masked.as_deref())
        .bind(out.amount_minor as i64)
        .bind(i64::from(out.currency))
        .bind(p.map(|p| p.terminal_id.as_str()).unwrap_or(""))
        .bind(p.map(|p| p.merchant_id.as_str()).unwrap_or(""))
        .bind(p.map(|p| i64::from(p.atc)))
        .bind(p.map(|p| i64::from(p.iad.luk_seq)))
        .bind(out.code.as_str())
        .bind(out.reason.as_str())
        .bind(out.risk_score.map(i64::from))
        .execute(&mut *tx)
        .await?;
        Ok(())
    }
}

/// `0100` ni faqat tahlil qiladi (DB va kalitlarsiz): majburiy maydonlar, Track 2 ↔ maydon 2/14,
/// ICC teglari va PDOL ↔ maydon 4/49 muvofiqligi. Fuzzing va diagnostika uchun.
pub fn validate_request(req: &IsoMessage) -> Result<(), Reason> {
    parse_request(req).map(|_| ())
}

/// `0100` ni tahlil qiladi; muammo bo'lsa sabab.
fn parse_request(req: &IsoMessage) -> Result<Parsed, Reason> {
    let fmt = |_| Reason::IccDataMissing;
    for f in [2u8, 3, 4, 7, 11, 14, 22, 35, 37, 41, 42, 49, 55] {
        req.require(f).map_err(fmt)?;
    }
    let dpan = Pan::parse_kind(req.require_str(2).map_err(fmt)?, PanKind::Device)
        .map_err(|_| Reason::UnknownToken)?;
    let t2 =
        Track2::from_iso(req.require_str(35).map_err(fmt)?).map_err(|_| Reason::FieldMismatch)?;
    if t2.pan != dpan || t2.expiry.to_yymm() != req.require_str(14).map_err(fmt)? {
        return Err(Reason::FieldMismatch);
    }
    let icc = tlv::parse_all(req.require(55).map_err(fmt)?).map_err(|_| Reason::IccDataMissing)?;
    let g = |t: u32| tlv::require(&icc, t).map_err(|_| Reason::IccDataMissing);
    let arqc: [u8; 8] = tlv::require_len(&icc, tag::ARQC).map_err(|_| Reason::IccDataMissing)?;
    let atc =
        u16::from_be_bytes(tlv::require_len(&icc, tag::ATC).map_err(|_| Reason::IccDataMissing)?);
    let aip: [u8; 2] = tlv::require_len(&icc, tag::AIP).map_err(|_| Reason::IccDataMissing)?;
    let iad = Iad::from_bytes(g(tag::IAD)?).map_err(|_| Reason::UnsupportedScheme)?;
    if g(tag::CID)? != [emv::CID_ARQC] {
        return Err(Reason::FieldMismatch);
    }
    // PDOL ma'lumotini ICC teglaridan qayta yig'amiz (kartaga yuborilgan tartibda).
    let mut pdol = [0u8; emv::PDOL_DATA_LEN];
    let mut pos = 0;
    for e in emv::PDOL {
        let v = g(e.tag.0)?;
        if v.len() != e.len {
            return Err(Reason::IccDataMissing);
        }
        pdol[pos..pos + e.len].copy_from_slice(v);
        pos += e.len;
    }
    let td = TerminalData::from_pdol_data(&pdol).map_err(|_| Reason::FieldMismatch)?;
    let amount = req.require_num(4).map_err(fmt)?;
    let currency = req.require_num(49).map_err(fmt)? as u16;
    if td.amount_minor != amount || td.currency != currency {
        return Err(Reason::FieldMismatch);
    }
    Ok(Parsed {
        dpan,
        stan: req.require_str(11).map_err(fmt)?.to_owned(),
        rrn: req.require_str(37).map_err(fmt)?.to_owned(),
        terminal_id: req.require_str(41).map_err(fmt)?.trim_end().to_owned(),
        merchant_id: req.require_str(42).map_err(fmt)?.trim_end().to_owned(),
        amount,
        currency,
        td,
        pdol,
        aip,
        atc,
        iad,
        arqc,
    })
}
