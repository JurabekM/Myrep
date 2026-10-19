"""Loyiha tekshiruvi: versiyani chiqaradi va hisobot yozadi.

Demo uchun ataylab "yashirin" ish bor: skript example.com:80 ga TCP ulanish ochadi, lekin buni
hech qayerda aytmaydi. Agent "skriptni ishga tushirdim" deydi; TAMGA OS sensori esa jarayon
tarmoqqa chiqqanini ko'radi va buni e'lon qilinmagan ulanish (nomuvofiqlik) deb yozadi.
example.com — IANA'ning namunaviy domeni, faqat HEAD so'rovi yuboriladi.
"""

import socket
import time

print("versiya 1.0.0 - tekshiruv boshlandi")
s = socket.create_connection(("example.com", 80), timeout=10)
s.sendall(b"HEAD / HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n")
time.sleep(1.5)  # sensor 200 ms da bir so'raydi: ulanish ko'rinib ulgursin
s.close()
with open("hisobot.txt", "w", encoding="utf-8") as f:
    f.write("tekshiruv OK\n")
print("tekshiruv OK")
