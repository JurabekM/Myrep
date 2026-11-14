//! Himoyalangan (xizmat) rejimi uchun FFI: DPAPI, pipe xavfsizlik deskriptori, pipe mijozining
//! identifikatori (SID + administrator huquqi) va server jarayonining exe yo'li.
//!
//! Har bir `unsafe` blok minimal; xotira egasi va umri `SAFETY` izohida ko'rsatilgan.

use std::ffi::c_void;
use std::io;
use std::os::windows::ffi::OsStrExt as _;
use std::os::windows::io::AsRawHandle;
use std::path::PathBuf;

use windows_sys::Win32::Foundation::{CloseHandle, HANDLE, LocalFree};

fn wide(s: &str) -> Vec<u16> {
    std::ffi::OsStr::new(s)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect()
}

// ---------------------------------------------------------------- mashina papkasi

/// `%ProgramData%` — Windows'ning ma'lum papka API'si orqali, **muhit o'zgaruvchisidan emas**:
/// `ProgramData` o'zgaruvchisini har bir jarayon o'zi uchun o'zgartira oladi va shu bilan mijozni
/// himoyalangan rejim belgisini ko'rmaydigan qilib, oddiy rejimga (o'z daemon'iga) o'tkazishi mumkin edi.
#[allow(unsafe_code)]
pub fn program_data() -> Option<PathBuf> {
    use windows_sys::Win32::System::Com::CoTaskMemFree;
    use windows_sys::Win32::UI::Shell::{FOLDERID_ProgramData, SHGetKnownFolderPath};
    let mut out: windows_sys::core::PWSTR = std::ptr::null_mut();
    // SAFETY: `FOLDERID_ProgramData` — statik GUID; token null (joriy foydalanuvchi, ProgramData uchun
    // ahamiyatsiz); `out` — chiqish, API `CoTaskMemAlloc` bilan ajratgan NUL bilan tugaydigan satr yozadi.
    let hr =
        unsafe { SHGetKnownFolderPath(&FOLDERID_ProgramData, 0, std::ptr::null_mut(), &mut out) };
    if out.is_null() {
        return None;
    }
    // SAFETY: muvaffaqiyatda `out` NUL bilan tugaydigan UTF-16 satr; uzunlikni NUL gacha sanab
    // nusxalaymiz. Bufer xato bo'lganda ham `CoTaskMemFree` bilan bir marta bo'shatiladi (hujjat talabi).
    let s = unsafe {
        let s = (hr >= 0).then(|| {
            let mut n = 0;
            while *out.add(n) != 0 {
                n += 1;
            }
            String::from_utf16_lossy(std::slice::from_raw_parts(out, n))
        });
        CoTaskMemFree(out.cast());
        s
    };
    s.filter(|s| !s.is_empty()).map(PathBuf::from)
}

// ---------------------------------------------------------------- DPAPI

/// DPAPI bilan shifrlash, **mashina doirasida** (`CRYPTPROTECT_LOCAL_MACHINE`). Faylni o'qiy oladigan
/// har kim ochishi mumkin — shuning uchun maxfiylik fayl ACL'i bilan ta'minlanadi (faqat xizmat
/// hisobi, SYSTEM va administratorlar). Virtual xizmat hisobida foydalanuvchi profili bo'lmasligi
/// mumkinligi sababli foydalanuvchi doirasi ishlatilmaydi. `entropy` — maqsadni bog'laydi.
#[allow(unsafe_code)]
pub fn dpapi_protect(data: &[u8], entropy: &[u8]) -> io::Result<Vec<u8>> {
    dpapi(data, entropy, true)
}

/// [`dpapi_protect`] teskarisi. Natija nusxalangandan keyin tizim buferi nollanib bo'shatiladi.
#[allow(unsafe_code)]
pub fn dpapi_unprotect(data: &[u8], entropy: &[u8]) -> io::Result<Vec<u8>> {
    dpapi(data, entropy, false)
}

#[allow(unsafe_code)]
fn dpapi(data: &[u8], entropy: &[u8], protect: bool) -> io::Result<Vec<u8>> {
    use windows_sys::Win32::Security::Cryptography::{
        CRYPT_INTEGER_BLOB, CRYPTPROTECT_LOCAL_MACHINE, CRYPTPROTECT_UI_FORBIDDEN,
        CryptProtectData, CryptUnprotectData,
    };
    let len =
        |s: &[u8]| u32::try_from(s.len()).map_err(|_| io::Error::other("ma'lumot juda katta"));
    let input = CRYPT_INTEGER_BLOB {
        cbData: len(data)?,
        pbData: data.as_ptr().cast_mut(),
    };
    let ent = CRYPT_INTEGER_BLOB {
        cbData: len(entropy)?,
        pbData: entropy.as_ptr().cast_mut(),
    };
    let mut out = CRYPT_INTEGER_BLOB::default();
    let mut flags = CRYPTPROTECT_UI_FORBIDDEN;
    if protect {
        flags |= CRYPTPROTECT_LOCAL_MACHINE;
    }
    // SAFETY: `input` va `ent` chaqiruv davomida tirik bo'lgan `data`/`entropy` ga ishora qiladi;
    // API ularni faqat o'qiydi (`*const`), shuning uchun `cast_mut` yozishga olib kelmaydi. Ixtiyoriy
    // parametrlar null. `out` — chiqish; muvaffaqiyatda API uni `LocalAlloc` bufer bilan to'ldiradi.
    let ok = unsafe {
        if protect {
            CryptProtectData(
                &input,
                std::ptr::null(),
                &ent,
                std::ptr::null(),
                std::ptr::null(),
                flags,
                &mut out,
            )
        } else {
            CryptUnprotectData(
                &input,
                std::ptr::null_mut(),
                &ent,
                std::ptr::null(),
                std::ptr::null(),
                flags,
                &mut out,
            )
        }
    };
    if ok == 0 {
        return Err(io::Error::last_os_error());
    }
    let n = out.cbData as usize;
    // SAFETY: muvaffaqiyatli chaqiruvdan keyin `out.pbData` aynan `out.cbData` baytli, API ajratgan
    // va bizga tegishli buferga ishora qiladi; uni bir marta o'qiymiz.
    let v = unsafe { std::slice::from_raw_parts(out.pbData, n) }.to_vec();
    // SAFETY: o'sha bufer: avval nollaymiz (ochiq kalit materiali qolmasin), so'ng `LocalFree` bilan
    // bir marta bo'shatamiz; shundan keyin `out.pbData` ishlatilmaydi.
    unsafe {
        std::ptr::write_bytes(out.pbData, 0, n);
        LocalFree(out.pbData.cast());
    }
    Ok(v)
}

// ---------------------------------------------------------------- pipe xavfsizligi

/// SDDL'dan qurilgan xavfsizlik deskriptori (`LocalFree` bilan bo'shatiladi).
pub struct SecurityDescriptor(*mut c_void);

// SAFETY: deskriptor yaratilgandan keyin o'zgarmaydigan, jarayonga tegishli bufer; uni bir nechta
// oqim faqat o'qiydi (CreateNamedPipeW'ga uzatish). Bo'shatish faqat `Drop` da, bir marta.
#[allow(unsafe_code)]
unsafe impl Send for SecurityDescriptor {}
// SAFETY: yuqoridagi sabab — umumiy o'qish xavfsiz.
#[allow(unsafe_code)]
unsafe impl Sync for SecurityDescriptor {}

impl SecurityDescriptor {
    #[allow(unsafe_code)]
    pub fn from_sddl(sddl: &str) -> io::Result<Self> {
        use windows_sys::Win32::Security::Authorization::{
            ConvertStringSecurityDescriptorToSecurityDescriptorW, SDDL_REVISION_1,
        };
        let w = wide(sddl);
        let mut sd: *mut c_void = std::ptr::null_mut();
        // SAFETY: `w` — NUL bilan tugaydigan UTF-16 satr, chaqiruv davomida tirik. `sd` — chiqish;
        // muvaffaqiyatda API `LocalAlloc` bufer yozadi (o'lcham kerak emas — null).
        let ok = unsafe {
            ConvertStringSecurityDescriptorToSecurityDescriptorW(
                w.as_ptr(),
                SDDL_REVISION_1,
                &mut sd,
                std::ptr::null_mut(),
            )
        };
        if ok == 0 || sd.is_null() {
            return Err(io::Error::last_os_error());
        }
        Ok(Self(sd))
    }
}

impl Drop for SecurityDescriptor {
    #[allow(unsafe_code)]
    fn drop(&mut self) {
        // SAFETY: `self.0` — `from_sddl` dagi muvaffaqiyatli API ajratgan bufer, faqat shu yerda bir
        // marta bo'shatiladi.
        unsafe {
            LocalFree(self.0);
        }
    }
}

/// Xizmat pipe'i uchun SDDL: SYSTEM, administratorlar va egasi (xizmat) — to'liq; autentifikatsiya
/// qilingan foydalanuvchilar — faqat o'qish/yozish/atribut o'qish/sinxronlash
/// (`0x00100083`). `GENERIC_WRITE` berilmaydi: u `FILE_CREATE_PIPE_INSTANCE` ni ham o'z ichiga oladi,
/// bu esa foydalanuvchiga xuddi shu nomdagi soxta server nusxasini yaratishga imkon berardi.
pub const SERVICE_PIPE_SDDL: &str = "D:P(A;;GA;;;SY)(A;;GA;;;BA)(A;;GA;;;OW)(A;;0x00100083;;;AU)";

/// Berilgan xavfsizlik deskriptori bilan pipe serveri nusxasini yaratadi.
#[allow(unsafe_code)]
pub fn create_pipe_server(
    opts: &tokio::net::windows::named_pipe::ServerOptions,
    name: &str,
    sd: &SecurityDescriptor,
) -> io::Result<tokio::net::windows::named_pipe::NamedPipeServer> {
    use windows_sys::Win32::Security::SECURITY_ATTRIBUTES;
    let mut sa = SECURITY_ATTRIBUTES {
        nLength: u32::try_from(size_of::<SECURITY_ATTRIBUTES>()).expect("o'lcham"),
        lpSecurityDescriptor: sd.0,
        bInheritHandle: 0,
    };
    // SAFETY: `sa` va u ishora qiladigan deskriptor (`sd` qarzga olingan) chaqiruv davomida tirik;
    // CreateNamedPipeW atributlarni faqat chaqiruv vaqtida o'qiydi. `bInheritHandle = 0`.
    unsafe { opts.create_with_security_attributes_raw(name, (&raw mut sa).cast()) }
}

// ---------------------------------------------------------------- mijoz identifikatori

/// Pipe mijozining Windows identifikatori.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClientIdentity {
    /// Foydalanuvchi SID'i (`S-1-5-21-…`).
    pub sid: String,
    /// Token administrator sifatida ko'tarilganmi (UAC tasdiqlangan).
    pub elevated: bool,
}

/// Impersonatsiyani har qanday yo'l bilan tugatadi. `RevertToSelf` muvaffaqiyatsiz bo'lsa jarayon
/// to'xtatiladi: begona token bilan davom etish xavfsizlik chegarasini buzardi.
struct Revert;

impl Drop for Revert {
    #[allow(unsafe_code)]
    fn drop(&mut self) {
        // SAFETY: argumentsiz, joriy oqimning impersonatsiyasini tugatadi.
        if unsafe { windows_sys::Win32::Security::RevertToSelf() } == 0 {
            std::process::abort();
        }
    }
}

/// Server tomonidagi pipe handle'i orqali mijozning SID'i va ko'tarilganligi. Mijoz kamida bitta
/// xabar yozgandan keyin chaqiriladi (impersonatsiya talabi).
#[allow(unsafe_code)]
pub fn pipe_client_identity(pipe: &impl AsRawHandle) -> Option<ClientIdentity> {
    use windows_sys::Win32::Security::{GetTokenInformation, TOKEN_QUERY};
    use windows_sys::Win32::System::Pipes::ImpersonateNamedPipeClient;
    use windows_sys::Win32::System::Threading::{GetCurrentThread, OpenThreadToken};

    let mut token: HANDLE = std::ptr::null_mut();
    {
        // SAFETY: `pipe` qarzga olingan ochiq server handle'i; muvaffaqiyatda joriy oqim mijoz
        // tokeni bilan impersonatsiya qilinadi va `Revert` blok oxirida uni tugatadi.
        if unsafe { ImpersonateNamedPipeClient(pipe.as_raw_handle()) } == 0 {
            return None;
        }
        let _revert = Revert;
        // SAFETY: `GetCurrentThread` psevdo-handle; `token` — chiqish. `OpenAsSelf = TRUE` — kirish
        // tekshiruvi xizmatning o'z huquqi bilan (impersonatsiya qilingan mijoznikida emas).
        if unsafe { OpenThreadToken(GetCurrentThread(), TOKEN_QUERY, 1, &mut token) } == 0 {
            return None;
        }
    }
    let close = |t: HANDLE| {
        // SAFETY: `t` — `OpenThreadToken` qaytargan, bizga tegishli handle; bir marta yopiladi.
        unsafe { CloseHandle(t) };
    };

    // TOKEN_USER (ichida ko'rsatkich) — 8 baytga tekislangan bufer kerak.
    let mut buf = vec![0u64; 64];
    let mut ret = 0u32;
    let bytes = u32::try_from(buf.len() * 8).expect("o'lcham");
    // SAFETY: `token` — ochiq, TOKEN_QUERY huquqli handle; `buf` — `bytes` baytli, tekislangan, yoziladigan
    // bufer; `ret` — chiqish.
    let ok = unsafe {
        GetTokenInformation(
            token,
            windows_sys::Win32::Security::TokenUser,
            buf.as_mut_ptr().cast(),
            bytes,
            &mut ret,
        )
    };
    if ok == 0 {
        close(token);
        return None;
    }
    // SAFETY: muvaffaqiyatda bufer boshida to'g'ri tekislangan `TOKEN_USER` turadi; uning `Sid`
    // ko'rsatkichi shu bufer ichiga ishora qiladi va `buf` tirikligida yaroqli.
    let sid_ptr = unsafe {
        (*buf
            .as_ptr()
            .cast::<windows_sys::Win32::Security::TOKEN_USER>())
        .User
        .Sid
    };
    let sid = sid_string(sid_ptr);

    let mut elev = windows_sys::Win32::Security::TOKEN_ELEVATION::default();
    let size =
        u32::try_from(size_of::<windows_sys::Win32::Security::TOKEN_ELEVATION>()).expect("o'lcham");
    // SAFETY: `elev` — to'g'ri o'lchamdagi chiqish strukturasi; `token` hali ochiq.
    let ok = unsafe {
        GetTokenInformation(
            token,
            windows_sys::Win32::Security::TokenElevation,
            (&raw mut elev).cast(),
            size,
            &mut ret,
        )
    };
    close(token);
    Some(ClientIdentity {
        sid: sid?,
        elevated: ok != 0 && elev.TokenIsElevated != 0,
    })
}

#[allow(unsafe_code)]
fn sid_string(sid: *mut c_void) -> Option<String> {
    use windows_sys::Win32::Security::Authorization::ConvertSidToStringSidW;
    let mut out: *mut u16 = std::ptr::null_mut();
    // SAFETY: `sid` — tirik `TOKEN_USER` buferidagi yaroqli SID; `out` — chiqish (LocalAlloc satr).
    if unsafe { ConvertSidToStringSidW(sid, &mut out) } == 0 || out.is_null() {
        return None;
    }
    // SAFETY: `out` NUL bilan tugaydigan UTF-16 satr; uzunlikni NUL gacha sanaymiz, nusxalaymiz va
    // bufer bir marta `LocalFree` bilan bo'shatiladi.
    let s = unsafe {
        let mut n = 0;
        while *out.add(n) != 0 {
            n += 1;
        }
        let s = String::from_utf16_lossy(std::slice::from_raw_parts(out, n));
        LocalFree(out.cast());
        s
    };
    Some(s)
}

// ---------------------------------------------------------------- server tekshiruvi (mijoz tomoni)

/// Mijoz tomonidagi pipe handle'i orqali server jarayonining PID'i.
#[allow(unsafe_code)]
pub fn pipe_server_pid(pipe: &impl AsRawHandle) -> Option<u32> {
    use windows_sys::Win32::System::Pipes::GetNamedPipeServerProcessId;
    let mut pid = 0u32;
    // SAFETY: `pipe` qarzga olingan ochiq handle; `pid` — 4 baytli chiqish.
    if unsafe { GetNamedPipeServerProcessId(pipe.as_raw_handle(), &mut pid) } == 0 || pid == 0 {
        return None;
    }
    Some(pid)
}

/// Jarayonning to'liq exe yo'li (cheklangan so'rov huquqi bilan).
#[allow(unsafe_code)]
pub fn process_image(pid: u32) -> Option<PathBuf> {
    use windows_sys::Win32::System::Threading::{
        OpenProcess, PROCESS_NAME_WIN32, PROCESS_QUERY_LIMITED_INFORMATION,
        QueryFullProcessImageNameW,
    };
    // SAFETY: faqat cheklangan so'rov huquqi bilan ochiladi; natija null bo'lsa xato.
    let h = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid) };
    if h.is_null() {
        return None;
    }
    let mut buf = vec![0u16; 32_768];
    let mut size = u32::try_from(buf.len()).expect("o'lcham");
    // SAFETY: `h` — ochiq jarayon handle'i; `buf` — `size` belgilik yoziladigan bufer; `size` — kirish/chiqish.
    let ok =
        unsafe { QueryFullProcessImageNameW(h, PROCESS_NAME_WIN32, buf.as_mut_ptr(), &mut size) };
    // SAFETY: `h` — `OpenProcess` qaytargan bizga tegishli handle, bir marta yopiladi.
    unsafe { CloseHandle(h) };
    (ok != 0).then(|| PathBuf::from(String::from_utf16_lossy(&buf[..size as usize])))
}

/// Mijoz tomonidagi pipe handle'i orqali server jarayonining to'liq exe yo'li.
pub fn pipe_server_image(pipe: &impl AsRawHandle) -> Option<PathBuf> {
    process_image(pipe_server_pid(pipe)?)
}

/// Xizmat ishlab turgan bo'lsa — SCM bo'yicha uning jarayon PID'i. Mijoz pipe serveri aynan shu
/// jarayon ekanini tekshiradi: exe yo'li yetarli emas, chunki oddiy foydalanuvchi ham o'rnatish
/// papkasidagi `tamgad.exe` ni o'z huquqi bilan ishga tushira oladi (xizmat to'xtagan paytda pipe
/// nomini egallash uchun). `SERVICE_QUERY_STATUS` interaktiv foydalanuvchilarga standart ochiq.
pub fn service_pid(name: &str) -> Option<u32> {
    use windows_service::service::{ServiceAccess, ServiceState};
    use windows_service::service_manager::{ServiceManager, ServiceManagerAccess};
    let scm = ServiceManager::local_computer(None::<&str>, ServiceManagerAccess::CONNECT).ok()?;
    let svc = scm.open_service(name, ServiceAccess::QUERY_STATUS).ok()?;
    let st = svc.query_status().ok()?;
    (st.current_state == ServiceState::Running)
        .then_some(st.process_id)
        .flatten()
        .filter(|&p| p != 0)
}

// ---------------------------------------------------------------- UAC bilan ishga tushirish

/// Argumentni Windows buyruq qatori qoidalari bo'yicha qo'shtirnoqqa oladi.
fn quote_arg(a: &str) -> String {
    if !a.is_empty() && !a.chars().any(|c| c.is_whitespace() || c == '"') {
        return a.to_owned();
    }
    let mut out = String::from("\"");
    let mut backslashes = 0;
    for c in a.chars() {
        match c {
            '\\' => backslashes += 1,
            '"' => {
                out.push_str(&"\\".repeat(backslashes * 2 + 1));
                out.push('"');
                backslashes = 0;
            }
            _ => {
                out.push_str(&"\\".repeat(backslashes));
                out.push(c);
                backslashes = 0;
            }
        }
    }
    out.push_str(&"\\".repeat(backslashes * 2));
    out.push('"');
    out
}

/// `exe` ni administrator sifatida ishga tushiradi (UAC so'rovi xavfsiz ish stolida — uni faqat
/// foydalanuvchi tasdiqlaydi), tugashini kutadi va chiqish kodini qaytaradi. Foydalanuvchi rad etsa —
/// `ERROR_CANCELLED` (1223) xatosi.
#[allow(unsafe_code)]
pub fn run_elevated(exe: &std::path::Path, args: &[&str]) -> io::Result<u32> {
    use windows_sys::Win32::System::Threading::{
        GetExitCodeProcess, INFINITE, WaitForSingleObject,
    };
    use windows_sys::Win32::UI::Shell::{
        SEE_MASK_NOASYNC, SEE_MASK_NOCLOSEPROCESS, SHELLEXECUTEINFOW, ShellExecuteExW,
    };
    use windows_sys::Win32::UI::WindowsAndMessaging::SW_HIDE;

    let verb = wide("runas");
    let file = wide(&exe.to_string_lossy());
    let params = wide(
        &args
            .iter()
            .map(|a| quote_arg(a))
            .collect::<Vec<_>>()
            .join(" "),
    );
    let mut info = SHELLEXECUTEINFOW {
        cbSize: u32::try_from(size_of::<SHELLEXECUTEINFOW>()).expect("o'lcham"),
        fMask: SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC,
        lpVerb: verb.as_ptr(),
        lpFile: file.as_ptr(),
        lpParameters: params.as_ptr(),
        nShow: SW_HIDE,
        ..Default::default()
    };
    // SAFETY: `info` to'g'ri `cbSize` bilan to'ldirilgan; satr ko'rsatkichlari NUL bilan tugaydigan,
    // chaqiruv davomida tirik `verb`/`file`/`params` buferlariga ishora qiladi. Muvaffaqiyatda API
    // `hProcess` ga bizga tegishli jarayon handle'ini yozadi (`SEE_MASK_NOCLOSEPROCESS`).
    if unsafe { ShellExecuteExW(&mut info) } == 0 {
        return Err(io::Error::last_os_error());
    }
    let h = info.hProcess;
    if h.is_null() {
        return Err(io::Error::other("jarayon handle'i qaytmadi"));
    }
    let mut code = 0u32;
    // SAFETY: `h` — ochiq, bizga tegishli jarayon handle'i; kutish va chiqish kodini o'qish, so'ng bir
    // marta yopish. `code` — 4 baytli chiqish.
    let ok = unsafe {
        WaitForSingleObject(h, INFINITE);
        let ok = GetExitCodeProcess(h, &mut code);
        CloseHandle(h);
        ok
    };
    if ok == 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(code)
}

// ---------------------------------------------------------------- Windows xizmati (SCM)

/// Xizmat tanasi: SCM `Stop`/`Shutdown` yuborganda `stop` kanaliga signal tushadi. Qaytgan qiymat —
/// xizmatga xos chiqish kodi (0 — muvaffaqiyat).
pub type ServiceBody = fn(stop: std::sync::mpsc::Receiver<()>) -> u32;

/// Windows xizmati nomi (o'rnatuvchi `sc create tamgad` bilan yaratadi).
pub const SERVICE_NAME: &str = "tamgad";

static RUNNING_AS: std::sync::OnceLock<String> = std::sync::OnceLock::new();
static SERVICE_BODY: std::sync::OnceLock<ServiceBody> = std::sync::OnceLock::new();

// Makro `extern "system"` kirish nuqtasini yaratadi (ichida `unsafe` bor — shuning uchun shu crate'da).
windows_service::define_windows_service!(ffi_service_main, service_main);

fn service_main(_args: Vec<std::ffi::OsString>) {
    use windows_service::service::{
        ServiceControl, ServiceControlAccept, ServiceExitCode, ServiceState, ServiceStatus,
        ServiceType,
    };
    use windows_service::service_control_handler::{self, ServiceControlHandlerResult};

    let (Some(name), Some(body)) = (RUNNING_AS.get(), SERVICE_BODY.get()) else {
        return;
    };
    let (tx, rx) = std::sync::mpsc::channel();
    let handler = move |ev| match ev {
        ServiceControl::Stop | ServiceControl::Shutdown => {
            let _ = tx.send(());
            ServiceControlHandlerResult::NoError
        }
        ServiceControl::Interrogate => ServiceControlHandlerResult::NoError,
        _ => ServiceControlHandlerResult::NotImplemented,
    };
    let Ok(status) = service_control_handler::register(name, handler) else {
        return;
    };
    let report = |state, accept, exit| {
        let _ = status.set_service_status(ServiceStatus {
            service_type: ServiceType::OWN_PROCESS,
            current_state: state,
            controls_accepted: accept,
            exit_code: exit,
            checkpoint: 0,
            wait_hint: std::time::Duration::from_secs(10),
            process_id: None,
        });
    };
    report(
        ServiceState::Running,
        ServiceControlAccept::STOP | ServiceControlAccept::SHUTDOWN,
        ServiceExitCode::Win32(0),
    );
    let code = body(rx);
    report(
        ServiceState::Stopped,
        ServiceControlAccept::empty(),
        if code == 0 {
            ServiceExitCode::Win32(0)
        } else {
            ServiceExitCode::ServiceSpecific(code)
        },
    );
}

/// SCM dispetcherini ishga tushiradi (bloklaydi). Faqat xizmat sifatida (SCM tomonidan) ishga
/// tushirilganda ishlaydi; oddiy jarayondan chaqirilsa xato qaytadi.
pub fn run_as_service(name: &str, body: ServiceBody) -> io::Result<()> {
    let _ = RUNNING_AS.set(name.to_owned());
    let _ = SERVICE_BODY.set(body);
    windows_service::service_dispatcher::start(name, ffi_service_main).map_err(io::Error::other)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dpapi_round_trip_and_entropy_binding() {
        let secret = b"imzo urug'i: 64 bayt sinov";
        let ct = dpapi_protect(secret, b"tamga-test").unwrap();
        assert_ne!(ct.as_slice(), secret.as_slice());
        assert_eq!(dpapi_unprotect(&ct, b"tamga-test").unwrap(), secret);
        assert!(
            dpapi_unprotect(&ct, b"boshqa-maqsad").is_err(),
            "entropy bog'langan"
        );
    }

    #[test]
    fn arguments_are_quoted_for_the_command_line() {
        assert_eq!(quote_arg("decide"), "decide");
        assert_eq!(quote_arg("a b"), "\"a b\"");
        assert_eq!(quote_arg(""), "\"\"");
        assert_eq!(quote_arg("x\"y"), "\"x\\\"y\"");
        assert_eq!(quote_arg(r"C:\Program Files\"), "\"C:\\Program Files\\\\\"");
    }

    #[test]
    fn program_data_comes_from_the_known_folder() {
        let p = program_data().expect("ProgramData");
        assert!(p.is_absolute(), "{}", p.display());
        assert!(p.is_dir(), "{}", p.display());
    }

    #[test]
    fn missing_service_has_no_pid() {
        assert_eq!(service_pid("tamga-bunday-xizmat-yoq"), None);
    }

    #[test]
    fn sddl_parses_and_rejects_garbage() {
        assert!(SecurityDescriptor::from_sddl(SERVICE_PIPE_SDDL).is_ok());
        assert!(SecurityDescriptor::from_sddl("bu SDDL emas").is_err());
    }

    #[test]
    fn secured_pipe_reports_client_and_server() {
        use tokio::io::{AsyncReadExt as _, AsyncWriteExt as _};
        use tokio::net::windows::named_pipe::{ClientOptions, ServerOptions};
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        rt.block_on(async {
            let name = format!(r"\\.\pipe\tamga-win-test-{}", std::process::id());
            let sd = SecurityDescriptor::from_sddl(SERVICE_PIPE_SDDL).unwrap();
            let mut server =
                create_pipe_server(ServerOptions::new().first_pipe_instance(true), &name, &sd)
                    .unwrap();
            let mut client = ClientOptions::new().open(&name).unwrap();
            server.connect().await.unwrap();
            client.write_all(b"salom\n").await.unwrap();
            let mut b = [0u8; 6];
            server.read_exact(&mut b).await.unwrap();

            let id = pipe_client_identity(&server).expect("mijoz identifikatori");
            assert!(id.sid.starts_with("S-1-5-"), "{}", id.sid);
            assert_eq!(pipe_server_pid(&client), Some(std::process::id()));
            let img = pipe_server_image(&client).expect("server exe");
            let me = std::env::current_exe().unwrap();
            assert_eq!(
                std::fs::canonicalize(img).unwrap(),
                std::fs::canonicalize(me).unwrap(),
                "server — shu test jarayoni"
            );
        });
    }
}
