package uz.buildcontrol.mobile.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "buildcontrol_prefs")

/** Replication configuration entered by the user. */
data class SyncSettings(
    val backend: String = "off",
    val url: String = "",
    val apiKey: String = "",
    val tenant: String = "buildcontrol",
    val deviceName: String = "",
    val auto: Boolean = true,
    val mqttHost: String = "broker.hivemq.com",
    val mqttPort: Int = 8883,
    val mqttPrefix: String = "buildcontrol",
    val mqttTls: Boolean = true,
    val mqttUser: String = "",
    val mqttPassword: String = "",
    val passphrase: String = "",
) {
    val enabled: Boolean get() = backend != "off" && backend.isNotBlank()
}

/** Persistent preferences (language, session, replication). */
class Prefs(private val context: Context) {

    private object Keys {
        val language = stringPreferencesKey("language")
        val rememberedUser = stringPreferencesKey("remembered_user")
        val backend = stringPreferencesKey("sync_backend")
        val url = stringPreferencesKey("sync_url")
        val apiKey = stringPreferencesKey("sync_api_key")
        val tenant = stringPreferencesKey("sync_tenant")
        val deviceName = stringPreferencesKey("sync_device_name")
        val auto = booleanPreferencesKey("sync_auto")
        val mqttHost = stringPreferencesKey("sync_mqtt_host")
        val mqttPort = intPreferencesKey("sync_mqtt_port")
        val mqttPrefix = stringPreferencesKey("sync_mqtt_prefix")
        val mqttTls = booleanPreferencesKey("sync_mqtt_tls")
        val mqttUser = stringPreferencesKey("sync_mqtt_user")
        val mqttPassword = stringPreferencesKey("sync_mqtt_password")
        val passphrase = stringPreferencesKey("sync_passphrase")
    }

    val language: Flow<String> = context.dataStore.data.map { it[Keys.language] ?: "uz" }

    suspend fun setLanguage(code: String) {
        context.dataStore.edit { it[Keys.language] = code }
    }

    val rememberedUser: Flow<String> = context.dataStore.data.map { it[Keys.rememberedUser] ?: "" }

    suspend fun setRememberedUser(username: String) {
        context.dataStore.edit { it[Keys.rememberedUser] = username }
    }

    val syncSettings: Flow<SyncSettings> = context.dataStore.data.map { prefs ->
        SyncSettings(
            backend = prefs[Keys.backend] ?: "off",
            url = prefs[Keys.url] ?: "",
            apiKey = prefs[Keys.apiKey] ?: "",
            tenant = prefs[Keys.tenant] ?: "buildcontrol",
            deviceName = prefs[Keys.deviceName] ?: "",
            auto = prefs[Keys.auto] ?: true,
            mqttHost = prefs[Keys.mqttHost] ?: "broker.hivemq.com",
            mqttPort = prefs[Keys.mqttPort] ?: 8883,
            mqttPrefix = prefs[Keys.mqttPrefix] ?: "buildcontrol",
            mqttTls = prefs[Keys.mqttTls] ?: true,
            mqttUser = prefs[Keys.mqttUser] ?: "",
            mqttPassword = prefs[Keys.mqttPassword] ?: "",
            passphrase = prefs[Keys.passphrase] ?: "",
        )
    }

    suspend fun currentSync(): SyncSettings = syncSettings.first()

    suspend fun saveSync(settings: SyncSettings) {
        context.dataStore.edit {
            it[Keys.backend] = settings.backend
            it[Keys.url] = settings.url
            it[Keys.apiKey] = settings.apiKey
            it[Keys.tenant] = settings.tenant.ifBlank { "buildcontrol" }
            it[Keys.deviceName] = settings.deviceName
            it[Keys.auto] = settings.auto
            it[Keys.mqttHost] = settings.mqttHost
            it[Keys.mqttPort] = settings.mqttPort
            it[Keys.mqttPrefix] = settings.mqttPrefix.ifBlank { "buildcontrol" }
            it[Keys.mqttTls] = settings.mqttTls
            it[Keys.mqttUser] = settings.mqttUser
            it[Keys.mqttPassword] = settings.mqttPassword
            it[Keys.passphrase] = settings.passphrase
        }
    }
}
