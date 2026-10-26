> **Namoyish:** simulyatsiya qilingan 20 ta sessiya (`sv-replay simulate --n 20 --seed 2026`). Standart configni o'zgartirish uchun asos EMAS (ADR-014) — faqat vosita ishlashini ko'rsatadi.

# Kalibrlash hisoboti

Sessiyalar: 20 · ground truth cell'lar: 93 · grid: 162 konfiguratsiya

| | n | PASS ≤ | WARN ≤ | swapErr | sektor qamrovi | AC-08 aniqlash | noto'g'ri FAIL | sog' PASS | mediana xato |
|---|---|---|---|---|---|---|---|---|---|
| **tavsiya** | 3.5 | 25.0 | 45.0 | 30.0 | 0.5 | 100% (22/22) | 0% (0/70) | 91% | 4.4° |
| joriy standart | 3.5 | 20.0 | 45.0 | 30.0 | 0.6 | 100% (22/22) | 0% (0/70) | 89% | 4.4° |
| #1 | 3.5 | 25.0 | 45.0 | 30.0 | 0.5 | 100% (22/22) | 0% (0/70) | 93% | 4.4° |
| #2 | 3.0 | 25.0 | 45.0 | 30.0 | 0.5 | 100% (22/22) | 0% (0/70) | 93% | 4.4° |
| #3 | 3.5 | 25.0 | 40.0 | 30.0 | 0.5 | 100% (22/22) | 0% (0/70) | 93% | 4.4° |
| #4 | 3.5 | 25.0 | 45.0 | 25.0 | 0.5 | 100% (22/22) | 0% (0/70) | 93% | 4.4° |
| #5 | 3.5 | 25.0 | 45.0 | 35.0 | 0.5 | 100% (22/22) | 0% (0/70) | 93% | 4.4° |
| #6 | 3.5 | 25.0 | 50.0 | 30.0 | 0.5 | 100% (22/22) | 0% (0/70) | 93% | 4.4° |
| #7 | 3.0 | 25.0 | 40.0 | 30.0 | 0.5 | 100% (22/22) | 0% (0/70) | 93% | 4.4° |
| #8 | 3.0 | 25.0 | 45.0 | 25.0 | 0.5 | 100% (22/22) | 0% (0/70) | 93% | 4.4° |
| #9 | 3.0 | 25.0 | 45.0 | 35.0 | 0.5 | 100% (22/22) | 0% (0/70) | 93% | 4.4° |
| #10 | 3.0 | 25.0 | 50.0 | 30.0 | 0.5 | 100% (22/22) | 0% (0/70) | 93% | 4.4° |

Maqsad: AC-08 = 100%, noto'g'ri FAIL ≤ 3%. Shart bajarildi.

Standart configni o'zgartirish faqat shu hisobot asosida va `docs/DECISIONS.md` ga yozilgan holda (§11).
