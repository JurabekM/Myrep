# Pico ichki dasturini emulyatorda sinash

`pico-hsm-run.ts` — [rp2040js](https://github.com/wokwi/rp2040js) (MIT) uchun ishga
tushiruvchi. U Pico uchun yig'ilgan **haqiqiy `.uf2`** ni RP2040 emulyatorida ishga tushiradi:

- stdin/stdout ↔ USB CDC (ikkilik oqim);
- KUTMOQDA ramkasi ko'rinsa, GP14 tugmasi bosiladi. `EMU_TUGMA` navbati: `ha` — 0,15 s bosish,
  `rad` — 2,5 s bosib turish, `yoq` — bosmaslik;
- `EMU_FLASH` — flash'ning oxirgi 4 KB sektori fayli (quvvat uzilishini sinash uchun);
- emulyatsiya vaqti bo'yicha har javob stderr'ga yoziladi (taxminiy 125 MHz).

⚠ rp2040js flash'ga yozishni emulyatsiya qilmaydi. Shuning uchun ichki dasturning
`flash_ish` funksiyasi (manzili — `EMU_FLASH_ISH`, `arm-none-eabi-nm` dan olinadi) ushlanadi
va sektor yozuvi JS tomonida bajariladi. `flash_safe_execute` va ROM flash funksiyalari faqat
haqiqiy Pico'da sinaladi.

```
git clone https://github.com/wokwi/rp2040js && cd rp2040js
git checkout a304c7486f329dae64be5f65baf28795d62ceb95 && npm ci --ignore-scripts
cp <repo>/zarbxona_v3/tools/pico_emulyator/pico-hsm-run.ts demo/
cd <repo>/zarbxona_v3
AQ_PICO_EMU=<rp2040js> AQ_PICO_UF2=<build>/zarbxona_pico_hsm.uf2 \
AQ_PICO_FLASH_ISH=$(arm-none-eabi-nm <build>/zarbxona_pico_hsm.elf | awk '$3=="flash_ish"{print $1}') \
python -m pytest -s tests/test_pico_emulyator.py
```
