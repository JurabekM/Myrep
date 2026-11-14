//! Soft-wallet holat fayli (`mpay-tsim`). **Faqat sandbox:** ichida qurilma kaliti va LUK'lar bor —
//! sandbox katalogida (`.mpay/`, git'ga tushmaydi) saqlang.

use std::path::Path;

use mpay_common::api::LukDto;
use mpay_common::{CardExpiry, Pan, PanKind, TokenId};
use mpay_crypto::SecretKey16;
use serde::{Deserialize, Serialize};
use zeroize::Zeroizing;

use crate::card::{CardLuk, CardProfile};
use crate::WalletError;

#[derive(Clone, Serialize, Deserialize)]
pub struct StoredLuk {
    pub seq: u32,
    pub key: Zeroizing<String>,
    pub expires_at: i64,
    pub uses_left: u32,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct StoredToken {
    pub token_id: TokenId,
    pub dpan: Zeroizing<String>,
    pub dpan_expiry: String,
    pub psn: u8,
    pub atc: u16,
    pub luks: Vec<StoredLuk>,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct WalletState {
    pub server_fingerprint: String,
    pub device_key_pkcs8: Zeroizing<String>,
    pub device_chain: Vec<String>,
    pub tokens: Vec<StoredToken>,
    /// Terminal STAN hisoblagichi (har tranzaksiyada oshadi, 999999 dan keyin 1).
    #[serde(default)]
    pub stan: u32,
}

impl std::fmt::Debug for WalletState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "WalletState({} token)", self.tokens.len())
    }
}

impl WalletState {
    pub fn load(path: &Path) -> Result<Self, WalletError> {
        let txt = Zeroizing::new(
            std::fs::read_to_string(path)
                .map_err(|e| WalletError::Config(format!("{}: {e}", path.display())))?,
        );
        serde_json::from_str(&txt).map_err(|_| WalletError::Decode("hamyon fayli"))
    }

    pub fn save(&self, path: &Path) -> Result<(), WalletError> {
        let txt = Zeroizing::new(
            serde_json::to_string_pretty(self).map_err(|_| WalletError::Decode("hamyon"))?,
        );
        std::fs::write(path, txt.as_bytes())
            .map_err(|e| WalletError::Config(format!("{}: {e}", path.display())))
    }

    /// Tokenni topadi (`None` — yagona/oxirgi token).
    pub fn token(&self, id: Option<&TokenId>) -> Result<&StoredToken, WalletError> {
        match id {
            Some(id) => self.tokens.iter().find(|t| &t.token_id == id),
            None => self.tokens.last(),
        }
        .ok_or(WalletError::Config("hamyonda bunday token yo'q".into()))
    }

    /// Keyingi STAN.
    pub fn next_stan(&mut self) -> u32 {
        self.stan = if self.stan >= 999_999 {
            1
        } else {
            self.stan + 1
        };
        self.stan
    }

    pub fn upsert(&mut self, t: StoredToken) {
        self.tokens.retain(|x| x.token_id != t.token_id);
        self.tokens.push(t);
    }
}

impl StoredToken {
    pub fn to_profile(&self) -> Result<CardProfile, WalletError> {
        let luks = self
            .luks
            .iter()
            .map(|l| {
                let raw = Zeroizing::new(
                    hex::decode(l.key.as_str()).map_err(|_| WalletError::Decode("LUK"))?,
                );
                Ok(CardLuk {
                    seq: l.seq,
                    key: SecretKey16::from_slice(&raw).ok_or(WalletError::Decode("LUK"))?,
                    expires_at: l.expires_at,
                    uses_left: l.uses_left,
                })
            })
            .collect::<Result<_, WalletError>>()?;
        Ok(CardProfile {
            token_id: self.token_id.clone(),
            dpan: Pan::parse_kind(&self.dpan, PanKind::Device)
                .map_err(|_| WalletError::Decode("DPAN"))?,
            expiry: CardExpiry::parse_yymm(&self.dpan_expiry)
                .ok_or(WalletError::Decode("muddat"))?,
            psn: self.psn,
            luks,
            atc: self.atc,
        })
    }

    pub fn from_profile(p: &CardProfile) -> Self {
        Self {
            token_id: p.token_id.clone(),
            dpan: Zeroizing::new(p.dpan.expose_digits().to_owned()),
            dpan_expiry: p.expiry.to_yymm(),
            psn: p.psn,
            atc: p.atc,
            luks: p
                .luks
                .iter()
                .map(|l| StoredLuk {
                    seq: l.seq,
                    key: Zeroizing::new(hex::encode(l.key.expose())),
                    expires_at: l.expires_at,
                    uses_left: l.uses_left,
                })
                .collect(),
        }
    }

    pub fn add_luks(&mut self, luks: &[LukDto]) {
        for l in luks {
            self.luks.push(StoredLuk {
                seq: l.seq,
                key: l.key.clone(),
                expires_at: l.expires_at,
                uses_left: l.max_uses,
            });
        }
    }
}
