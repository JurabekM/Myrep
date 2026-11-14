//! Oynasiz UI sinovlari: har bir sahifa va modal oyna chiziladi (panic yo'q), amallar haqiqiy tunellar bilan
//! bajariladi. Fayl dialoglari (rfd) chaqirilmaydi — ular foydalanuvchi oynasini kutadi.

use std::path::PathBuf;
use std::time::{Duration, Instant};

use crate::app::{Action, App, Confirm, Page};
use crate::engine::Status;
use crate::keys;
use crate::model::{Profile, Role};
use crate::ui::wizard::Scenario;

fn tmp_root(tag: &str) -> PathBuf {
    std::env::temp_dir().join(format!("aq-studio-ui-{tag}-{}", crate::model::new_id()))
}

/// Bir kadr (1320×820 ekran) — UI kodi to'liq yuradi.
fn frame(ctx: &egui::Context, app: &mut App) {
    let raw = egui::RawInput {
        screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(1320.0, 820.0))),
        ..Default::default()
    };
    let mut out = ctx.run_ui(raw, |ui| app.frame(ui));
    // Renderer yo'q: tekstura o'zgarishlarini qo'llamay tashlaymiz.
    out.textures_delta.clear();
}

fn ctx() -> egui::Context {
    let c = egui::Context::default();
    crate::theme::install_fonts(&c);
    crate::theme::apply(&c);
    c
}

fn all_pages(ctx: &egui::Context, app: &mut App) {
    for p in Page::ALL {
        app.page = p;
        frame(ctx, app);
        frame(ctx, app);
    }
}

#[test]
fn every_page_and_modal_renders_empty_and_populated() {
    let root = tmp_root("render");
    let c = ctx();
    let mut app = App::new(root.clone());
    // Bo'sh holat: har sahifa, usta (har stsenariy), muharrir (ikkala rol).
    all_pages(&c, &mut app);
    for s in [None, Some(Scenario::Demo), Some(Scenario::Server), Some(Scenario::Client)] {
        app.apply(Action::OpenWizard(s));
        frame(&c, &mut app);
        frame(&c, &mut app);
        assert!(app.wizard.is_some(), "usta ochiq qolishi kerak");
        app.wizard = None;
    }
    for r in [Role::Server, Role::Client] {
        app.apply(Action::NewProfile(r));
        frame(&c, &mut app);
        assert!(app.editor.is_some(), "muharrir ochiq qolishi kerak");
        app.editor = None;
    }

    // To'ldirilgan holat: kalitlar, server + klient, ishlab turgan tunellar.
    let kd = app.store.keys_dir();
    let srv = keys::create(&kd, "srv", 30).unwrap();
    let cli = keys::create(&kd, "cli", 5).unwrap(); // tez orada muddati tugaydi — ogohlantirish holati
    app.refresh_keys();
    let free = || std::net::TcpListener::bind("127.0.0.1:0").unwrap().local_addr().unwrap().port();
    let mut s = Profile::new(Role::Server);
    s.name = "Server".into();
    s.listen = format!("127.0.0.1:{}", free());
    s.identity = srv.name.clone();
    let mut k = Profile::new(Role::Client);
    k.name = "Klient".into();
    k.listen = format!("127.0.0.1:{}", free());
    k.target = "127.0.0.1:9".into();
    k.identity = cli.name.clone();
    k.server_pub = srv.pub_hex();
    app.save_profile(s.clone()).unwrap();
    app.save_profile(k.clone()).unwrap();
    app.start(&s.id).unwrap();
    app.start(&k.id).unwrap();
    all_pages(&c, &mut app);
    app.selected = Some(s.id.clone());
    app.page = Page::Tunnels;
    frame(&c, &mut app);
    app.selected = Some(k.id.clone());
    frame(&c, &mut app);
    app.apply(Action::Edit(s.id.clone()));
    frame(&c, &mut app);
    assert!(app.editor.is_some());
    app.editor = None;
    for conf in [
        Confirm::DeleteProfile(s.id.clone()),
        Confirm::DeleteKey("cli".into()),
        Confirm::RotateKey("srv".into()),
        Confirm::RemoveAllow(s.id.clone(), 0),
        Confirm::Exit,
    ] {
        app.confirm = Some(conf);
        frame(&c, &mut app);
        assert!(app.confirm.is_some(), "tasdiqlash oynasi ochiq qolishi kerak");
        app.confirm = None;
    }
    // Jurnal filtrlari va qidiruv bilan.
    app.logs_ui.search = "ishga".into();
    app.logs_ui.level = crate::app::LevelFilter::Problems;
    app.page = Page::Logs;
    frame(&c, &mut app);
    app.shutdown();
    let _ = std::fs::remove_dir_all(&root);
}

fn wait(app: &mut App, mut f: impl FnMut(&mut App) -> bool) -> bool {
    let t = Instant::now();
    while t.elapsed() < Duration::from_secs(10) {
        app.engine.tick();
        if f(app) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(20));
    }
    false
}

#[test]
fn wizard_demo_creates_working_chain_and_actions_work() {
    let root = tmp_root("actions");
    let c = ctx();
    let mut app = App::new(root.clone());
    // Usta: demo stsenariysi — kalitlar, sinov serveri, ikki profil, ikkala tunel va HTTP sinovi.
    let mut w = crate::ui::wizard::Wizard::new(Some(Scenario::Demo), &app);
    w.create_for_test(&mut app).expect("demo yaratilmadi");
    assert_eq!(app.store.cfg.profiles.len(), 2);
    let (sid, cid) = (app.store.cfg.profiles[0].id.clone(), app.store.cfg.profiles[1].id.clone());
    assert_eq!(app.engine.status(&sid), Status::Running);
    assert_eq!(app.engine.status(&cid), Status::Running);
    assert!(app.diag.test_server.is_some(), "ichki sinov serveri ishga tushishi kerak");
    // Klient sinovi: tunel orqali GET / → sinov serveri javobi.
    app.test_profile(&cid).unwrap();
    assert!(wait(&mut app, |a| {
        a.frame_tasks_for_test();
        a.probe_results.iter().any(|(id, _)| id == &cid)
    }));
    let r = &app.probe_results.iter().find(|(id, _)| id == &cid).unwrap().1;
    let p = r.as_ref().expect("tunel sinovi muvaffaqiyatsiz");
    assert!(p.status_line.contains("200") && p.preview.contains("sinov serveri"), "{p:?}");
    frame(&c, &mut app);

    // Taklif va ruxsat so'rovi JSON'lari to'g'ri formatda.
    let inv = keys::parse_invite(&app.invite_json(&sid).unwrap()).unwrap();
    assert_eq!(inv.name, "Demo server");
    assert!(inv.address.starts_with("127.0.0.1:"), "lokal server taklifi 127.0.0.1 bo'lsin: {}", inv.address);
    // Foydalanuvchi kiritgan tashqi manzil (domen) taklifga yoziladi.
    let mut sp = app.profile(&sid).unwrap().clone();
    sp.public_host = "vpn.example.uz".into();
    let port = crate::model::split_host_port(&sp.listen).unwrap().1;
    app.save_profile(sp).unwrap();
    let inv2 = keys::parse_invite(&app.invite_json(&sid).unwrap()).unwrap();
    assert_eq!(inv2.address, format!("vpn.example.uz:{port}"));
    let req = app.request_json(&cid).unwrap();
    // So'rov nomi — kompyuter nomi (profil nomi emas).
    let parsed: keys::AccessRequest = serde_json::from_str(&req).unwrap();
    assert!(parsed.name.ends_with("kompyuteri"), "{}", parsed.name);
    // So'rovni allowlist'ga qayta qo'shish — takror sifatida rad etiladi.
    assert!(app.add_allow(&sid, &req, "").unwrap_err().contains("allaqachon"));
    // Yangi klient kaliti so'rovi — qo'shiladi.
    let extra = keys::create(&app.store.keys_dir(), "pc-2", 30).unwrap();
    let req2 = serde_json::to_string(&keys::make_request("PC-2", &extra)).unwrap();
    assert!(app.add_allow(&sid, &req2, "").unwrap().contains("PC-2"));
    assert_eq!(app.profile(&sid).unwrap().allow.len(), 2);
    assert!(app.remove_allow(&sid, 1).is_ok());

    // Ishlatilayotgan kalitni o'chirib bo'lmaydi; rotatsiya profilni yangi kalitga o'tkazadi.
    let skey = app.profile(&sid).unwrap().identity.clone();
    assert!(app.delete_key(&skey).unwrap_err().contains("ishlatilmoqda"));
    app.refresh_keys();
    let msg = app.rotate_key(&skey).unwrap();
    let new_key = app.profile(&sid).unwrap().identity.clone();
    assert_ne!(new_key, skey, "{msg}");
    assert_eq!(app.engine.status(&sid), Status::Running, "rotatsiyadan keyin qayta ishga tushishi kerak");
    // Endi eski kalit ishlatilmaydi — o'chiriladi.
    assert!(app.delete_key(&skey).is_ok());

    // Nusxa, to'xtatish, o'chirish.
    let dup = app.duplicate_profile(&cid).unwrap();
    assert_ne!(app.profile(&dup).unwrap().listen, app.profile(&cid).unwrap().listen, "nusxa boshqa portda");
    app.apply(Action::StopAll);
    assert_eq!(app.engine.running_count(), 0);
    app.delete_profile(&dup);
    assert_eq!(app.store.cfg.profiles.len(), 2);
    // Saqlangan konfiguratsiya qayta ochiladi.
    let again = App::new(root.clone());
    assert_eq!(again.store.cfg.profiles.len(), 2);
    app.shutdown();
    let _ = std::fs::remove_dir_all(&root);
}

/// UI matnlaridagi har bir maxsus belgi (emoji, strelka, tire…) yuklangan shriftlarda bo'lishi kerak —
/// aks holda ekranda kvadrat ("tofu") chiqadi. Manba fayllaridagi satr literallaridan yig'iladi.
#[test]
fn every_symbol_in_ui_strings_has_a_glyph() {
    use skrifa::MetadataProvider;
    let defs = crate::theme::font_definitions();
    let chain = defs.families.get(&egui::FontFamily::Proportional).cloned().unwrap_or_default();
    let faces: Vec<skrifa::FontRef> = chain
        .iter()
        .filter_map(|k| defs.font_data.get(k))
        .filter_map(|d| skrifa::FontRef::from_index(&d.font, d.index).ok())
        .collect();
    assert!(faces.len() >= 3, "shrift zanjiri bo'sh");
    let mut files = Vec::new();
    let mut stack = vec![PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src")];
    while let Some(d) = stack.pop() {
        for e in std::fs::read_dir(&d).unwrap().flatten() {
            let p = e.path();
            if p.is_dir() {
                stack.push(p);
            } else if p.extension().is_some_and(|x| x == "rs") && !p.ends_with("tests_ui.rs") {
                files.push(p);
            }
        }
    }
    let mut missing = std::collections::BTreeMap::<char, String>::new();
    let mut checked = 0;
    for f in files {
        let text = std::fs::read_to_string(&f).unwrap();
        for (n, line) in text.lines().enumerate() {
            let t = line.trim_start();
            if t.starts_with("//") || t.starts_with("#[") {
                continue;
            }
            let (Some(a), Some(b)) = (line.find('"'), line.rfind('"')) else { continue };
            if b <= a {
                continue;
            }
            for ch in line[a + 1..b].chars().filter(|c| !c.is_ascii() && !c.is_alphabetic()) {
                checked += 1;
                // `Fonts::has_glyph` ishonchsiz: almashtiruvchi belgi turgan shriftdagi belgilar uchun ham false beradi.
                // Shuning uchun dasturdagi bilan bir xil shrift zanjirining cmap jadvallari to'g'ridan-to'g'ri tekshiriladi.
                let ok = faces.iter().any(|f| f.charmap().map(ch).is_some());
                if !ok {
                    missing.entry(ch).or_insert_with(|| format!("{}:{}", f.file_name().unwrap().to_string_lossy(), n + 1));
                }
            }
        }
    }
    assert!(checked > 50, "belgilar yig'ilmadi");
    assert!(missing.is_empty(), "shriftda yo'q belgilar (U+): {:?}", missing.iter().map(|(c, w)| format!("{c} U+{:04X} {w}", *c as u32)).collect::<Vec<_>>());
}

#[test]
fn starting_invalid_profile_gives_clear_reason() {
    let root = tmp_root("invalid");
    let mut app = App::new(root.clone());
    let mut p = Profile::new(Role::Client);
    p.name = "Yaroqsiz".into();
    let id = p.id.clone();
    app.store.cfg.profiles.push(p);
    let e = app.start(&id).unwrap_err();
    assert!(e.contains("Server manzili") || e.contains("Server ochiq kalitini"), "{e}");
    assert_eq!(app.engine.running_count(), 0);
    let _ = std::fs::remove_dir_all(&root);
}

