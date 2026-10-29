# M-Pay hamyon: R8 qoidalari.
# org.json va BouncyCastle (PQ Link: ML-KEM, ML-DSA) refleksiya bilan provayder yuklaydi.
-keep class org.bouncycastle.** { *; }
-dontwarn org.bouncycastle.**
-dontwarn javax.naming.**
# WorkManager ishchisi nomi bo'yicha yaratiladi.
-keep class uz.mpay.wallet.app.SyncWorker { <init>(...); }
