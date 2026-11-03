package uz.havoradar.app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import uz.havoradar.engine.Engine
import uz.havoradar.engine.alert.AlertNotification
import uz.havoradar.engine.alert.AlertPolicy
import uz.havoradar.engine.model.RiskLevel
import uz.havoradar.engine.model.Settings
import uz.havoradar.engine.model.Snapshot
import uz.havoradar.engine.model.StoredState
import uz.havoradar.engine.net.UrlConnectionFetcher
import java.io.File
import java.time.Instant
import java.time.LocalTime

/**
 * Yadro ([Engine]) ustidagi Android qatlami: xom prognozni faylda, sozlamalarni SharedPreferences'da
 * saqlaydi. Bir vaqtda faqat bitta sinxronlash ishlaydi (UI tugmasi va fon vazifasi to'qnashmaydi).
 */
class Repository private constructor(
    context: Context,
) {
    private val app = context.applicationContext
    private val prefs = app.getSharedPreferences("havoradar", Context.MODE_PRIVATE)
    private val stateFile = File(app.filesDir, "state.json")
    private val mutex = Mutex()
    private val policy = AlertPolicy()

    val engine: Engine by lazy {
        Engine(UrlConnectionFetcher(userAgent = "HavoRadar/${BuildConfig.VERSION_NAME} (Android; +https://github.com/JurabekM/Myrep)"))
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

    private fun loadState(): StoredState? =
        runCatching { stateFile.takeIf { it.exists() }?.let { engine.codec.decodeState(it.readText()) } }.getOrNull()

    /** Saqlangan prognozdan joriy sozlamalar va vaqt bo'yicha baholangan snapshot (tarmoqsiz). */
    suspend fun current(): Snapshot? =
        withContext(Dispatchers.IO) {
            loadState()?.let { engine.reassess(it, settings()) }
        }

    suspend fun sync(): SyncResult =
        mutex.withLock {
            withContext(Dispatchers.IO) {
                val settings = settings()
                val synced = engine.sync(settings, loadState())
                val tmp = File(stateFile.path + ".tmp")
                tmp.writeText(engine.codec.encodeState(synced.state).toString())
                tmp.renameTo(stateFile)

                val firstRun = !prefs.contains(KEY_NOTIFIED)
                val decision = policy.decide(synced.snapshot, settings, notified(), firstRun, LocalTime.now())
                prefs
                    .edit()
                    .putString(KEY_NOTIFIED, encodeNotified(decision.notified))
                    .putString(KEY_LAST_SYNC, Instant.now().toString())
                    .apply()
                SyncResult(synced.snapshot, decision.notifications)
            }
        }

    fun lastSync(): String? = prefs.getString(KEY_LAST_SYNC, null)

    fun encode(snapshot: Snapshot): String = engine.codec.encode(snapshot).toString()

    fun catalogJson(): String = engine.codec.catalog().toString()

    private fun notified(): Map<String, RiskLevel> {
        val raw = prefs.getString(KEY_NOTIFIED, null) ?: return emptyMap()
        val o = runCatching { Json.parseToJsonElement(raw).jsonObject }.getOrNull() ?: return emptyMap()
        return o.mapNotNull { (k, v) -> RiskLevel.parse((v as? JsonPrimitive)?.content)?.let { k to it } }.toMap()
    }

    private fun encodeNotified(map: Map<String, RiskLevel>): String = JsonObject(map.mapValues { JsonPrimitive(it.value.name) }).toString()

    companion object {
        @Volatile private var instance: Repository? = null

        /**
         * Jarayon bo'yicha yagona nusxa (Activity, WorkManager, vidjet bir xil holat va Mutex'ni ulashadi).
         * `applicationContext` turiga tayanmaymiz: WorkManager/test kontekstlari Application bo'lmasligi mumkin.
         */
        fun get(context: Context): Repository =
            instance ?: synchronized(this) {
                instance ?: Repository(context.applicationContext ?: context).also { instance = it }
            }

        private const val KEY_SETTINGS = "settings"
        private const val KEY_NOTIFIED = "notified"
        private const val KEY_LAST_SYNC = "last_sync"
    }
}
