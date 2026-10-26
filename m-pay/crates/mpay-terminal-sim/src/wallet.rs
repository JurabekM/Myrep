//! Soft-wallet: Android Wallet SDK'ning Rust o'rinbosari (telefonsiz e2e uchun).
//! PQ Link sessiyasi, provisioning, OTP, LUK to'ldirish.

use mpay_common::api::{
    Empty, Envelope, ErrorResponse, LuksResponse, OtpVerifyRequest, ProvisionRequest,
    ProvisionResponse, TokenProfileDto,
};
use mpay_common::{DeviceId, TokenId};
use mpay_pqlink::sandbox::SoftDeviceKey;
use mpay_pqlink::{ClientHandshake, ClientSession, ServerIdentity};
use serde::de::DeserializeOwned;
use serde::Serialize;
use zeroize::Zeroizing;

use crate::http::ServerClient;
use crate::WalletError;

/// Soft-wallet.
pub struct SoftWallet {
    client: ServerClient,
    pinned: ServerIdentity,
    device: SoftDeviceKey,
    session: Option<ClientSession>,
}

impl std::fmt::Debug for SoftWallet {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SoftWallet")
            .field("server", &self.client)
            .field("session", &self.session.as_ref().map(|s| s.device_id()))
            .finish()
    }
}

impl SoftWallet {
    pub fn new(client: ServerClient, pinned: ServerIdentity, device: SoftDeviceKey) -> Self {
        Self {
            client,
            pinned,
            device,
            session: None,
        }
    }

    pub fn client(&self) -> &ServerClient {
        &self.client
    }

    /// PQ Link handshake. Muvaffaqiyatli bo'lsa server tasdiqlagan `DeviceId` qaytadi.
    pub async fn connect(&mut self) -> Result<DeviceId, WalletError> {
        let (hs, ch) = ClientHandshake::start(self.pinned.clone())?;
        let sh = self.client.post_pqlink("/v1/pqlink/hello", ch).await?;
        let sh = Self::expect_raw(sh)?;
        let (pending, cf) = hs.on_server_hello(&sh, &self.device)?;
        let sa = Self::expect_raw(self.client.post_pqlink("/v1/pqlink/finish", cf).await?)?;
        let s = pending.on_accept(&sa)?;
        let id = s.device_id();
        self.session = Some(s);
        Ok(id)
    }

    /// Keyingi so'rovlar boshqa serverga (ko'p instansiya / load balancer simulyatsiyasi).
    pub fn set_client(&mut self, client: ServerClient) {
        self.client = client;
    }

    /// Handshake ikki xil instansiyada: `hello` — joriy klientga, `finish` — `finish_via` ga
    /// (sessiyalar ombori umumiy bo'lsagina muvaffaqiyatli; 2-faza P2.4).
    pub async fn connect_split(
        &mut self,
        finish_via: &ServerClient,
    ) -> Result<DeviceId, WalletError> {
        let (hs, ch) = ClientHandshake::start(self.pinned.clone())?;
        let sh = Self::expect_raw(self.client.post_pqlink("/v1/pqlink/hello", ch).await?)?;
        let (pending, cf) = hs.on_server_hello(&sh, &self.device)?;
        let sa = Self::expect_raw(finish_via.post_pqlink("/v1/pqlink/finish", cf).await?)?;
        let s = pending.on_accept(&sa)?;
        let id = s.device_id();
        self.session = Some(s);
        Ok(id)
    }

    fn expect_raw(r: crate::http::RawResponse) -> Result<Vec<u8>, WalletError> {
        if r.status.is_success() && r.sealed {
            return Ok(r.body);
        }
        Err(Self::plain_error(r.status.as_u16(), &r.body))
    }

    fn plain_error(status: u16, body: &[u8]) -> WalletError {
        match serde_json::from_slice::<ErrorResponse>(body) {
            Ok(e) => WalletError::Api {
                status,
                code: e.error.code,
                message: e.error.message,
            },
            Err(_) => WalletError::Api {
                status,
                code: "HTTP".into(),
                message: String::from_utf8_lossy(body).into_owned(),
            },
        }
    }

    /// Muhrlangan so'rovni tayyorlaydi (replay testlari uchun alohida).
    pub fn seal_request<Req: Serialize>(&mut self, req: &Req) -> Result<Vec<u8>, WalletError> {
        let s = self.session.as_mut().ok_or(WalletError::NotConnected)?;
        let json = Zeroizing::new(
            serde_json::to_vec(req).map_err(|_| WalletError::Decode("so'rov JSON"))?,
        );
        Ok(s.seal(&json)?)
    }

    /// Muhrlangan so'rov yuboradi va muhrlangan javobni ochadi.
    pub async fn call<Req: Serialize, Resp: DeserializeOwned>(
        &mut self,
        path: &str,
        req: &Req,
    ) -> Result<Resp, WalletError> {
        let body = self.seal_request(req)?;
        self.send_sealed(path, body).await
    }

    /// Tayyor muhrlangan tanani yuboradi.
    pub async fn send_sealed<Resp: DeserializeOwned>(
        &mut self,
        path: &str,
        body: Vec<u8>,
    ) -> Result<Resp, WalletError> {
        let r = self.client.post_pqlink(path, body).await?;
        if !r.sealed {
            let e = Self::plain_error(r.status.as_u16(), &r.body);
            if matches!(&e, WalletError::Api { code, .. } if code == "PQLINK_SESSION") {
                self.session = None;
            }
            return Err(e);
        }
        let s = self.session.as_mut().ok_or(WalletError::NotConnected)?;
        let pt = s.open(&r.body)?;
        let env: Envelope<Resp> =
            serde_json::from_slice(&pt).map_err(|_| WalletError::Decode("javob konverti"))?;
        match (env.ok, env.data, env.error) {
            (true, Some(d), _) => Ok(d),
            (_, _, Some(e)) => Err(WalletError::Api {
                status: r.status.as_u16(),
                code: e.code,
                message: e.message,
            }),
            _ => Err(WalletError::Decode("javob konverti")),
        }
    }

    pub async fn provision(
        &mut self,
        fpan: &str,
        expiry_yymm: &str,
    ) -> Result<ProvisionResponse, WalletError> {
        let req = ProvisionRequest {
            pan: Zeroizing::new(fpan.to_owned()),
            expiry: expiry_yymm.to_owned(),
        };
        self.call("/v1/tokens", &req).await
    }

    pub async fn verify_otp(
        &mut self,
        token_id: &TokenId,
        challenge_id: &str,
        otp: &str,
    ) -> Result<TokenProfileDto, WalletError> {
        let req = OtpVerifyRequest {
            challenge_id: challenge_id.to_owned(),
            otp: Zeroizing::new(otp.to_owned()),
        };
        self.call(&format!("/v1/tokens/{token_id}/idv/verify"), &req)
            .await
    }

    /// OTP SMS'ni qayta yuborishni so'raydi (2-faza P2.1); javobda maskalangan telefon.
    pub async fn resend_otp(
        &mut self,
        token_id: &TokenId,
        challenge_id: &str,
    ) -> Result<mpay_common::api::OtpResendResponse, WalletError> {
        let req = mpay_common::api::OtpResendRequest {
            challenge_id: challenge_id.to_owned(),
        };
        self.call(&format!("/v1/tokens/{token_id}/idv/resend"), &req)
            .await
    }

    /// Qurilma kalitini almashtirish (ADR-0015): `new` — `/v1/pqlink/enroll` nonce'i bilan yaratilgan
    /// kalit. Yangi kalit `REKEY_LABEL ‖ session_id ‖ eski device_id` ni imzolaydi; muvaffaqiyatda
    /// hamyon yangi kalitga o'tadi va keyingi so'rovdan oldin qayta ulanish kerak.
    pub async fn rekey(
        &mut self,
        new: SoftDeviceKey,
    ) -> Result<mpay_common::api::RekeyResponse, WalletError> {
        use mpay_pqlink::DeviceSigner;
        let s = self.session.as_ref().ok_or(WalletError::NotConnected)?;
        let msg = [
            mpay_pqlink::crypto::REKEY_LABEL,
            &s.session_id()[..],
            &s.device_id().0[..],
        ]
        .concat();
        let req = mpay_common::api::RekeyRequest {
            cert_chain: new.cert_chain().iter().map(hex::encode).collect(),
            signature: hex::encode(new.sign(&msg)?),
        };
        let r = self.call("/v1/devices/rekey", &req).await?;
        self.device = new;
        self.session = None;
        Ok(r)
    }

    pub async fn replenish(&mut self, token_id: &TokenId) -> Result<LuksResponse, WalletError> {
        self.call(&format!("/v1/tokens/{token_id}/luks"), &Empty {})
            .await
    }
}
