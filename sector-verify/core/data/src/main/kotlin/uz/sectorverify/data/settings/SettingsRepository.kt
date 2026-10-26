package uz.sectorverify.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import uz.sectorverify.format.SvJson
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.AnalysisPreset
import uz.sectorverify.model.DeviceCapabilities

enum class AppTheme { DARK, LIGHT, SUN }

data class Settings(
    val preset: AnalysisPreset = AnalysisPreset.SUBURBAN,
    /** Manual or imported (calibration) config; overrides the preset when set. */
    val configOverride: AnalysisConfig? = null,
    val trafficUrl: String = "",
    val appLanguage: String = "uz",
    val reportLanguage: String = "uz",
    val engineerName: String = "",
    val theme: AppTheme = AppTheme.DARK,
    val capabilities: DeviceCapabilities? = null,
) {
    val effectiveConfig: AnalysisConfig get() = configOverride ?: AnalysisConfig.forPreset(preset)
}

interface SettingsRepository {
    val settings: Flow<Settings>

    suspend fun current(): Settings = settings.first()

    suspend fun update(transform: (Settings) -> Settings)
}

class DataStoreSettingsRepository @Inject constructor(private val store: DataStore<Preferences>) : SettingsRepository {
    private object Keys {
        val PRESET = stringPreferencesKey("preset")
        val CONFIG = stringPreferencesKey("config_override")
        val TRAFFIC = stringPreferencesKey("traffic_url")
        val APP_LANG = stringPreferencesKey("app_language")
        val REPORT_LANG = stringPreferencesKey("report_language")
        val ENGINEER = stringPreferencesKey("engineer_name")
        val THEME = stringPreferencesKey("theme")
        val CAPS = stringPreferencesKey("capabilities")
    }

    override val settings: Flow<Settings> = store.data.map { it.toSettings() }

    private fun Preferences.toSettings(): Settings {
        val d = Settings()
        return Settings(
            preset = this[Keys.PRESET]?.let { runCatching { AnalysisPreset.valueOf(it) }.getOrNull() } ?: d.preset,
            configOverride = this[Keys.CONFIG]?.let { runCatching { SvJson.parseConfig(it) }.getOrNull() },
            trafficUrl = this[Keys.TRAFFIC] ?: d.trafficUrl,
            appLanguage = this[Keys.APP_LANG] ?: d.appLanguage,
            reportLanguage = this[Keys.REPORT_LANG] ?: d.reportLanguage,
            engineerName = this[Keys.ENGINEER] ?: d.engineerName,
            theme = this[Keys.THEME]?.let { runCatching { AppTheme.valueOf(it) }.getOrNull() } ?: d.theme,
            capabilities = this[Keys.CAPS]?.let {
                runCatching { SvJson.compact.decodeFromString(DeviceCapabilities.serializer(), it) }.getOrNull()
            },
        )
    }

    override suspend fun update(transform: (Settings) -> Settings) {
        store.edit { p ->
            val n = transform(p.toSettings())
            p[Keys.PRESET] = n.preset.name
            n.configOverride?.let { p[Keys.CONFIG] = SvJson.compact.encodeToString(AnalysisConfig.serializer(), it) }
                ?: p.remove(Keys.CONFIG)
            p[Keys.TRAFFIC] = n.trafficUrl
            p[Keys.APP_LANG] = n.appLanguage
            p[Keys.REPORT_LANG] = n.reportLanguage
            p[Keys.ENGINEER] = n.engineerName
            p[Keys.THEME] = n.theme.name
            n.capabilities?.let { p[Keys.CAPS] = SvJson.compact.encodeToString(DeviceCapabilities.serializer(), it) } ?: p.remove(Keys.CAPS)
        }
    }
}
