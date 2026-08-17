# AgroVision Mobile — R8/ProGuard qoidalari
-keep class com.agrovision.mobile.data.local.** { *; }
-keepattributes *Annotation*
-dontwarn org.bouncycastle.**
-dontwarn org.conscrypt.**
-dontwarn org.openjsse.**
