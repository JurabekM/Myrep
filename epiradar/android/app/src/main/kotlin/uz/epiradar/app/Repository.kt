package uz.epiradar.app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.put
import uz.epiradar.engine.Engine
import uz.epiradar.engine.alert.AlertNotification
import uz.epiradar.engine.alert.AlertPolicy
import uz.epiradar.engine.json.StoredState
import uz.epiradar.engine.model.Settings
import uz.epiradar.engine.model.Snapshot
import uz.epiradar.engine.model.ThreatLevel
import uz.epiradar.engine.net.UrlConnectionFetcher
import java.io.File
import java.time.Instant

/**
 * Yadro ([Engine]) ustidagi Android qatlami: holatni faylda, sozlamalarni SharedPreferences'da
 * saqlaydi. Bir vaqtda faqat bitta sinxronlash ishlaydi (UI tugmasi va fon vazifasi to'qnashmaydi).
 */
class Repository(
    context: Context,
) {
    private val app = context.applicationContext
    private val prefs = app.getSharedPreferences("epiradar", Context.MODE_PRIVATE)
    private val stateFile = File(app.filesDir, "state.json")
    private val mutex = Mutex()
    private val policy = AlertPolicy()

    val engine: Engine by lazy {
        Engine(UrlConnectionFetcher(userAgent = "EpiRadar/${BuildConfig.VERSION_NAME} (Android; +https://github.com/JurabekM/Myrep)"))
    }

    data class SyncResult(
        val snapshot: Snapshot,
        val notifications: List<AlertNotification>,
    )

    fun settings(): Settings = engine.codec.decodeSettings(prefs.getString(KEY_SETTINGS, null))

    /** UI'dan kelgan sozlamalarni tozalab saqlaydi; jadval o'zgargan bo'lsa qayta rejalashtiradi. */
    fun saveSettings(json: String): Settings {
        val old = settings()
        val new = engine.codec.decodeSettings(json)
        prefs.edit().putString(KEY_SETTINGS, engine.codec.encodeSettings(new).toString()).apply()
        if (old.syncHours != new.syncHours) SyncScheduler.schedule(app, new, replace = true)
        return new
    }

    private fun loadState(): StoredState? = stateFile.takeIf { it.exists() }?.let { engine.codec.decodeState(it.readText()) }

    /** Saqlangan holatdan joriy sozlamalar bo'yicha baholangan snapshot (tarmoqsiz). */
    suspend fun current(): Snapshot? =
        withContext(Dispatchers.IO) {
            loadState()?.let { engine.reassess(it, settings()) }
        }

    suspend fun sync(): SyncResult =
        mutex.withLock {
            withContext(Dispatchers.IO) {
                val settings = settings()
                val snapshot = engine.sync(settings, loadState())
                val tmp = File(stateFile.path + ".tmp")
                tmp.writeText(engine.codec.encode(snapshot).toString())
                tmp.renameTo(stateFile)

                val firstRun = !prefs.contains(KEY_NOTIFIED)
                val decision = policy.decide(snapshot, settings, notified(), firstRun, Instant.now())
                prefs
                    .edit()
                    .putString(KEY_NOTIFIED, encodeNotified(decision.notified))
                    .putString(KEY_LAST_SYNC, Instant.now().toString())
                    .apply()
                SyncResult(snapshot, decision.notifications)
            }
        }

    fun lastSync(): String? = prefs.getString(KEY_LAST_SYNC, null)

    fun encode(snapshot: Snapshot): String = engine.codec.encode(snapshot).toString()

    fun catalogJson(): String =
        buildJsonObject {
            put("diseases", engine.codec.diseases())
            put("countries", engine.codec.countryList())
            put("levels", engine.codec.levels())
            put("trendCountries", kotlinx.serialization.json.JsonArray(engine.trendCountries(settings()).map { JsonPrimitive(it) }))
        }.toString()

    private fun notified(): Map<String, ThreatLevel> {
        val raw = prefs.getString(KEY_NOTIFIED, null) ?: return emptyMap()
        val o = runCatching { Json.parseToJsonElement(raw).jsonObject }.getOrNull() ?: return emptyMap()
        return o.mapNotNull { (k, v) -> ThreatLevel.parse((v as? JsonPrimitive)?.content)?.let { k to it } }.toMap()
    }

    private fun encodeNotified(map: Map<String, ThreatLevel>): String = JsonObject(map.mapValues { JsonPrimitive(it.value.name) }).toString()

    companion object {
        private const val KEY_SETTINGS = "settings"
        private const val KEY_NOTIFIED = "notified"
        private const val KEY_LAST_SYNC = "last_sync"
    }
}
