# BouncyCastle: reflection orqali provayder qidiradi.
-keep class org.bouncycastle.** { *; }
-dontwarn org.bouncycastle.**

# HiveMQ MQTT klienti Netty ustida ishlaydi.
-keep class com.hivemq.client.** { *; }
-dontwarn com.hivemq.client.**
-keep class io.netty.** { *; }
-dontwarn io.netty.**
-dontwarn org.slf4j.**
-dontwarn reactor.**
-dontwarn org.reactivestreams.**

# RxJava va JCTools — HiveMQ klientining ichki navbatlari.
#
# Bu navbatlar `Unsafe` bilan maydon ofsetini maydon NOMI bo'yicha
# qidiradi. R8 nomni qisqartirsa ishga tushishda
# `NoSuchFieldException: consumerIndex` chiqadi va MQTT klienti
# UMUMAN ulanmaydi.
#
# Bu xato faqat reliz build'ida bo'ladi: debug'da minifikatsiya yo'q.
# Aynan shuning uchun reliz APK'si alohida sinaladi — debug'ning
# ishlashi hech narsani isbotlamaydi.
-keep class io.reactivex.** { *; }
-dontwarn io.reactivex.**
-keep class org.jctools.** { *; }
-dontwarn org.jctools.**
-keepclassmembers class ** {
    long producerIndex;
    long consumerIndex;
    long producerNode;
    long consumerNode;
}

# Room generatsiya qilgan sinflar.
-keep class * extends androidx.room.RoomDatabase { <init>(); }
-keep @androidx.room.Entity class *

# Kotlinx serialization.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
