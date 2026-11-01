# kotlinx.serialization: @Serializable klasslar va ularning serializer'lari saqlanadi.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keepclassmembers class uz.qarzsiz.** {
    *** Companion;
}
-keepclasseswithmembers class uz.qarzsiz.** {
    kotlinx.serialization.KSerializer serializer(...);
}
-keep,includedescriptorclasses class uz.qarzsiz.**$$serializer { *; }
