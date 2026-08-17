package com.agrovision.mobile.data.repository

import com.agrovision.mobile.data.local.SettingDao
import com.agrovision.mobile.data.local.SettingEntity
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SettingsRepository @Inject constructor(private val settingDao: SettingDao) {

    companion object {
        val DEFAULTS = mapOf(
            "theme" to "light",
            "language" to "uz",
            "ml_auto_retrain" to "true",
        )
    }

    suspend fun get(key: String, default: String = ""): String = settingDao.get(key) ?: default
    suspend fun set(key: String, value: String) = settingDao.upsert(SettingEntity(key, value))

    suspend fun ensureDefaults() {
        if (settingDao.count() > 0) return
        DEFAULTS.forEach { (k, v) -> settingDao.upsert(SettingEntity(k, v)) }
    }
}
