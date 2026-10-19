//! TAMGA Studio — Tauri qobig'i. Jurnalni fayldan o'qiydi, boshqaruv buyruqlarini `tamgad` ga yuboradi.

mod data;

use std::sync::Mutex;
use std::time::Duration;

use serde::Serialize;
use serde_json::{Value, json};
use tamga_store::home::{AskRoute, Mode};
use tamga_store::{Home, client};

#[derive(Debug, Serialize)]
pub struct AppInfo {
    pub version: &'static str,
    pub format_version: &'static str,
}

struct AppState {
    home: Home,
    cache: Mutex<data::Cache>,
}

#[tauri::command]
fn app_info() -> AppInfo {
    AppInfo {
        version: env!("CARGO_PKG_VERSION"),
        format_version: tamga_core::FORMAT_VERSION,
    }
}

/// `tamgad` ga so'rov. Daemon ishlamasa, Studio yonidagi `tamgad.exe` ni ishga tushiradi.
fn daemon(req: Value) -> Value {
    let exe = std::env::current_exe()
        .ok()
        .and_then(|p| {
            p.parent().map(|d| {
                d.join(if cfg!(windows) {
                    "tamgad.exe"
                } else {
                    "tamgad"
                })
            })
        })
        .filter(|p| p.exists());
    match client::connect_auto(exe.as_deref(), Duration::from_secs(3))
        .and_then(|mut p| client::request(&mut p, &req))
    {
        Ok(v) => v,
        Err(e) => json!({"ok": false, "error": e.to_string()}),
    }
}

#[tauri::command]
async fn status() -> Value {
    tauri::async_runtime::spawn_blocking(|| daemon(json!({"op": "status"})))
        .await
        .unwrap_or_else(|e| json!({"ok": false, "error": e.to_string()}))
}

#[tauri::command]
async fn pending() -> Value {
    tauri::async_runtime::spawn_blocking(|| daemon(json!({"op": "pending"})))
        .await
        .unwrap_or_else(|e| json!({"ok": false, "error": e.to_string()}))
}

#[tauri::command]
async fn policies() -> Value {
    tauri::async_runtime::spawn_blocking(|| daemon(json!({"op": "policies"})))
        .await
        .unwrap_or_else(|e| json!({"ok": false, "error": e.to_string()}))
}

#[tauri::command]
async fn decide(seq: u64, verdict: String, scope: String) -> Value {
    tauri::async_runtime::spawn_blocking(move || {
        daemon(json!({"op": "decide", "seq": seq, "verdict": verdict, "scope": scope}))
    })
    .await
    .unwrap_or_else(|e| json!({"ok": false, "error": e.to_string()}))
}

/// Imzo kalitini almashtirish (spec §7.5): yozuv + eski kalit checkpoint'i + yangi kalit.
#[tauri::command]
async fn rotate_key(reason: String) -> Value {
    tauri::async_runtime::spawn_blocking(move || daemon(json!({"op": "rotate", "reason": reason})))
        .await
        .unwrap_or_else(|e| json!({"ok": false, "error": e.to_string()}))
}

#[tauri::command]
async fn checkpoint_now() -> Value {
    tauri::async_runtime::spawn_blocking(|| daemon(json!({"op": "checkpoint"})))
        .await
        .unwrap_or_else(|e| json!({"ok": false, "error": e.to_string()}))
}

/// `after` dan keyingi yozuvlar (ixcham). `after` berilmasa — oxirgi `limit` ta.
#[tauri::command]
fn records(state: tauri::State<'_, AppState>, after: Option<u64>, limit: Option<usize>) -> Value {
    let mut cache = state.cache.lock().expect("kesh");
    if let Err(e) = cache.refresh(&state.home) {
        return json!({"ok": false, "error": e});
    }
    let all = cache.records();
    let limit = limit.unwrap_or(500);
    let items: Vec<Value> = match after {
        Some(a) => all
            .iter()
            .filter(|r| r["seq"].as_u64().is_some_and(|s| s > a))
            .take(limit)
            .map(data::compact)
            .collect(),
        None => all[all.len().saturating_sub(limit)..]
            .iter()
            .map(data::compact)
            .collect(),
    };
    json!({"ok": true, "total": all.len(), "items": items})
}

#[tauri::command]
fn record_detail(state: tauri::State<'_, AppState>, seq: u64) -> Value {
    let mut cache = state.cache.lock().expect("kesh");
    let _ = cache.refresh(&state.home);
    data::record_detail(&state.home, cache.records(), seq)
}

#[tauri::command]
fn sessions(state: tauri::State<'_, AppState>) -> Value {
    let mut cache = state.cache.lock().expect("kesh");
    if let Err(e) = cache.refresh(&state.home) {
        return json!({"ok": false, "error": e});
    }
    json!({"ok": true, "items": data::sessions(cache.records())})
}

#[tauri::command]
fn session_records(state: tauri::State<'_, AppState>, session: String) -> Value {
    let mut cache = state.cache.lock().expect("kesh");
    let _ = cache.refresh(&state.home);
    let items: Vec<Value> = cache
        .records()
        .iter()
        .filter(|r| r["session"] == session.as_str())
        .map(data::compact)
        .collect();
    json!({"ok": true, "items": items})
}

#[tauri::command]
async fn verify(state: tauri::State<'_, AppState>) -> Result<Value, String> {
    let home = state.home.clone();
    tauri::async_runtime::spawn_blocking(move || data::verify(&home))
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn config_get(state: tauri::State<'_, AppState>) -> Value {
    let c = state.home.config();
    json!({"ok": true, "home": state.home.root().display().to_string(), "config": c.to_json()})
}

/// Rejim va `ask` yo'nalishini o'zgartiradi. Daemon config'ni har soniyada qayta o'qiydi.
#[tauri::command]
fn config_set(
    state: tauri::State<'_, AppState>,
    mode: Option<String>,
    ask_route: Option<String>,
) -> Value {
    let mut c = state.home.config();
    if let Some(m) = mode {
        c.mode = if m == "strict" {
            Mode::Strict
        } else {
            Mode::Dev
        };
    }
    if let Some(r) = ask_route {
        c.ask_route = if r == "studio" {
            AskRoute::Studio
        } else {
            AskRoute::Agent
        };
    }
    match state.home.write_config(&c) {
        Ok(()) => json!({"ok": true, "config": c.to_json()}),
        Err(e) => json!({"ok": false, "error": e.to_string()}),
    }
}

/// Dalil to'plami (ZIP) `<TAMGA_HOME>/exports/` ga.
#[tauri::command]
async fn export_bundle(
    state: tauri::State<'_, AppState>,
    sessions: Vec<String>,
    include_payloads: bool,
) -> Result<Value, String> {
    let home = state.home.clone();
    tauri::async_runtime::spawn_blocking(move || {
        use tamga_store::export::{ExportOptions, default_path, export};
        let vault = if include_payloads {
            let store = tamga_store::secrets::default_store(&home).map_err(|e| e.to_string())?;
            let master = tamga_store::keystore::vault_master(store.as_ref()).map_err(|e| e.to_string())?;
            Some(tamga_store::vault::Vault::new(home.vault(), master).map_err(|e| e.to_string())?)
        } else {
            None
        };
        let opts = ExportOptions { sessions, include_payloads, out: default_path(&home) };
        let r = export(&home, vault.as_ref(), &opts).map_err(|e| e.to_string())?;
        Ok::<_, String>(json!({
            "ok": true, "path": r.path.display().to_string(), "records": r.records, "checkpoints": r.checkpoints,
            "payloads": r.payloads, "shredded": r.shredded, "verified": r.verified, "sha256": r.sha256,
        }))
    })
    .await
    .map_err(|e| e.to_string())?
}

/// Avval yaratilgan dalil to'plamlari (eng yangisi birinchi).
#[tauri::command]
fn list_exports(state: tauri::State<'_, AppState>) -> Value {
    let dir = state.home.root().join("exports");
    let mut items: Vec<(std::time::SystemTime, Value)> = std::fs::read_dir(&dir)
        .into_iter()
        .flatten()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().extension().is_some_and(|x| x == "zip"))
        .filter_map(|e| {
            let m = e.metadata().ok()?;
            let t = m.modified().ok()?;
            let secs = t.duration_since(std::time::UNIX_EPOCH).ok()?.as_millis() as i64;
            Some((t, json!({"path": e.path().display().to_string(), "name": e.file_name().to_string_lossy(), "size": m.len(), "ts": tamga_store::format_ts(secs)})))
        })
        .collect();
    items.sort_by_key(|(t, _)| std::cmp::Reverse(*t));
    json!({"ok": true, "dir": dir.display().to_string(), "items": items.into_iter().map(|(_, v)| v).collect::<Vec<_>>()})
}

/// Faylni Explorer'da belgilab ko'rsatadi (faqat TAMGA eksport papkasi ichidagi fayllar).
#[tauri::command]
fn reveal(state: tauri::State<'_, AppState>, path: String) -> Value {
    let dir = state.home.root().join("exports");
    let p = std::path::PathBuf::from(&path);
    let inside = p
        .canonicalize()
        .ok()
        .zip(dir.canonicalize().ok())
        .is_some_and(|(p, d)| p.starts_with(d));
    if !inside {
        return json!({"ok": false, "error": "faqat eksport papkasidagi fayllar ko'rsatiladi"});
    }
    // Explorer faqat Windows ko'rinishidagi yo'lni tushunadi (teskari chiziq, `\\?\` prefiksisiz).
    let win_path = p.display().to_string().replace('/', "\\");
    match std::process::Command::new("explorer")
        .arg(format!("/select,{win_path}"))
        .spawn()
    {
        Ok(_) => json!({"ok": true}),
        Err(e) => json!({"ok": false, "error": e.to_string()}),
    }
}

fn sibling(name: &str) -> Option<std::path::PathBuf> {
    let exe = if cfg!(windows) {
        format!("{name}.exe")
    } else {
        name.to_owned()
    };
    std::env::current_exe()
        .ok()?
        .parent()
        .map(|d| d.join(exe))
        .filter(|p| p.exists())
}

/// Claude Code (foydalanuvchi darajasi) integratsiyasi holati.
#[tauri::command]
fn integration_status() -> Value {
    let settings = match tamga_store::integrate::target(&["--user"]) {
        Ok(p) => p,
        Err(e) => return json!({"ok": false, "error": e}),
    };
    let installed = tamga_store::integrate::installed(&settings);
    json!({
        "ok": installed.is_ok(),
        "settings": settings.display().to_string(),
        "installed": installed.as_ref().ok(),
        "error": installed.err(),
        "hook": sibling("tamga-hook").map(|p| p.display().to_string()),
    })
}

/// Foydalanuvchi Studio'da bosganda: `~/.claude/settings.json` ga hook'larni qo'shish yoki olib tashlash
/// (zaxira nusxa bilan; boshqa sozlamalar saqlanadi).
#[tauri::command]
fn integrate(action: String) -> Value {
    let settings = match tamga_store::integrate::target(&["--user"]) {
        Ok(p) => p,
        Err(e) => return json!({"ok": false, "error": e}),
    };
    let r = match action.as_str() {
        "install" => match sibling("tamga-hook") {
            Some(hook) => tamga_store::integrate::install(&settings, &hook).map(|()| 5),
            None => Err("tamga-hook.exe Studio bilan bir papkada topilmadi".into()),
        },
        "uninstall" => tamga_store::integrate::uninstall(&settings),
        _ => Err("noma'lum amal".into()),
    };
    match r {
        Ok(n) => json!({"ok": true, "changed": n, "settings": settings.display().to_string()}),
        Err(e) => json!({"ok": false, "error": e}),
    }
}

pub fn run() {
    tauri::Builder::default()
        .manage(AppState {
            home: Home::from_env(),
            cache: Mutex::new(data::Cache::default()),
        })
        .invoke_handler(tauri::generate_handler![
            app_info,
            status,
            pending,
            policies,
            decide,
            checkpoint_now,
            rotate_key,
            records,
            record_detail,
            sessions,
            session_records,
            verify,
            config_get,
            config_set,
            export_bundle,
            list_exports,
            reveal,
            integration_status,
            integrate
        ])
        .run(tauri::generate_context!())
        .expect("TAMGA Studio ishga tushmadi");
}
