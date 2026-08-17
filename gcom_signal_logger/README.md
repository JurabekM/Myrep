# GCOM Signal Logger

Router (LuCI) ning `admin/network/gcom` sahifasidan 4G/5G modem ko'rsatkichlarini
(RSSI, RSRP, RSRQ, SINR, IMEI, IMSI, ICCID, band va h.k.) davriy ravishda o'qib,
`gcom_signal_log.csv` (yoki JSON-Lines) fayliga vaqt tamg'asi bilan yozadi.

## O'rnatish

```
cd gcom_signal_logger
pip install -r requirements.txt
```

## Sozlash

`config.ini` faylida router manzili, login/parol, interfeys va interval sozlangan
(default: `http://192.168.8.144`, `admin` / `admin123`, `iface=4g`, har 60 sekundda).
Kerak bo'lsa `config.ini` ni tahrirlang yoki CLI argumentlaridan foydalaning.

## Ishga tushirish

Bir marta o'qib ko'rish:
```
python logger.py --once
```

Doimiy kuzatish (Ctrl+C bilan to'xtatiladi):
```
python logger.py
```

Interval va formatni CLI orqali o'zgartirish:
```
python logger.py --interval 30 --format jsonl --logfile gcom_signal_log.jsonl
```

## Carrier aggregation (PCC/SCC)

Diapazon almashganda modem 1 yoki bir necha SCC (Secondary Component Carrier)
bilan ishlashi mumkin — sahifada "SCC" qatori shuncha marta takrorlanadi. Skript
buni hisobga oladi: `pcc_1`, `pcc_2` va `scc_1`..`scc_4` ustunlariga taqsimlaydi,
`scc_count` esa qancha SCC faol ekanini ko'rsatadi. Agar 4 tadan ortiq SCC chiqsa
(kamdan-kam holat), ortig'i `scc_4` ustuniga `"; "` bilan qo'shib yoziladi —
hech qanday ma'lumot yo'qolmaydi.

## Eslatma

- `config.ini` faylida parol ochiq matnda saqlanadi — faylni boshqalar bilan
  baham ko'rmang.
- Skript sessiya eskirsa (login talab qilinsa) avtomatik qayta login qiladi.
- LuCI sahifa razmetkasi router proshivka versiyasiga qarab farq qilishi mumkin;
  agar ba'zi maydonlar bo'sh chiqsa, `logger.py` dagi `LABEL_MAP` ichidagi
  yorliqlarni haqiqiy sahifadagi matnga moslab tuzating.
- CSV ustunlari o'zgarganda (masalan shu yangilanishdagi kabi `pcc`/`scc` dan
  `pcc_1`/`scc_1..4`ga) eski log faylini davom ettirish ustunlarni chalkashtirib
  yuborishi mumkin — bunday holatlarda eski faylni arxivlab, yangi bosh ustun
  bilan yangi faylni boshlang.
