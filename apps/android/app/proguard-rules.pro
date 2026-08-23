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

# Room generatsiya qilgan sinflar.
-keep class * extends androidx.room.RoomDatabase { <init>(); }
-keep @androidx.room.Entity class *

# Kotlinx serialization.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
