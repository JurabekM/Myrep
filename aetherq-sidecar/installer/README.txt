AETHER-Q Sidecar Studio
=======================

Post-kvant AETHER-Q tunellarini sozlash va boshqarish dasturi. Ilova kodini o'zgartirmasdan uning tarmoq
trafigini ML-KEM-768 + X25519 kalit almashinuvi va ML-DSA-65 imzolari bilan himoyalangan tunel orqali
o'tkazadi.

Boshlash
--------
1. Start menyusidan "AETHER-Q Sidecar Studio" ni oching.
2. "Tez sozlash ustasi" ni bosing va stsenariyni tanlang:
   - Bitta kompyuterda sinash — hammasi avtomatik, natijani brauzerda ko'rasiz.
   - Server — ilovangizni himoyalaydi; taklif faylini (.aqinvite) klientga yuboring.
   - Klient — taklif faylini import qiling; ruxsat so'rovini (.aqrequest) serverga qaytaring.

Fayllar
-------
aq-studio.exe   — grafik dastur (shu)
aq-sidecar.exe  — buyruq qatori sidecar'i (GUI'siz, server xizmati sifatida)
aqctl.exe       — standart PQ-TLS rejimi va boshqaruv (Studio standart rejimda uni ishga tushiradi)
aether_new.exe  — namunaviy ilova (REST API), sinov uchun: aether_new.exe -listen 127.0.0.1:8080

Ma'lumotlar
-----------
Profillar, kalitlar va jurnal: %APPDATA%\AETHER-Q\Studio
Maxfiy kalitlar (.key) shu kompyuterdan chiqmasligi kerak. Dasturni o'chirganda bu papka saqlanib qoladi.

Eslatma
-------
AETHER-Q protokoli va bu dastur mustaqil xavfsizlik auditidan o'tmagan. Muhim tizimlarda ishlatishdan oldin
audit o'tkazing.
