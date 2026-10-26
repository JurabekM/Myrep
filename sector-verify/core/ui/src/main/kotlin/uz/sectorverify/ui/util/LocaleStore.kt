package uz.sectorverify.ui.util

import android.content.Context
import android.content.res.Configuration
import java.util.Locale

/**
 * App language (uz/ru/en). DataStore is async, so the chosen tag is mirrored in SharedPreferences that
 * MainActivity reads synchronously in attachBaseContext.
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

        /** Wraps [base] so that resources resolve in the stored language. */
        fun wrap(base: Context): Context {
            val tag = prefs(base).getString(KEY, DEFAULT) ?: DEFAULT
            val config = Configuration(base.resources.configuration).apply { setLocale(Locale.forLanguageTag(tag)) }
            return base.createConfigurationContext(config)
        }
    }
}
