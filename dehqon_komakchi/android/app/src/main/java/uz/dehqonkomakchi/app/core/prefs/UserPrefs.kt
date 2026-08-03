package uz.dehqonkomakchi.app.core.prefs

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore by preferencesDataStore(name = "dehqon_prefs")

data class UserSettings(
    val onboardingComplete: Boolean = false,
    val languageTag: String = "uz",
    val region: String = "",
    val district: String = "",
    val plantingDateEpochDay: Long? = null,
    val notificationsEnabled: Boolean = false,
    val darkModeOverride: String = "system", // "light" | "dark" | "system"
    val textScale: Float = 1.0f,
    val lastWateredEpochDay: Long? = null,
    val authToken: String? = null,
    val phoneNumber: String? = null,
)

/**
 * Single source of truth for lightweight user preferences and onboarding state.
 * Backed by Jetpack DataStore so it survives process death and is easy to unit test
 * via an in-memory DataStore in tests.
 */
@Singleton
class UserPrefs @Inject constructor(private val context: Context) {

    private object Keys {
        val ONBOARDING_COMPLETE = booleanPreferencesKey("onboarding_complete")
        val LANGUAGE = stringPreferencesKey("language")
        val REGION = stringPreferencesKey("region")
        val DISTRICT = stringPreferencesKey("district")
        val PLANTING_DATE = longPreferencesKey("planting_date_epoch_day")
        val NOTIFICATIONS = booleanPreferencesKey("notifications_enabled")
        val DARK_MODE = stringPreferencesKey("dark_mode_override")
        val TEXT_SCALE = stringPreferencesKey("text_scale")
        val LAST_WATERED = longPreferencesKey("last_watered_epoch_day")
        val AUTH_TOKEN = stringPreferencesKey("auth_token")
        val PHONE = stringPreferencesKey("phone_number")
    }

    val settings: Flow<UserSettings> = context.dataStore.data.map { prefs ->
        UserSettings(
            onboardingComplete = prefs[Keys.ONBOARDING_COMPLETE] ?: false,
            languageTag = prefs[Keys.LANGUAGE] ?: "uz",
            region = prefs[Keys.REGION] ?: "",
            district = prefs[Keys.DISTRICT] ?: "",
            plantingDateEpochDay = prefs[Keys.PLANTING_DATE],
            notificationsEnabled = prefs[Keys.NOTIFICATIONS] ?: false,
            darkModeOverride = prefs[Keys.DARK_MODE] ?: "system",
            textScale = prefs[Keys.TEXT_SCALE]?.toFloatOrNull() ?: 1.0f,
            lastWateredEpochDay = prefs[Keys.LAST_WATERED],
            authToken = prefs[Keys.AUTH_TOKEN],
            phoneNumber = prefs[Keys.PHONE],
        )
    }

    suspend fun setOnboardingComplete(complete: Boolean) {
        context.dataStore.edit { it[Keys.ONBOARDING_COMPLETE] = complete }
    }

    suspend fun setRegion(region: String, district: String) {
        context.dataStore.edit {
            it[Keys.REGION] = region
            it[Keys.DISTRICT] = district
        }
    }

    suspend fun setPlantingDate(epochDay: Long) {
        context.dataStore.edit { it[Keys.PLANTING_DATE] = epochDay }
    }

    suspend fun setNotificationsEnabled(enabled: Boolean) {
        context.dataStore.edit { it[Keys.NOTIFICATIONS] = enabled }
    }

    suspend fun setDarkModeOverride(mode: String) {
        context.dataStore.edit { it[Keys.DARK_MODE] = mode }
    }

    suspend fun setTextScale(scale: Float) {
        context.dataStore.edit { it[Keys.TEXT_SCALE] = scale.toString() }
    }

    suspend fun setLastWatered(epochDay: Long) {
        context.dataStore.edit { it[Keys.LAST_WATERED] = epochDay }
    }

    suspend fun setAuth(token: String?, phone: String?) {
        context.dataStore.edit {
            if (token != null) it[Keys.AUTH_TOKEN] = token else it.remove(Keys.AUTH_TOKEN)
            if (phone != null) it[Keys.PHONE] = phone else it.remove(Keys.PHONE)
        }
    }

    suspend fun clearAll() {
        context.dataStore.edit { it.clear() }
    }
}
