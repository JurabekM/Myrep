# BouncyCastle: faqat ishlatilgan lightweight sinflar qoladi, qolganini R8 olib tashlaydi.
-dontwarn org.bouncycastle.**
# apksig ixtiyoriy JCA va javax sinflariga havola qiladi.
-dontwarn javax.naming.**
-dontwarn com.android.apksig.**
-keep class com.android.apksig.** { *; }
