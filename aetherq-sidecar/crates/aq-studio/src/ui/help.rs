//! Qo'llanma: sidecar nima, qanday ishga tushiriladi, kalit almashinuvi, xatolar va yechimlar.

use egui::{RichText, Ui};

use crate::app::{Action, App};
use crate::theme::{self, ACCENT, AMBER, BLUE, FAINT, MUTED, TEXT, VIOLET};
use crate::ui::wizard::Scenario;

fn para(ui: &mut Ui, t: &str) {
    ui.add(egui::Label::new(RichText::new(t).color(MUTED)).wrap());
}

fn step(ui: &mut Ui, n: &str, t: &str) {
    ui.horizontal_top(|ui| {
        ui.label(RichText::new(n).font(theme::heading(14.0)).color(ACCENT));
        ui.add(egui::Label::new(RichText::new(t).color(TEXT)).wrap());
    });
}

impl App {
    pub fn page_help(&mut self, ui: &mut Ui) {
        let mut acts = Vec::new();
        theme::card(ui, |ui| {
            theme::section(ui, "Sidecar nima?", "");
            para(
                ui,
                "Sidecar — ilovangiz yonida ishlaydigan yordamchi dastur. Ilova odatdagidek oddiy TCP ulanish ochadi, sidecar esa \
                 bu trafikni AETHER-Q post-kvant tunelida shifrlab, qarshi tomondagi sidecar'ga uzatadi. Ilova kodini o'zgartirish shart emas.",
            );
            ui.add_space(6.0);
            ui.horizontal_wrapped(|ui| {
                for (i, (t, c)) in [("Ilova (klient)", BLUE), ("Klient sidecar", VIOLET), ("AETHER-Q tunel", ACCENT), ("Server sidecar", VIOLET), ("Ilova (server)", BLUE)]
                    .iter()
                    .enumerate()
                {
                    theme::badge(ui, t, *c);
                    if i < 4 {
                        ui.label(RichText::new("→").color(FAINT));
                    }
                }
            });
            ui.add_space(6.0);
            para(
                ui,
                "Nega kerak: bugungi shifrlash (RSA, ECDH) kelajakdagi kvant kompyuterlarga chidamsiz. Hujumchi trafikni bugun yozib olib, \
                 keyin ochishi mumkin. AETHER-Q kalit almashinuvi ML-KEM-768 + X25519 va ML-DSA-65 imzolariga asoslangan.",
            );
        });
        ui.add_space(8.0);
        ui.columns(2, |cols| {
            theme::card(&mut cols[0], |ui| {
                theme::section(ui, "Server tomonda (ilovani himoyalash)", "");
                step(ui, "1.", "«Tez sozlash ustasi» → «Server». Ilova manzili va tunel portini kiriting.");
                step(ui, "2.", "Taklif faylini (.aqinvite) saqlab, klientga yuboring (pochta, messenjer — maxfiy emas).");
                step(ui, "3.", "Klient qaytargan ruxsat so'rovini (.aqrequest) Tunellar → Allowlist'ga import qiling.");
                step(ui, "4.", "Windows Firewall so'rasa — tunel portiga ruxsat bering.");
                ui.horizontal(|ui| {
                    if theme::small(ui, "Server ustasini ochish", true).clicked() {
                        acts.push(Action::OpenWizard(Some(Scenario::Server)));
                    }
                });
            });
            theme::card(&mut cols[1], |ui| {
                theme::section(ui, "Klient tomonda (serverga ulanish)", "");
                step(ui, "1.", "«Tez sozlash ustasi» → «Klient». Server yuborgan taklif faylini tanlang.");
                step(ui, "2.", "Barmoq izini server administratori bilan telefonda solishtiring.");
                step(ui, "3.", "Ruxsat so'rovini saqlab, serverga yuboring.");
                step(ui, "4.", "Server qo'shgach «Sinash» tugmasini bosing. Ilovangiz 127.0.0.1:<port> ga ulanadi.");
                ui.horizontal(|ui| {
                    if theme::small(ui, "Klient ustasini ochish", true).clicked() {
                        acts.push(Action::OpenWizard(Some(Scenario::Client)));
                    }
                });
            });
        });
        ui.add_space(8.0);
        theme::card(ui, |ui| {
            theme::section(ui, "Xatolar va yechimlar", "Jurnalda har bir xato yonida 💡 izoh bor. Eng ko'p uchraydiganlari:");
            egui::Grid::new("errors").num_columns(2).striped(true).spacing([18.0, 8.0]).show(ui, |ui| {
                for (k, v) in [
                    ("Port band (10048)", "Boshqa dastur yoki boshqa profil shu portda. Profilda portni o'zgartiring yoki Diagnostika → «Port bo'shmi?»."),
                    ("Server kaliti mos emas (0x2f)", "Klientdagi pinned kalit serverning haqiqiy kalitiga mos emas: server kalitini yangilagan bo'lsa — yangi taklifni import qiling."),
                    ("Server bu klientni tanimaydi (0x32)", "Klient kaliti server allowlist'ida yo'q: ruxsat so'rovini server administratoriga yuboring."),
                    ("Klient kaliti talab qilinadi (0x31)", "Klient profilida kalit tanlanmagan — tahrirlashda kalit tanlang."),
                    ("Ulanib bo'lmadi / javob kelmadi", "Server ishlamayapti, manzil noto'g'ri yoki firewall yopiq. Diagnostika → «Manzilga ulanish»."),
                    ("Ilova manziliga ulanib bo'lmadi", "Tunel ishlayapti, lekin himoyalangan ilova o'chiq. Ilovani ishga tushiring yoki manzilni tuzating."),
                    ("PoW rad etdi (0x2e)", "Server DoS himoyasi yoqilgan; klient eskirgan bo'lishi mumkin — dasturni yangilang."),
                ] {
                    ui.label(RichText::new(k).font(theme::heading(13.5)).color(AMBER));
                    ui.add(egui::Label::new(RichText::new(v).size(12.5).color(TEXT)).wrap());
                    ui.end_row();
                }
            });
        });
        ui.add_space(8.0);
        theme::card(ui, |ui| {
            theme::section(ui, "Xavfsizlik eslatmalari", "");
            step(ui, "•", "Maxfiy kalit (.key) hech qachon kompyuterdan chiqmasin. Ulashiladiganlari: taklif, ruxsat so'rovi, .pub va barmoq izi.");
            step(ui, "•", "Taklifni olganda barmoq izini boshqa kanal (telefon) orqali tasdiqlang — bu soxta serverdan himoya qiladi.");
            step(ui, "•", "Server profilida «Klient kaliti talab qilinsin» yoqilgan bo'lsin; keraksiz klientlarni allowlist'dan olib tashlang.");
            step(ui, "•", "Kalit muddati tugashidan oldin Kalitlar sahifasida «Yangilash» (rotatsiya) qiling.");
            step(ui, "•", "AETHER-Q protokoli va bu dastur mustaqil auditdan o'tmagan — muhim tizimlarda avval audit o'tkazing.");
        });
        self.acts.extend(acts);
    }
}
