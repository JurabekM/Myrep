//! Saqlanadigan model: tunel profillari, sozlamalar va ularni tekshirish (validatsiya).

use std::net::SocketAddr;

use serde::{Deserialize, Serialize};

/// ML-DSA-65 ochiq kaliti uzunligi (bayt).
pub const PUB_LEN: usize = 1952;

#[derive(Serialize, Deserialize, Clone, Copy, PartialEq, Eq, Debug)]
#[serde(rename_all = "snake_case")]
pub enum Role {
    /// Ilovani himoyalaydi: tarmoqdan tunelni qabul qilib, ilovaga uzatadi.
    Server,
    /// Serverga ulanadi: mahalliy portdagi ulanishlarni tunel orqali yuboradi.
    Client,
}

#[derive(Serialize, Deserialize, Clone, Copy, PartialEq, Eq, Debug)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    /// Asosiy rejim: AETHER-Q (ML-KEM-768 + X25519, ML-DSA-65).
    AetherQ,
    /// Qo'shimcha: standart TLS 1.3 + X25519MLKEM768 (aqctl gateway).
    Standard,
}

impl Role {
    pub fn label(self) -> &'static str {
        match self {
            Role::Server => "Server",
            Role::Client => "Klient",
        }
    }
}

impl Mode {
    pub fn label(self) -> &'static str {
        match self {
            Mode::AetherQ => "AETHER-Q",
            Mode::Standard => "Standart PQ-TLS",
        }
    }
}

/// Server allowlist'idagi bitta klient kaliti.
#[derive(Serialize, Deserialize, Clone, PartialEq, Debug)]
pub struct AllowEntry {
    pub label: String,
    pub pub_hex: String,
    #[serde(default)]
    pub added: String,
}

#[derive(Serialize, Deserialize, Clone, PartialEq, Debug)]
pub struct Profile {
    pub id: String,
    pub name: String,
    pub role: Role,
    pub mode: Mode,
    /// Server: tarmoqdan tinglash (masalan 0.0.0.0:9443). Klient: mahalliy port (127.0.0.1:7000).
    pub listen: String,
    /// Server: ilova manzili (upstream). Klient: server manzili (peer).
    pub target: String,
    /// Identity (kalit) nomi; klientda bo'sh bo'lishi mumkin (server klient kalitini talab qilmasa).
    #[serde(default)]
    pub identity: String,
    /// Klient: serverning pinned ochiq kaliti (hex).
    #[serde(default)]
    pub server_pub: String,
    /// Klient: server nomi (taklif faylidan).
    #[serde(default)]
    pub server_label: String,
    /// Server: taklif fayliga yoziladigan manzil (IP yoki domen). Bo'sh — avtomatik (asosiy IP).
    #[serde(default)]
    pub public_host: String,
    /// Server: klient kaliti talab qilinadi (mutual auth).
    #[serde(default = "yes")]
    pub require_client_auth: bool,
    #[serde(default)]
    pub allow: Vec<AllowEntry>,
    /// AETHER-Q: session resumption.
    #[serde(default = "yes")]
    pub resumption: bool,
    /// AETHER-Q server: PoW qiyinligi (0 — o'chiq).
    #[serde(default)]
    pub pow: u8,
    /// Dastur ochilganda avtomatik ishga tushirish.
    #[serde(default)]
    pub autostart: bool,
}

fn yes() -> bool {
    true
}

impl Profile {
    pub fn new(role: Role) -> Profile {
        let (listen, target) = match role {
            Role::Server => ("0.0.0.0:9443", "127.0.0.1:8080"),
            Role::Client => ("127.0.0.1:7000", ""),
        };
        Profile {
            id: new_id(),
            name: String::new(),
            role,
            mode: Mode::AetherQ,
            listen: listen.into(),
            target: target.into(),
            identity: String::new(),
            server_pub: String::new(),
            server_label: String::new(),
            public_host: String::new(),
            require_client_auth: true,
            allow: Vec::new(),
            resumption: true,
            pow: 0,
            autostart: false,
        }
    }

    /// "127.0.0.1:7000 → server:9443" ko'rinishidagi qisqa yo'nalish.
    pub fn route(&self) -> String {
        format!("{} → {}", self.listen, self.target)
    }

    /// Allowlist'dagi ochiq kalitlar (baytlarda).
    pub fn allow_keys(&self) -> Vec<Vec<u8>> {
        self.allow.iter().filter_map(|a| parse_pub_hex(&a.pub_hex)).collect()
    }
}

#[derive(Serialize, Deserialize, Clone, PartialEq, Debug)]
pub struct Settings {
    /// Dastur ochilganda `autostart` belgilangan tunellarni ishga tushirish.
    #[serde(default = "yes")]
    pub autostart_enabled: bool,
    /// Tunellar ishlab turganda oynani yopishdan oldin so'rash.
    #[serde(default = "yes")]
    pub confirm_exit: bool,
    /// Yangi kalitlarning amal qilish muddati (kun).
    #[serde(default = "default_days")]
    pub key_days: u32,
    /// Jurnalda saqlanadigan eng ko'p qator.
    #[serde(default = "default_log_cap")]
    pub log_cap: usize,
    /// Jurnalni kunlik faylga ham yozish.
    #[serde(default = "yes")]
    pub log_to_file: bool,
    /// aqctl.exe yo'li (standart rejim). Bo'sh — dastur yonidan avtomatik qidiriladi.
    #[serde(default)]
    pub aqctl_path: String,
}

fn default_days() -> u32 {
    90
}

fn default_log_cap() -> usize {
    5000
}

impl Default for Settings {
    fn default() -> Self {
        Settings {
            autostart_enabled: true,
            confirm_exit: true,
            key_days: default_days(),
            log_cap: default_log_cap(),
            log_to_file: true,
            aqctl_path: String::new(),
        }
    }
}

#[derive(Serialize, Deserialize, Clone, PartialEq, Debug)]
pub struct Config {
    #[serde(default = "one")]
    pub version: u32,
    #[serde(default)]
    pub profiles: Vec<Profile>,
    #[serde(default)]
    pub settings: Settings,
}

fn one() -> u32 {
    1
}

impl Default for Config {
    fn default() -> Self {
        Config { version: 1, profiles: Vec::new(), settings: Settings::default() }
    }
}

/// Noyob qisqa identifikator (vaqt + hisoblagich).
pub fn new_id() -> String {
    use std::sync::atomic::{AtomicU64, Ordering};
    static N: AtomicU64 = AtomicU64::new(0);
    let t = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
    format!("p{:x}{:x}", t, N.fetch_add(1, Ordering::Relaxed))
}

/// ML-DSA-65 ochiq kaliti (hex) → baytlar; uzunlik noto'g'ri bo'lsa None.
pub fn parse_pub_hex(s: &str) -> Option<Vec<u8>> {
    let t: String = s.chars().filter(|c| !c.is_whitespace()).collect();
    let b = aq_core::identity::from_hex(&t.to_ascii_lowercase())?;
    (b.len() == PUB_LEN).then_some(b)
}

/// "host:port" → (host, port).
pub fn split_host_port(s: &str) -> Option<(String, u16)> {
    let s = s.trim();
    let i = s.rfind(':')?;
    let (h, p) = (&s[..i], &s[i + 1..]);
    let port: u16 = p.parse().ok()?;
    let h = h.trim_start_matches('[').trim_end_matches(']');
    if h.is_empty() || port == 0 {
        return None;
    }
    Some((h.to_string(), port))
}

/// Tekshiruv natijasi: qaysi maydon va nima noto'g'ri. `blocking` — saqlash/ishga tushirishga to'sqinlik qiladi.
#[derive(Clone, Debug, PartialEq)]
pub struct Issue {
    pub field: &'static str,
    pub msg: String,
    pub blocking: bool,
}

fn issue(field: &'static str, msg: impl Into<String>) -> Issue {
    Issue { field, msg: msg.into(), blocking: true }
}

fn warn(field: &'static str, msg: impl Into<String>) -> Issue {
    Issue { field, msg: msg.into(), blocking: false }
}

/// Profilni tekshiradi. `keys` — mavjud identity nomlari; `others` — boshqa profillar (port to'qnashuvi uchun).
pub fn validate(p: &Profile, keys: &[String], others: &[Profile], aqctl_found: bool) -> Vec<Issue> {
    let mut out = Vec::new();
    if p.name.trim().is_empty() {
        out.push(issue("name", "Nom kiriting (masalan, «Ofis serveri»)."));
    }
    match p.listen.trim().parse::<SocketAddr>() {
        Err(_) => out.push(issue("listen", "Tinglash manzili IP:port ko'rinishida bo'lsin (masalan 127.0.0.1:7000).")),
        Ok(a) if a.port() == 0 => out.push(issue("listen", "Port 1..65535 oralig'ida bo'lsin.")),
        Ok(a) => {
            if let Some(o) = others.iter().find(|o| {
                o.id != p.id && o.listen.trim().parse::<SocketAddr>().map(|b| b.port() == a.port()).unwrap_or(false)
            }) {
                out.push(warn(
                    "listen",
                    format!("{} porti «{}» profilida ham ishlatilgan — ikkalasi bir vaqtda ishlay olmaydi.", a.port(), o.name),
                ));
            }
        }
    }
    let target_field = if p.role == Role::Server { "Ilova manzili" } else { "Server manzili" };
    if split_host_port(&p.target).is_none() {
        out.push(issue("target", format!("{target_field} host:port ko'rinishida bo'lsin (masalan 192.168.1.10:9443).")));
    }
    let has_key = |n: &str| keys.iter().any(|k| k == n);
    match p.role {
        Role::Server => {
            if p.identity.is_empty() {
                out.push(issue("identity", "Server uchun kalit (identity) tanlang yoki yarating."));
            } else if !has_key(&p.identity) {
                out.push(issue("identity", format!("«{}» kaliti topilmadi.", p.identity)));
            }
            if p.require_client_auth && p.allow.is_empty() {
                out.push(warn("allow", "Allowlist bo'sh: hech bir klient ulana olmaydi. Klient ruxsat so'rovini import qiling."));
            }
            if !p.require_client_auth {
                out.push(warn("auth", "Klient kaliti talab qilinmaydi: server kalitini bilgan har kim ulana oladi."));
            }
            let local_only = p.listen.trim().parse::<SocketAddr>().map(|a| a.ip().is_loopback()).unwrap_or(false);
            let ph = p.public_host.trim();
            if local_only && !ph.is_empty() && ph != "127.0.0.1" && ph != "localhost" && ph != "::1" {
                out.push(warn(
                    "public_host",
                    format!("Server faqat shu kompyuterda tinglaydi, lekin taklifda «{ph}» — boshqa kompyuterdan ulanib bo'lmaydi."),
                ));
            }
        }
        Role::Client => {
            if p.server_pub.trim().is_empty() {
                out.push(issue("server_pub", "Server ochiq kalitini kiriting yoki taklif faylini import qiling."));
            } else if parse_pub_hex(&p.server_pub).is_none() {
                out.push(issue("server_pub", "Server kaliti noto'g'ri: 3904 belgili hex (ML-DSA-65) bo'lishi kerak."));
            }
            if !p.identity.is_empty() && !has_key(&p.identity) {
                out.push(issue("identity", format!("«{}» kaliti topilmadi.", p.identity)));
            }
            if p.identity.is_empty() {
                out.push(warn("identity", "Klient kaliti tanlanmagan: server klient kalitini talab qilsa, ulanish rad etiladi."));
            }
        }
    }
    if p.mode == Mode::Standard && !aqctl_found {
        out.push(issue("mode", "Standart rejim uchun aqctl.exe kerak — Sozlamalar sahifasida yo'lini ko'rsating."));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn good_server() -> Profile {
        let mut p = Profile::new(Role::Server);
        p.name = "Ofis".into();
        p.identity = "srv".into();
        p.allow.push(AllowEntry { label: "pc".into(), pub_hex: "ab".repeat(PUB_LEN), added: String::new() });
        p
    }

    #[test]
    fn valid_server_has_no_blocking_issues() {
        let p = good_server();
        let v = validate(&p, &["srv".into()], &[], true);
        assert!(v.iter().all(|i| !i.blocking), "{v:?}");
        assert_eq!(p.allow_keys().len(), 1);
    }

    #[test]
    fn detects_bad_fields() {
        let mut p = Profile::new(Role::Client);
        p.listen = "localhost".into();
        p.target = "nohost".into();
        p.server_pub = "zz".into();
        let v = validate(&p, &[], &[], false);
        let fields: Vec<_> = v.iter().filter(|i| i.blocking).map(|i| i.field).collect();
        for f in ["name", "listen", "target", "server_pub"] {
            assert!(fields.contains(&f), "{f} yo'q: {v:?}");
        }
    }

    #[test]
    fn standard_mode_needs_aqctl_and_port_conflicts_warn() {
        let mut a = good_server();
        a.mode = Mode::Standard;
        assert!(validate(&a, &["srv".into()], &[], false).iter().any(|i| i.field == "mode" && i.blocking));
        let mut b = good_server();
        b.id = "other".into();
        b.name = "Boshqa".into();
        let v = validate(&a, &["srv".into()], &[b], true);
        assert!(v.iter().any(|i| i.field == "listen" && !i.blocking));
    }

    #[test]
    fn local_server_with_foreign_public_host_warns() {
        let mut p = good_server();
        p.listen = "127.0.0.1:9443".into();
        p.public_host = "192.168.1.10".into();
        let v = validate(&p, &["srv".into()], &[], true);
        assert!(v.iter().any(|i| i.field == "public_host" && !i.blocking), "{v:?}");
        p.public_host = "127.0.0.1".into();
        assert!(!validate(&p, &["srv".into()], &[], true).iter().any(|i| i.field == "public_host"));
    }

    #[test]
    fn host_port_and_pub_parsing() {
        assert_eq!(split_host_port("example.com:9443"), Some(("example.com".into(), 9443)));
        assert_eq!(split_host_port("[::1]:7000"), Some(("::1".into(), 7000)));
        assert_eq!(split_host_port("host:0"), None);
        assert_eq!(split_host_port("host"), None);
        assert!(parse_pub_hex(&"AB".repeat(PUB_LEN)).is_some());
        assert!(parse_pub_hex(&"ab".repeat(PUB_LEN - 1)).is_none());
    }

    #[test]
    fn config_json_defaults_are_backward_compatible() {
        let c: Config = serde_json::from_str(r#"{"profiles":[{"id":"x","name":"n","role":"client","mode":"aether_q","listen":"127.0.0.1:1","target":"h:2"}]}"#).unwrap();
        assert!(c.profiles[0].resumption && c.profiles[0].require_client_auth);
        assert_eq!(c.settings, Settings::default());
    }
}
