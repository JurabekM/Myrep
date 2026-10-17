//! Vektor ikonkalar (painter bilan) — shrift glifiga bog'liq emas, har o'lchamda tiniq.

use egui::{pos2, vec2, Color32, Painter, Pos2, Rect, Stroke};

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Icon {
    Dashboard,
    Tunnel,
    Key,
    Log,
    Pulse,
    Settings,
    Help,
}

/// Ikonkani `rect` ichiga chizadi.
pub fn paint(p: &Painter, rect: Rect, icon: Icon, color: Color32) {
    let c = rect.center();
    let s = rect.width().min(rect.height()) / 2.0;
    let st = Stroke::new((s * 0.16).max(1.4), color);
    match icon {
        Icon::Dashboard => {
            let g = s * 0.12;
            for (dx, dy, h) in [(-1.0, -1.0, 0.9), (1.0, -1.0, 0.55), (-1.0, 1.0, 0.55), (1.0, 1.0, 0.9)] {
                let w = s * 0.78;
                let hh = s * 0.78 * h;
                let x0 = if dx < 0.0 { c.x - g - w } else { c.x + g };
                let y0 = if dy < 0.0 { c.y - g - hh } else { c.y + g };
                p.rect_stroke(
                    Rect::from_min_size(pos2(x0, y0), vec2(w, hh)),
                    2.0,
                    st,
                    egui::StrokeKind::Middle,
                );
            }
        }
        Icon::Tunnel => {
            let a = pos2(c.x - s * 0.72, c.y);
            let b = pos2(c.x + s * 0.72, c.y);
            p.line_segment([a, b], st);
            p.circle_stroke(a, s * 0.26, st);
            p.circle_filled(b, s * 0.26, color);
            // qulf belgisi markazda
            let lock = Rect::from_center_size(pos2(c.x, c.y + s * 0.05), vec2(s * 0.5, s * 0.4));
            p.rect_filled(lock, 2.0, color);
            p.circle_stroke(pos2(c.x, lock.top()), s * 0.17, Stroke::new(st.width * 0.8, color));
        }
        Icon::Key => {
            let head = pos2(c.x - s * 0.38, c.y - s * 0.12);
            p.circle_stroke(head, s * 0.36, st);
            let a = pos2(head.x + s * 0.26, head.y + s * 0.26);
            let b = pos2(c.x + s * 0.78, c.y + s * 0.78);
            p.line_segment([a, b], st);
            let mid = a.lerp(b, 0.62);
            p.line_segment([mid, pos2(mid.x + s * 0.22, mid.y - s * 0.22)], st);
            let end = a.lerp(b, 0.86);
            p.line_segment([end, pos2(end.x + s * 0.18, end.y - s * 0.18)], st);
        }
        Icon::Log => {
            for (i, w) in [0.9, 0.7, 0.9, 0.5].iter().enumerate() {
                let y = c.y - s * 0.6 + i as f32 * s * 0.4;
                p.line_segment([pos2(c.x - s * 0.8, y), pos2(c.x - s * 0.8 + s * 1.6 * w, y)], st);
            }
        }
        Icon::Pulse => {
            let pts: Vec<Pos2> = [(-0.9, 0.0), (-0.4, 0.0), (-0.2, -0.6), (0.1, 0.6), (0.35, -0.2), (0.5, 0.0), (0.9, 0.0)]
                .iter()
                .map(|(x, y)| pos2(c.x + s * x, c.y + s * y))
                .collect();
            p.add(egui::Shape::line(pts, st));
        }
        Icon::Settings => {
            for (i, k) in [0.3, -0.35, 0.1].iter().enumerate() {
                let y = c.y - s * 0.55 + i as f32 * s * 0.55;
                p.line_segment([pos2(c.x - s * 0.8, y), pos2(c.x + s * 0.8, y)], st);
                p.circle_filled(pos2(c.x + s * k * 1.6, y), s * 0.18, color);
            }
        }
        Icon::Help => {
            p.circle_stroke(c, s * 0.8, st);
            let font = egui::FontId::proportional(s * 1.15);
            p.text(c + vec2(0.0, s * 0.02), egui::Align2::CENTER_CENTER, "?", font, color);
        }
    }
}

/// Dastur logotipi: ikki tugun, shifrlangan tunel va qulf (exe ikonkasi bilan bir xil g'oya).
pub fn logo(p: &Painter, rect: Rect) {
    let c = rect.center();
    let s = rect.width() / 2.0;
    p.rect_filled(rect, s * 0.42, crate::theme::CARD_HI);
    let teal = crate::theme::ACCENT;
    let a = pos2(c.x - s * 0.55, c.y + s * 0.18);
    let b = pos2(c.x + s * 0.55, c.y + s * 0.18);
    p.line_segment([a, b], Stroke::new(s * 0.16, teal.gamma_multiply(0.85)));
    p.circle_filled(a, s * 0.2, teal);
    p.circle_filled(b, s * 0.2, teal);
    let body = Rect::from_center_size(pos2(c.x, c.y - s * 0.12), vec2(s * 0.5, s * 0.38));
    p.circle_stroke(pos2(c.x, body.top()), s * 0.17, Stroke::new(s * 0.09, crate::theme::TEXT));
    p.rect_filled(body, s * 0.07, crate::theme::TEXT);
    p.circle_filled(pos2(c.x, body.center().y), s * 0.055, crate::theme::CARD_HI);
}
