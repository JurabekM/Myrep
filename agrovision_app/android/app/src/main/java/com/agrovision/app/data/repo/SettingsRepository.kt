package com.agrovision.app.data.repo

import com.agrovision.app.config.Constants
import com.agrovision.app.core.I18n
import com.agrovision.app.core.NetworkStatus
import com.agrovision.app.data.local.SettingDao
import com.agrovision.app.data.local.SettingEntity
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SettingsRepository @Inject constructor(private val settingDao: SettingDao) {

    suspend fun get(key: String, default: String = ""): String = settingDao.get(key) ?: default

    suspend fun set(key: String, value: String) {
        settingDao.upsert(SettingEntity(key, value))
        applyGlobals(key, value)
    }

    suspend fun ensureDefaults() {
        Constants.DEFAULT_SETTINGS.forEach { (key, value) ->
            if (settingDao.get(key) == null) settingDao.upsert(SettingEntity(key, value))
        }
        loadGlobals()
    }

    /** Til va offlayn rejim kabi global holatlarni jarayon boshida tiklash. */
    suspend fun loadGlobals() {
        I18n.language = get("language", "uz")
        NetworkStatus.offlineMode = get("offline_mode", "auto")
    }

    private fun applyGlobals(key: String, value: String) {
        when (key) {
            "language" -> I18n.language = value
            "offline_mode" -> NetworkStatus.offlineMode = value
        }
    }
}
