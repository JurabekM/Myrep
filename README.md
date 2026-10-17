# TAMGA — AI agentlar uchun "qora quti"

TAMGA AI agentning har bir harakatini **bajarilishidan oldin** siyosat bo'yicha tekshiradi va
**keyin** xesh-zanjirli, post-kvant imzoli, o'zgartirib bo'lmaydigan jurnalga yozadi.
Jurnalni uchinchi tomon mustaqil verifikator bilan tekshira oladi.

- Reja va arxitektura: [docs/PLAN.md](docs/PLAN.md)
- Ochiq format: `spec/` (AAR-0.1, F1 bosqichida)

## Holat

**F0 — poydevor** tayyor: Rust workspace (9 crate skeleti), Tauri 2 + React "TAMGA Studio" qobig'i,
Claude Code dark theme tokenlari ([studio/src/theme/tokens.css](studio/src/theme/tokens.css)).

![TAMGA Studio — Jonli ekran (F0, namuna ma'lumot)](docs/screenshots/f0-studio-live.png)

## Ishga tushirish (Windows)

Talablar: Rust 1.90+, Node 24, pnpm 12.

```bash
cd studio && pnpm install && pnpm tauri dev
```

Tekshiruvlar:

```bash
cargo fmt --all --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace
```

Ikonkani qayta chizish: `py scripts/make_icon.py` (Pillow kerak).

## Litsenziya

Kod — Apache-2.0, spec — CC-BY-4.0 (taklif, [docs/PLAN.md](docs/PLAN.md) §9).
