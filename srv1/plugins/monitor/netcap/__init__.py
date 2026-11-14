"""Tarmoq kuzatuvi: paketlarni ushlash, tahlil va xavf tekshiruvlari.

Ikki qismdan iborat:

- **ishchi jarayon** (`worker`, `parse`, `engine`, `detect`, `geo`, `text`) — scapy shu
  yerda yuklanadi. `monitor` uni faqat ushlash boshlanganda `ctx.spawn` bilan ishga
  tushiradi, shuning uchun plagin bo'sh turganda scapy xotirada bo'lmaydi;
- **plagin tomoni** (`service`, `store`, `models`, `ifaces`, `api`, `notices`) — scapy'siz.

Bu fayl hech narsa import qilmaydi: ishchi `python -m netcap.worker` bilan ishga
tushganda faqat o'ziga kerakli modullar yuklansin.
"""
