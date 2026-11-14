//! Loopback soft-karta — M-Pay Test Scheme applet'i (`docs/specs/emv-profile.md` §2).
//! Android HCE (`HostApduService`, M6) shu mantiqni Kotlin'da takrorlaydi.

use mpay_common::api::TokenProfileDto;
use mpay_common::emv::{self, cvr, tag, Iad, TerminalData, Track2};
use mpay_common::tlv::{self, Tlv};
use mpay_common::{CardExpiry, Pan, PanKind, TokenId};
use mpay_crypto::scheme::{CryptogramScheme, MpayAes128CmacV1};
use mpay_crypto::{ct_eq, SecretKey16};

use crate::apdu::{sw, ApduHandler, Command, Response};

/// Kartadagi LUK.
#[derive(Clone)]
pub struct CardLuk {
    pub seq: u32,
    pub key: SecretKey16,
    pub expires_at: i64,
    pub uses_left: u32,
}

impl std::fmt::Debug for CardLuk {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "CardLuk(seq={}, uses_left={})", self.seq, self.uses_left)
    }
}

/// Token profili (kartada).
#[derive(Debug, Clone)]
pub struct CardProfile {
    pub token_id: TokenId,
    pub dpan: Pan,
    pub expiry: CardExpiry,
    pub psn: u8,
    pub luks: Vec<CardLuk>,
    /// Oxirgi ishlatilgan ATC.
    pub atc: u16,
}

impl CardProfile {
    /// Server javobidan.
    pub fn from_dto(d: &TokenProfileDto) -> Result<Self, &'static str> {
        let dpan = Pan::parse_kind(&d.dpan, PanKind::Device).map_err(|_| "DPAN")?;
        let expiry = CardExpiry::parse_yymm(&d.dpan_expiry).ok_or("muddat")?;
        if d.aid != hex::encode_upper(emv::AID) {
            return Err("AID");
        }
        let mut p = Self {
            token_id: d.token_id.clone(),
            dpan,
            expiry,
            psn: d.psn,
            luks: vec![],
            atc: 0,
        };
        p.add_luks(&d.luks)?;
        Ok(p)
    }

    /// Yangi LUK'larni qo'shadi.
    pub fn add_luks(&mut self, luks: &[mpay_common::api::LukDto]) -> Result<(), &'static str> {
        for l in luks {
            let raw = zeroize::Zeroizing::new(hex::decode(l.key.as_str()).map_err(|_| "LUK")?);
            self.luks.push(CardLuk {
                seq: l.seq,
                key: SecretKey16::from_slice(&raw).ok_or("LUK uzunligi")?,
                expires_at: l.expires_at,
                uses_left: l.max_uses,
            });
        }
        Ok(())
    }
}

/// Karta siyosati.
#[derive(Debug, Clone)]
pub struct CardPolicy {
    /// Shu summadan yuqori bo'lsa CDCVM (biometriya) talab qilinadi.
    pub cdcvm_limit_minor: u64,
    /// `false` — faqat testlar uchun: karta o'z LUK limit/muddatini tekshirmaydi
    /// (server tomoni himoyasini sinash uchun).
    pub enforce_local_limits: bool,
}

impl Default for CardPolicy {
    fn default() -> Self {
        Self {
            // 1 000 000,00 UZS
            cdcvm_limit_minor: 100_000_000,
            enforce_local_limits: true,
        }
    }
}

struct LastTxn {
    sk: SecretKey16,
    arqc: [u8; 8],
}

/// Soft-karta.
pub struct SoftCard {
    profile: CardProfile,
    policy: CardPolicy,
    scheme: MpayAes128CmacV1,
    selected: bool,
    cdcvm_verified: bool,
    now: Box<dyn Fn() -> i64 + Send>,
    last: Option<LastTxn>,
}

impl std::fmt::Debug for SoftCard {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SoftCard")
            .field("profile", &self.profile)
            .finish_non_exhaustive()
    }
}

fn unix_now() -> i64 {
    time::OffsetDateTime::now_utc().unix_timestamp()
}

impl SoftCard {
    pub fn new(profile: CardProfile, policy: CardPolicy) -> Self {
        Self {
            profile,
            policy,
            scheme: MpayAes128CmacV1,
            selected: false,
            cdcvm_verified: false,
            now: Box::new(unix_now),
            last: None,
        }
    }

    /// Vaqt manbaini almashtiradi (testlar).
    pub fn with_clock(mut self, now: impl Fn() -> i64 + Send + 'static) -> Self {
        self.now = Box::new(now);
        self
    }

    pub fn profile(&self) -> &CardProfile {
        &self.profile
    }

    pub fn profile_mut(&mut self) -> &mut CardProfile {
        &mut self.profile
    }

    /// Biometrik tasdiq simulyatsiyasi (Android'da `BiometricPrompt`, M6).
    pub fn set_cdcvm_verified(&mut self, v: bool) {
        self.cdcvm_verified = v;
    }

    /// Oxirgi tranzaksiya uchun emitent javobidagi `91` (ARPC ‖ ARC) ni tekshiradi.
    pub fn verify_issuer_auth(&self, iad91: &[u8]) -> bool {
        let (Some(last), [a0, a1, a2, a3, c0, c1]) = (&self.last, iad91) else {
            return false;
        };
        let want = self.scheme.arpc(&last.sk, &last.arqc, [*c0, *c1]);
        ct_eq(&want, &[*a0, *a1, *a2, *a3])
    }

    fn ppse_fci() -> Vec<u8> {
        Tlv::constructed(
            tag::FCI_TEMPLATE,
            vec![
                Tlv::primitive(tag::DF_NAME, emv::PPSE_NAME.to_vec()),
                Tlv::constructed(
                    tag::FCI_PROPRIETARY,
                    vec![Tlv::constructed(
                        tag::FCI_ISSUER_DISCRETIONARY,
                        vec![Tlv::constructed(
                            tag::APPLICATION_TEMPLATE,
                            vec![
                                Tlv::primitive(tag::AID, emv::AID.to_vec()),
                                Tlv::primitive(tag::APP_LABEL, emv::APP_LABEL.to_vec()),
                                Tlv::primitive(tag::APP_PRIORITY, vec![0x01]),
                            ],
                        )],
                    )],
                ),
            ],
        )
        .to_bytes()
    }

    fn aid_fci() -> Vec<u8> {
        Tlv::constructed(
            tag::FCI_TEMPLATE,
            vec![
                Tlv::primitive(tag::DF_NAME, emv::AID.to_vec()),
                Tlv::constructed(
                    tag::FCI_PROPRIETARY,
                    vec![
                        Tlv::primitive(tag::APP_LABEL, emv::APP_LABEL.to_vec()),
                        Tlv::primitive(tag::PDOL, tlv::encode_dol(&emv::PDOL)),
                    ],
                ),
            ],
        )
        .to_bytes()
    }

    fn gpo(&mut self, cmd: &Command) -> Response {
        if !self.selected {
            return Response::status(sw::CONDITIONS_NOT_SATISFIED);
        }
        let pdol = match tlv::parse_all(&cmd.data).ok().as_deref() {
            Some([t]) if t.tag.0 == tag::COMMAND_TEMPLATE => t.bytes().map(<[u8]>::to_vec),
            _ => None,
        };
        let Some(pdol) = pdol else {
            return Response::status(sw::WRONG_DATA);
        };
        let Ok(pdol) = <[u8; emv::PDOL_DATA_LEN]>::try_from(pdol.as_slice()) else {
            return Response::status(sw::WRONG_DATA);
        };
        let Ok(td) = TerminalData::from_pdol_data(&pdol) else {
            return Response::status(sw::WRONG_DATA);
        };
        let cdcvm_required = td.amount_minor > self.policy.cdcvm_limit_minor;
        if cdcvm_required && !self.cdcvm_verified {
            return Response::status(sw::SEE_PHONE);
        }
        let now = (self.now)();
        let enforce = self.policy.enforce_local_limits;
        let Some(idx) = self
            .profile
            .luks
            .iter()
            .position(|l| !enforce || (l.uses_left > 0 && l.expires_at > now))
        else {
            return Response::status(sw::CONDITIONS_NOT_SATISFIED);
        };
        let Some(atc) = self.profile.atc.checked_add(1) else {
            return Response::status(sw::CONDITIONS_NOT_SATISFIED);
        };
        self.profile.atc = atc;
        let luk = &mut self.profile.luks[idx];
        luk.uses_left = luk.uses_left.saturating_sub(1);
        let mut cvr_bits = 0;
        if self.cdcvm_verified {
            cvr_bits |= cvr::CDCVM_PERFORMED;
        }
        if cdcvm_required {
            cvr_bits |= cvr::CDCVM_REQUIRED;
        }
        let iad = Iad {
            scheme_id: self.scheme.scheme_id(),
            luk_seq: luk.seq,
            cvr: cvr_bits,
        };
        let sk = self.scheme.session_key(&luk.key, atc);
        let cdol = emv::cdol_data(&pdol, emv::AIP, atc, &iad);
        let arqc = self.scheme.arqc(&sk, &cdol);
        self.last = Some(LastTxn { sk, arqc });
        // Bir martalik CDCVM: har tasdiq faqat bitta tranzaksiya uchun.
        self.cdcvm_verified = false;

        let t2 = Track2::new(self.profile.dpan.clone(), self.profile.expiry);
        let e = self.profile.expiry;
        let exp = emv::to_bcd::<3>(
            u64::from(e.year % 100) * 10_000 + u64::from(e.month) * 100 + u64::from(e.last_day()),
        )
        .unwrap_or([0; 3]);
        let body = Tlv::constructed(
            tag::RESPONSE_TEMPLATE_2,
            vec![
                Tlv::primitive(tag::AIP, emv::AIP.to_vec()),
                Tlv::primitive(tag::TRACK2, t2.to_emv()),
                Tlv::primitive(tag::PSN, vec![self.profile.psn]),
                Tlv::primitive(tag::APP_EXPIRY, exp.to_vec()),
                Tlv::primitive(tag::ATC, atc.to_be_bytes().to_vec()),
                Tlv::primitive(tag::ARQC, arqc.to_vec()),
                Tlv::primitive(tag::CID, vec![emv::CID_ARQC]),
                Tlv::primitive(tag::IAD, iad.to_bytes().to_vec()),
            ],
        );
        Response::ok(body.to_bytes())
    }
}

impl ApduHandler for SoftCard {
    fn process(&mut self, capdu: &[u8]) -> Vec<u8> {
        let Ok(cmd) = Command::parse(capdu) else {
            return Response::status(sw::WRONG_LENGTH).to_bytes();
        };
        let r = match (cmd.cla, cmd.ins) {
            (0x00, 0xA4) if cmd.p1 == 0x04 => {
                if cmd.data == emv::PPSE_NAME {
                    self.selected = false;
                    Response::ok(Self::ppse_fci())
                } else if cmd.data == emv::AID {
                    self.selected = true;
                    Response::ok(Self::aid_fci())
                } else {
                    self.selected = false;
                    Response::status(sw::FILE_NOT_FOUND)
                }
            }
            (0x80, 0xA8) => self.gpo(&cmd),
            (0x00 | 0x80, _) => Response::status(sw::INS_NOT_SUPPORTED),
            _ => Response::status(sw::CLA_NOT_SUPPORTED),
        };
        r.to_bytes()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::apdu::Response;

    fn card() -> SoftCard {
        let p = CardProfile {
            token_id: TokenId::from_random([1; 16]),
            dpan: Pan::from_prefix("990077000000123").unwrap(),
            expiry: CardExpiry::new(2029, 12).unwrap(),
            psn: 0,
            luks: vec![CardLuk {
                seq: 1,
                key: SecretKey16::from_bytes([7; 16]),
                expires_at: i64::MAX,
                uses_left: 2,
            }],
            atc: 0,
        };
        SoftCard::new(p, CardPolicy::default())
    }

    #[test]
    fn status_words() {
        let mut c = card();
        let r = |c: &mut SoftCard, b: &[u8]| Response::parse(&c.process(b)).unwrap().sw;
        // SELECT'siz GPO.
        assert_eq!(
            r(&mut c, &Command::gpo(&[0; 29]).to_bytes()),
            sw::CONDITIONS_NOT_SATISFIED
        );
        assert_eq!(
            r(&mut c, &Command::select(&[0xA0, 0, 0, 0, 3]).to_bytes()),
            sw::FILE_NOT_FOUND
        );
        assert_eq!(r(&mut c, &Command::select(&emv::AID).to_bytes()), sw::OK);
        assert_eq!(
            r(&mut c, &Command::gpo(&[0; 28]).to_bytes()),
            sw::WRONG_DATA
        );
        assert_eq!(r(&mut c, &[0x00, 0xB2, 0, 0, 0]), sw::INS_NOT_SUPPORTED);
        assert_eq!(r(&mut c, &[0x90, 0xB2, 0, 0, 0]), sw::CLA_NOT_SUPPORTED);
        assert_eq!(r(&mut c, &[0x00]), sw::WRONG_LENGTH);
    }
}
