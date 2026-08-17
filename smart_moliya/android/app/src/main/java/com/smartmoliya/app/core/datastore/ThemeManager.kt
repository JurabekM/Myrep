package com.smartmoliya.app.core.datastore

import android.content.Context
import com.smartmoliya.app.ui.theme.AppThemeId
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

/** Foydalanuvchi tanlagan temani saqlaydi va reaktiv uzatadi. */
@Singleton
class ThemeManager @Inject constructor(@ApplicationContext context: Context) {

    private val prefs = context.getSharedPreferences("smart_moliya_theme", Context.MODE_PRIVATE)

    private val _theme = MutableStateFlow(load())
    val theme: StateFlow<AppThemeId> = _theme.asStateFlow()

    fun setTheme(id: AppThemeId) {
        prefs.edit().putString(KEY_THEME, id.name).apply()
        _theme.value = id
    }

    private fun load(): AppThemeId =
        runCatching { AppThemeId.valueOf(prefs.getString(KEY_THEME, "") ?: "") }
            .getOrDefault(AppThemeId.DARK_MODERN)

    companion object {
        private const val KEY_THEME = "selected_theme"
    }
}
