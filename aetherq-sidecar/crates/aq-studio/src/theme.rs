//! Dark tema: AETHER-Q oilasining ranglari (teal urg'u, to'q navy fon), shriftlar va qayta ishlatiladigan
//! vidjetlar (kartochka, yorliq, KPI, tugmalar, grafik).

use std::sync::Arc;

use egui::{Color32, CornerRadius, FontFamily, FontId, Margin, RichText, Stroke, Ui};

pub const BG: Color32 = Color32::from_rgb(10, 22, 40);
pub const SIDEBAR: Color32 = Color32::from_rgb(8, 17, 32);
pub const CARD: Color32 = Color32::from_rgb(17, 35, 61);
pub const CARD_HI: Color32 = Color32::from_rgb(24, 47, 79);
pub const INPUT: Color32 = Color32::from_rgb(12, 27, 48);
pub const BORDER: Color32 = Color32::from_rgb(33, 60, 94);
pub const TEXT: Color32 = Color32::from_rgb(230, 238, 247);
pub const MUTED: Color32 = Color32::from_rgb(142, 163, 189);
pub const FAINT: Color32 = Color32::from_rgb(92, 114, 142);
pub const ACCENT: Color32 = Color32::from_rgb(79, 209, 197);
pub const ACCENT_DIM: Color32 = Color32::from_rgb(39, 120, 116);
pub const BLUE: Color32 = Color32::from_rgb(96, 165, 250);
pub const GREEN: Color32 = Color32::from_rgb(52, 211, 153);
pub const AMBER: Color32 = Color32::from_rgb(245, 181, 71);
pub const RED: Color32 = Color32::from_rgb(248, 113, 113);
pub const VIOLET: Color32 = Color32::from_rgb(167, 139, 250);

/// Yarim qalin sarlavha shrifti (Segoe UI Semibold, bo'lmasa oddiy).
pub fn semibold() -> FontFamily {
    FontFamily::Name("semibold".into())
}

pub fn heading(size: f32) -> FontId {
    FontId::new(size, semibold())
}

/// Windows shriftlari (Segoe UI, Segoe UI Semibold, Consolas) — bo'lmasa egui'ning o'z shriftlari qoladi.
pub fn install_fonts(ctx: &egui::Context) {
    ctx.set_fonts(font_definitions());
}

/// Shrift zanjirlari: Segoe UI birinchi, keyin egui'ning shriftlari (emoji va belgilar uchun zaxira).
pub fn font_definitions() -> egui::FontDefinitions {
    let mut fonts = egui::FontDefinitions::default();
    let dir = std::env::var("WINDIR").map(|w| std::path::PathBuf::from(w).join("Fonts")).ok();
    let load = |name: &str| dir.as_ref().and_then(|d| std::fs::read(d.join(name)).ok());
    let mut add_front = |key: &str, data: Option<Vec<u8>>, family: FontFamily| {
        if let Some(bytes) = data {
            fonts.font_data.insert(key.to_owned(), Arc::new(egui::FontData::from_owned(bytes)));
            fonts.families.entry(family).or_default().insert(0, key.to_owned());
        }
    };
    add_front("segoe", load("segoeui.ttf"), FontFamily::Proportional);
    add_front("consolas", load("consola.ttf"), FontFamily::Monospace);
    // Semibold oilasi: Segoe UI Semibold, keyin oddiy proportional zanjir (emoji va belgilar uchun).
    let mut semi: Vec<String> = Vec::new();
    if let Some(bytes) = load("seguisb.ttf") {
        fonts.font_data.insert("segoe-semibold".into(), Arc::new(egui::FontData::from_owned(bytes)));
        semi.push("segoe-semibold".into());
    }
    semi.extend(fonts.families.get(&FontFamily::Proportional).cloned().unwrap_or_default());
    fonts.families.insert(semibold(), semi);
    fonts
}

pub fn apply(ctx: &egui::Context) {
    ctx.set_theme(egui::ThemePreference::Dark);
    ctx.all_styles_mut(style_dark);
}

fn style_dark(style: &mut egui::Style) {
    let mut v = egui::Visuals::dark();
    v.panel_fill = BG;
    v.window_fill = CARD;
    v.extreme_bg_color = INPUT;
    v.faint_bg_color = CARD_HI;
    v.code_bg_color = INPUT;
    v.hyperlink_color = ACCENT;
    v.selection.bg_fill = ACCENT.gamma_multiply(0.35);
    v.selection.stroke = Stroke::new(1.0, ACCENT);
    v.window_corner_radius = CornerRadius::same(14);
    v.window_stroke = Stroke::new(1.0, BORDER);
    v.override_text_color = Some(TEXT);
    v.text_cursor.stroke = Stroke::new(2.0, ACCENT);
    let r = CornerRadius::same(8);
    for w in [
        &mut v.widgets.noninteractive,
        &mut v.widgets.inactive,
        &mut v.widgets.hovered,
        &mut v.widgets.active,
        &mut v.widgets.open,
    ] {
        w.corner_radius = r;
    }
    v.widgets.noninteractive.bg_fill = CARD;
    v.widgets.noninteractive.weak_bg_fill = CARD;
    v.widgets.noninteractive.bg_stroke = Stroke::new(1.0, BORDER);
    v.widgets.noninteractive.fg_stroke = Stroke::new(1.0, TEXT);
    // Faol bo'lmagan vidjet (checkbox katagi, slayder relsi) kartochka fonidan farq qilsin.
    v.widgets.inactive.bg_fill = Color32::from_rgb(30, 58, 94);
    v.widgets.inactive.weak_bg_fill = CARD_HI;
    // Radio/checkbox doirasi va kiritish maydoni chegarasi kartochka fonida aniq ko'rinsin.
    v.widgets.inactive.bg_stroke = Stroke::new(1.0, Color32::from_rgb(72, 108, 150));
    v.widgets.inactive.fg_stroke = Stroke::new(1.0, TEXT);
    v.widgets.hovered.bg_fill = Color32::from_rgb(34, 66, 104);
    v.widgets.hovered.weak_bg_fill = Color32::from_rgb(30, 58, 94);
    v.widgets.hovered.bg_stroke = Stroke::new(1.0, ACCENT.gamma_multiply(0.8));
    v.widgets.hovered.fg_stroke = Stroke::new(1.5, TEXT);
    v.widgets.active.bg_fill = ACCENT_DIM;
    v.widgets.active.weak_bg_fill = ACCENT_DIM;
    v.widgets.active.bg_stroke = Stroke::new(1.0, ACCENT);
    v.widgets.open.weak_bg_fill = CARD_HI;
    style.visuals = v;
    style.spacing.item_spacing = egui::vec2(10.0, 8.0);
    style.spacing.button_padding = egui::vec2(14.0, 7.0);
    style.spacing.interact_size.y = 30.0;
    style.spacing.combo_width = 220.0;
    // Aylantirish chizig'i kontent ustiga chiqmasin (KPI plitkalarining o'ng cheti yopilmasin).
    style.spacing.scroll = egui::style::ScrollStyle::solid();
    style.spacing.text_edit_width = 260.0;
    use egui::TextStyle;
    style.text_styles = [
        (TextStyle::Heading, FontId::new(22.0, semibold())),
        (TextStyle::Body, FontId::new(14.5, FontFamily::Proportional)),
        (TextStyle::Button, FontId::new(14.0, FontFamily::Proportional)),
        (TextStyle::Small, FontId::new(12.0, FontFamily::Proportional)),
        (TextStyle::Monospace, FontId::new(13.0, FontFamily::Monospace)),
    ]
    .into();
}

/// Kartochka: yumaloq burchakli, ichki bo'shliqli panel (to'liq kenglik).
pub fn card<R>(ui: &mut Ui, add: impl FnOnce(&mut Ui) -> R) -> R {
    card_with(ui, CARD, BORDER, add)
}

pub fn card_with<R>(ui: &mut Ui, fill: Color32, border: Color32, add: impl FnOnce(&mut Ui) -> R) -> R {
    egui::Frame::new()
        .fill(fill)
        .stroke(Stroke::new(1.0, border))
        .corner_radius(CornerRadius::same(12))
        .inner_margin(Margin::same(16))
        .show(ui, |ui| {
            ui.set_width(ui.available_width());
            add(ui)
        })
        .inner
}

/// Bo'lim sarlavhasi va izohi.
pub fn section(ui: &mut Ui, title: &str, subtitle: &str) {
    ui.label(RichText::new(title).font(heading(17.0)).color(TEXT));
    if !subtitle.is_empty() {
        ui.label(RichText::new(subtitle).size(12.5).color(MUTED));
    }
    ui.add_space(6.0);
}

fn filled_button(text: &str, fill: Color32, fg: Color32, enabled: bool) -> egui::Button<'static> {
    egui::Button::new(RichText::new(text.to_owned()).font(heading(14.0)).color(if enabled {
        fg
    } else {
        fg.gamma_multiply(0.5)
    }))
    .fill(if enabled { fill } else { fill.gamma_multiply(0.35) })
    .corner_radius(CornerRadius::same(8))
    .min_size(egui::vec2(0.0, 34.0))
}

/// Asosiy (teal) tugma.
pub fn primary(ui: &mut Ui, text: &str, enabled: bool) -> egui::Response {
    ui.add_enabled(enabled, filled_button(text, ACCENT, Color32::from_rgb(4, 30, 36), enabled))
}

/// Ikkinchi darajali tugma (konturli).
pub fn secondary(ui: &mut Ui, text: &str, enabled: bool) -> egui::Response {
    ui.add_enabled(
        enabled,
        egui::Button::new(RichText::new(text).color(if enabled { TEXT } else { FAINT }))
            .fill(CARD_HI)
            .stroke(Stroke::new(1.0, BORDER))
            .corner_radius(CornerRadius::same(8))
            .min_size(egui::vec2(0.0, 34.0)),
    )
}

/// Xavfli amal tugmasi (o'chirish, to'xtatish).
pub fn danger(ui: &mut Ui, text: &str, enabled: bool) -> egui::Response {
    ui.add_enabled(enabled, filled_button(text, Color32::from_rgb(127, 29, 29), Color32::from_rgb(254, 226, 226), enabled))
}

/// Kichik (ixcham) konturli tugma — jadval qatorlari uchun.
pub fn small(ui: &mut Ui, text: &str, enabled: bool) -> egui::Response {
    ui.add_enabled(
        enabled,
        egui::Button::new(RichText::new(text).size(12.5).color(if enabled { TEXT } else { FAINT }))
            .fill(CARD_HI)
            .stroke(Stroke::new(1.0, BORDER))
            .corner_radius(CornerRadius::same(6))
            .min_size(egui::vec2(0.0, 26.0)),
    )
}

/// Holat yorlig'i (rangli nuqta + matn).
pub fn pill(ui: &mut Ui, text: &str, color: Color32) {
    egui::Frame::new()
        .fill(color.gamma_multiply(0.14))
        .stroke(Stroke::new(1.0, color.gamma_multiply(0.55)))
        .corner_radius(CornerRadius::same(20))
        .inner_margin(Margin::symmetric(10, 3))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.spacing_mut().item_spacing.x = 6.0;
                let (r, _) = ui.allocate_exact_size(egui::vec2(8.0, 8.0), egui::Sense::hover());
                ui.painter().circle_filled(r.center(), 4.0, color);
                ui.label(RichText::new(text).color(color).size(12.5));
            });
        });
}

/// Nuqtasiz yorliq (rol, rejim).
pub fn badge(ui: &mut Ui, text: &str, color: Color32) {
    egui::Frame::new()
        .fill(color.gamma_multiply(0.12))
        .corner_radius(CornerRadius::same(6))
        .inner_margin(Margin::symmetric(8, 2))
        .show(ui, |ui| {
            ui.label(RichText::new(text).color(color).size(12.0));
        });
}

/// `n` ta KPI plitkasi bir qatorga sig'adigan ichki kenglik.
pub fn kpi_width(ui: &Ui, n: usize) -> f32 {
    let gap = ui.spacing().item_spacing.x;
    let n = n as f32;
    ((ui.available_width() - gap * (n - 1.0)) / n - 30.0).max(110.0)
}

/// KPI plitkasi: izoh, katta qiymat va kichik tushuntirish.
pub fn kpi(ui: &mut Ui, width: f32, label: &str, value: &str, hint: &str, color: Color32) {
    egui::Frame::new()
        .fill(CARD)
        .stroke(Stroke::new(1.0, BORDER))
        .corner_radius(CornerRadius::same(12))
        .inner_margin(Margin::symmetric(14, 12))
        .show(ui, |ui| {
            ui.set_width(width);
            ui.vertical(|ui| {
                ui.spacing_mut().item_spacing.y = 3.0;
                ui.add(egui::Label::new(RichText::new(label).size(12.5).color(MUTED)).truncate());
                ui.add(egui::Label::new(RichText::new(value).font(heading(24.0)).color(color)).truncate());
                ui.add(egui::Label::new(RichText::new(hint).size(11.5).color(FAINT)).truncate());
            });
        });
}

/// Ma'lumot yo'q holati: belgi, sarlavha va izoh (markazda).
pub fn empty_state(ui: &mut Ui, title: &str, text: &str) {
    ui.vertical_centered(|ui| {
        ui.add_space(12.0);
        ui.label(RichText::new(title).font(heading(16.0)).color(TEXT));
        ui.add(egui::Label::new(RichText::new(text).color(MUTED).size(13.0)).wrap());
        ui.add_space(8.0);
    });
}

/// Ikki seriyali chiziqli grafik. O'q yorliqlari uchun chapda va pastda alohida joy ajratiladi.
pub fn line_chart(ui: &mut Ui, series: &[(&[f64], Color32, &str)], unit: &str, height: f32) {
    let width = ui.available_width();
    let (rect, _) = ui.allocate_exact_size(egui::vec2(width, height), egui::Sense::hover());
    let p = ui.painter_at(rect);
    p.rect_filled(rect, CornerRadius::same(10), INPUT);
    let max_y = series
        .iter()
        .flat_map(|(s, _, _)| s.iter().copied())
        .fold(0.0f64, f64::max)
        .max(1.0)
        * 1.15;
    let plot = egui::Rect::from_min_max(rect.min + egui::vec2(48.0, 14.0), rect.max - egui::vec2(12.0, 26.0));
    for i in 0..=4 {
        let y = plot.bottom() - plot.height() * i as f32 / 4.0;
        p.line_segment(
            [egui::pos2(plot.left(), y), egui::pos2(plot.right(), y)],
            Stroke::new(1.0, BORDER.gamma_multiply(0.55)),
        );
        p.text(
            egui::pos2(plot.left() - 8.0, y),
            egui::Align2::RIGHT_CENTER,
            fmt_num(max_y * i as f64 / 4.0),
            FontId::proportional(11.0),
            FAINT,
        );
    }
    // Pastki qator: legenda chapda, birlik o'ngda (chizma sohasidan tashqarida).
    let mut x = plot.left();
    for (_, color, name) in series {
        p.circle_filled(egui::pos2(x + 5.0, rect.bottom() - 12.0), 4.0, *color);
        let g = p.text(
            egui::pos2(x + 14.0, rect.bottom() - 12.0),
            egui::Align2::LEFT_CENTER,
            *name,
            FontId::proportional(11.5),
            MUTED,
        );
        x = g.right() + 16.0;
    }
    p.text(
        egui::pos2(plot.right(), rect.bottom() - 12.0),
        egui::Align2::RIGHT_CENTER,
        unit,
        FontId::proportional(11.0),
        FAINT,
    );
    let n = series.iter().map(|(s, _, _)| s.len()).max().unwrap_or(0);
    if n < 2 {
        p.text(plot.center(), egui::Align2::CENTER_CENTER, "Ma'lumot yig'ilmoqda…", FontId::proportional(13.0), MUTED);
        return;
    }
    for (s, color, _) in series {
        if s.len() < 2 {
            continue;
        }
        let step = plot.width() / (n - 1) as f32;
        let off = (n - s.len()) as f32 * step;
        let pts: Vec<egui::Pos2> = s
            .iter()
            .enumerate()
            .map(|(i, y)| {
                egui::pos2(plot.left() + off + i as f32 * step, plot.bottom() - (*y / max_y) as f32 * plot.height())
            })
            .collect();
        for w in pts.windows(2) {
            p.add(egui::Shape::convex_polygon(
                vec![w[0], w[1], egui::pos2(w[1].x, plot.bottom()), egui::pos2(w[0].x, plot.bottom())],
                color.gamma_multiply(0.10),
                Stroke::NONE,
            ));
        }
        p.add(egui::Shape::line(pts.clone(), Stroke::new(2.0, *color)));
        if let Some(last) = pts.last() {
            p.circle_filled(*last, 3.5, *color);
        }
    }
}

pub fn fmt_num(v: f64) -> String {
    if v >= 1_000_000.0 {
        format!("{:.1}M", v / 1_000_000.0)
    } else if v >= 10_000.0 {
        format!("{:.0}k", v / 1000.0)
    } else if v >= 100.0 {
        format!("{v:.0}")
    } else if v >= 10.0 {
        format!("{v:.1}")
    } else {
        format!("{v:.2}")
    }
}

/// Baytlar: B, KiB, MiB, GiB.
pub fn fmt_bytes(b: u64) -> String {
    let f = b as f64;
    if f >= 1024.0 * 1024.0 * 1024.0 {
        format!("{:.2} GiB", f / (1024.0 * 1024.0 * 1024.0))
    } else if f >= 1024.0 * 1024.0 {
        format!("{:.1} MiB", f / (1024.0 * 1024.0))
    } else if f >= 1024.0 {
        format!("{:.1} KiB", f / 1024.0)
    } else {
        format!("{b} B")
    }
}

/// Minglik ajratkich bilan (bo'shliq).
pub fn group(n: u64) -> String {
    let s = n.to_string();
    let mut out = String::new();
    for (i, c) in s.chars().enumerate() {
        if i > 0 && (s.len() - i) % 3 == 0 {
            out.push(' ');
        }
        out.push(c);
    }
    out
}

/// Davomiylik: "3 s", "4 daq 12 s", "2 soat 5 daq".
pub fn fmt_duration(secs: u64) -> String {
    if secs < 60 {
        format!("{secs} s")
    } else if secs < 3600 {
        format!("{} daq {} s", secs / 60, secs % 60)
    } else {
        format!("{} soat {} daq", secs / 3600, (secs % 3600) / 60)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn formatting_helpers() {
        assert_eq!(group(1234567), "1 234 567");
        assert_eq!(group(12), "12");
        assert_eq!(fmt_bytes(512), "512 B");
        assert_eq!(fmt_bytes(1536), "1.5 KiB");
        assert_eq!(fmt_bytes(5 * 1024 * 1024), "5.0 MiB");
        assert_eq!(fmt_duration(42), "42 s");
        assert_eq!(fmt_duration(125), "2 daq 5 s");
        assert_eq!(fmt_duration(7300), "2 soat 1 daq");
        assert_eq!(fmt_num(0.5), "0.50");
        assert_eq!(fmt_num(15000.0), "15k");
    }
}
