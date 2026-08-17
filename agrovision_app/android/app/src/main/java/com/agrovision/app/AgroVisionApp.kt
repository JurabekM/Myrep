package com.agrovision.app

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

/**
 * Ilova kirish nuqtasi. Baza yaratish, ma'lumotnoma urug'lash va (tanlansa)
 * namuna ma'lumotlar generatsiyasi MainActivity'dagi bootstrap oqimida,
 * yuklanish ekrani ostida bajariladi.
 */
@HiltAndroidApp
class AgroVisionApp : Application()
