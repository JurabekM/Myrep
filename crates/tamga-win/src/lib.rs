//! Windows'ga xos yordamchilar. Workspace'dagi **yagona** `unsafe` kod shu yerda.
//!
//! Muammo: Rust std Windows'da bola jarayonni `bInheritHandles = TRUE` bilan yaratadi
//! (`inherit_handles(false)` hali barqaror emas, rust-lang/rust#146407). Hook'ning stdout'i —
//! Claude Code yaratgan meros qilinadigan pipe. Hook daemon'ni ishga tushirsa, daemon shu pipe'ni
//! meros qilib oladi va Claude Code hook chiqishining EOF'ini daemon to'xtaguncha kutib qoladi.
//!
//! Yechim: bola jarayon yaratishdan oldin joriy jarayonning std handle'laridan
//! `HANDLE_FLAG_INHERIT` bayrog'i olib tashlanadi. Handle'lar ishlashda davom etadi — faqat
//! bolalarga o'tmaydi.

use std::path::Path;
use std::process::{Command, Stdio};

/// Joriy jarayonning stdin/stdout/stderr handle'larini meros qilinmaydigan qiladi.
#[cfg(windows)]
#[allow(unsafe_code)]
pub fn make_std_handles_private() {
    use windows_sys::Win32::Foundation::{
        HANDLE_FLAG_INHERIT, INVALID_HANDLE_VALUE, SetHandleInformation,
    };
    use windows_sys::Win32::System::Console::{
        GetStdHandle, STD_ERROR_HANDLE, STD_INPUT_HANDLE, STD_OUTPUT_HANDLE,
    };
    for id in [STD_INPUT_HANDLE, STD_OUTPUT_HANDLE, STD_ERROR_HANDLE] {
        // SAFETY: GetStdHandle faqat joriy jarayon jadvalidagi handle qiymatini o'qiydi, xotiraga yozmaydi.
        let h = unsafe { GetStdHandle(id) };
        if h.is_null() || h == INVALID_HANDLE_VALUE {
            continue;
        }
        // SAFETY: `h` joriy jarayonning haqiqiy std handle'i (null/invalid emasligi yuqorida tekshirildi);
        // SetHandleInformation faqat uning meros bayrog'ini o'zgartiradi, egaligi va yopilishiga ta'sir qilmaydi.
        // Xato qaytsa (masalan, konsol psevdo-handle) — e'tiborsiz: eng yomoni, handle meros bo'lib qoladi.
        let _ = unsafe { SetHandleInformation(h, HANDLE_FLAG_INHERIT, 0) };
    }
}

#[cfg(not(windows))]
pub fn make_std_handles_private() {}

/// Jarayonni konsolsiz, mustaqil va chaqiruvchining std handle'larini meros qilmasdan ishga tushiradi.
pub fn spawn_detached(exe: &Path) -> std::io::Result<()> {
    make_std_handles_private();
    let mut cmd = Command::new(exe);
    cmd.stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt as _;
        const DETACHED_PROCESS: u32 = 0x0000_0008;
        const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW);
    }
    cmd.spawn().map(drop)
}
