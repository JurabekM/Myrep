package uz.sectorverify.ui.util

import android.annotation.SuppressLint
import android.content.Context
import android.content.res.Configuration
import java.util.Locale

/**
 * Ilova tili (uz/ru/en). DataStore asinxron, shuning uchun tanlangan teg SharedPreferences'ga ham yoziladi,
 * uni MainActivity attachBaseContext'da sinxron o'qiydi.
 */
class LocaleStore(private val context: Context) {
    fun get(): String = prefs(context).getString(KEY, DEFAULT) ?: DEFAULT

    fun set(tag: String) {
        prefs(context).edit().putString(KEY, tag).apply()
    }

    companion object {
        const val DEFAULT = "uz"
        private const val FILE = "locale"
        private const val KEY = "app_language"
        val SUPPORTED = listOf("uz", "ru", "en")

        private fun prefs(c: Context) = c.getSharedPreferences(FILE, Context.MODE_PRIVATE)

        /** [base] ni o'raydi, shunda resurslar saqlangan tilda olinadi. */
        @SuppressLint("AppBundleLocaleChanges") // :app bundle til split'larini o'chiradi (barcha tillar birga yetkaziladi).
        fun wrap(base: Context): Context {
            val tag = prefs(base).getString(KEY, DEFAULT) ?: DEFAULT
            val config = Configuration(base.resources.configuration).apply { setLocale(Locale.forLanguageTag(tag)) }
            return base.createConfigurationContext(config)
        }
    }
}
