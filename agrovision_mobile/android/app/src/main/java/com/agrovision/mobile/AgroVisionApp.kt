package com.agrovision.mobile

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

/**
 * Ilova kirish nuqtasi (Hilt uchun majburiy). Baza yaratish/urug'lash
 * MainActivity'dagi yuklanish (splash) holatida amalga oshiriladi — shu bilan
 * Login ekrani hech qachon bo'sh bazaga qarshi ishlamaydi (irqiy holat yo'q).
 * HECH QANDAY tarmoq chaqiruvi yo'q — ilova to'liq avtonom.
 */
@HiltAndroidApp
class AgroVisionApp : Application()
