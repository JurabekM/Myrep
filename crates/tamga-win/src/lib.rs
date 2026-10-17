//! Windows'ga xos yordamchilar. Workspace'dagi **yagona** `unsafe` kod shu yerda.
//!
//! Muammo: Rust std Windows'da bola jarayonni `bInheritHandles = TRUE` bilan yaratadi
//! (`inherit_handles(false)` hali barqaror emas, rust-lang/rust#146407). Shunda chaqiruvchidagi
//! **barcha** meros qilinadigan handle'lar daemon'ga o'tadi: hook'ning stdout'i (Claude Code
//! yaratgan pipe), yoki PowerShell `tamga.exe` ga bergan boshqa pipe'lar. Daemon uzoq yashaydi,
//! va o'sha pipe'larni o'qiyotgan tomon EOF'ni daemon to'xtaguncha kutib qoladi.
//!
//! Dastlabki yechim (F2) faqat joriy jarayonning std handle'larini meros qilinmaydigan qilardi —
//! F8 demosida PowerShell orqali ishga tushirilganda boshqa meros handle'lar baribir o'tib ketdi.
//! Endi daemon `CreateProcessW(bInheritHandles = FALSE)` bilan yaratiladi: hech qanday handle
//! meros bo'lmaydi, std handle'lar bo'sh (daemon faqat o'z log fayliga yozadi).

use std::path::Path;

/// Jarayonni konsolsiz, mustaqil va chaqiruvchidan **hech qanday** handle meros qilmasdan ishga tushiradi.
/// Muhit o'zgaruvchilari (`TAMGA_HOME`, `TAMGA_PIPE` ...) va joriy papka meros bo'ladi.
#[cfg(windows)]
#[allow(unsafe_code)]
pub fn spawn_detached(exe: &Path) -> std::io::Result<()> {
    use std::os::windows::ffi::OsStrExt as _;
    use windows_sys::Win32::Foundation::CloseHandle;
    use windows_sys::Win32::System::Threading::{
        CREATE_NEW_PROCESS_GROUP, CREATE_NO_WINDOW, CREATE_UNICODE_ENVIRONMENT, CreateProcessW,
        DETACHED_PROCESS, PROCESS_INFORMATION, STARTUPINFOW,
    };

    let wide = |s: &std::ffi::OsStr| {
        s.encode_wide()
            .chain(std::iter::once(0))
            .collect::<Vec<u16>>()
    };
    let app = wide(exe.as_os_str());
    // Buyruq qatori: faqat qo'shtirnoqdagi yo'l (argumentlar yo'q). CreateProcessW uni o'zgartirishi
    // mumkin, shuning uchun alohida o'zgaruvchan bufer.
    let mut quoted = std::ffi::OsString::from("\"");
    quoted.push(exe.as_os_str());
    quoted.push("\"");
    let mut cmdline = wide(&quoted);
    if app.contains(&u16::from(b'"')) {
        return Err(std::io::Error::other("yo'lda qo'shtirnoq bor"));
    }

    let si = STARTUPINFOW {
        cb: u32::try_from(size_of::<STARTUPINFOW>()).expect("STARTUPINFOW o'lchami"),
        ..Default::default()
    };
    let mut pi = PROCESS_INFORMATION::default();
    // SAFETY: `app` va `cmdline` NUL bilan tugaydigan UTF-16 buferlar va chaqiruv davomida yashaydi;
    // `cmdline` o'zgaruvchan (API talabi). Xavfsizlik atributlari, muhit va joriy papka uchun null —
    // chaqiruvchinikidan foydalaniladi. `si.cb` to'g'ri o'rnatilgan, qolgan maydonlar nol (std handle
    // berilmaydi). `bInheritHandles = 0` — hech qanday handle bolaga o'tmaydi. `pi` — chiqish buferi.
    let ok = unsafe {
        CreateProcessW(
            app.as_ptr(),
            cmdline.as_mut_ptr(),
            std::ptr::null(),
            std::ptr::null(),
            0,
            DETACHED_PROCESS
                | CREATE_NEW_PROCESS_GROUP
                | CREATE_NO_WINDOW
                | CREATE_UNICODE_ENVIRONMENT,
            std::ptr::null(),
            std::ptr::null(),
            &si,
            &mut pi,
        )
    };
    if ok == 0 {
        return Err(std::io::Error::last_os_error());
    }
    // SAFETY: muvaffaqiyatli CreateProcessW `pi` ga ikkita haqiqiy, bizga tegishli handle yozdi;
    // ular boshqa joyda ishlatilmaydi va bir martadan yopiladi. Yopish jarayonni to'xtatmaydi.
    unsafe {
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
    }
    Ok(())
}

#[cfg(not(windows))]
pub fn spawn_detached(exe: &Path) -> std::io::Result<()> {
    use std::process::{Command, Stdio};
    Command::new(exe)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map(drop)
}
