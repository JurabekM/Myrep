# Sector Verify — R8 rules (§5). Room, Hilt, Compose and DataStore ship their own consumer rules.

# SQLCipher: JNI looks classes and methods up by name.
-keep class net.zetetic.database.** { *; }
-keep class net.zetetic.database.sqlcipher.** { *; }

# kotlinx.serialization: generated serializers and companions of our @Serializable classes.
-keepattributes *Annotation*, InnerClasses, Signature, Exceptions
-dontnote kotlinx.serialization.**
-keepclassmembers class kotlinx.serialization.json.** { *** Companion; }
-keepclasseswithmembers class kotlinx.serialization.json.** { kotlinx.serialization.KSerializer serializer(...); }
-keep,includedescriptorclasses class uz.sectorverify.**$$serializer { *; }
-keepclassmembers class uz.sectorverify.** { *** Companion; }
-keepclasseswithmembers class uz.sectorverify.** { kotlinx.serialization.KSerializer serializer(...); }

# Enum names are persisted (Room TEXT columns, JSON).
-keepclassmembers enum uz.sectorverify.** { *; }

# Stack traces in the local crash log stay readable with the mapping file.
-keepattributes SourceFile, LineNumberTable
-renamesourcefileattribute SourceFile
