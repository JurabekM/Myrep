# Sector Verify — R8 qoidalari (§5). Room, Hilt, Compose va DataStore o'z consumer qoidalari bilan keladi.

# SQLCipher: JNI klass va metodlarni nomi bo'yicha qidiradi.
-keep class net.zetetic.database.** { *; }
-keep class net.zetetic.database.sqlcipher.** { *; }

# kotlinx.serialization: @Serializable klasslarimizning generatsiya qilingan serializer va companion'lari.
-keepattributes *Annotation*, InnerClasses, Signature, Exceptions
-dontnote kotlinx.serialization.**
-keepclassmembers class kotlinx.serialization.json.** { *** Companion; }
-keepclasseswithmembers class kotlinx.serialization.json.** { kotlinx.serialization.KSerializer serializer(...); }
-keep,includedescriptorclasses class uz.sectorverify.**$$serializer { *; }
-keepclassmembers class uz.sectorverify.** { *** Companion; }
-keepclasseswithmembers class uz.sectorverify.** { kotlinx.serialization.KSerializer serializer(...); }

# Enum nomlari saqlanadi (Room TEXT ustunlari, JSON).
-keepclassmembers enum uz.sectorverify.** { *; }

# Lokal crash log'dagi stack trace'lar mapping fayli tufayli o'qiladigan bo'lib qoladi.
-keepattributes SourceFile, LineNumberTable
-renamesourcefileattribute SourceFile
