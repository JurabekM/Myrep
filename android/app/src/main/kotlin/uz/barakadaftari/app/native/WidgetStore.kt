package uz.barakadaftari.app.native

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Vidjet holati. Shablonlar (summalar bilan) va bosilgan yozuvlar navbati
 * Keystore kaliti bilan shifrlangan bloblarda; faqat «qachongacha ko'rinadi»
 * vaqti oddiy sozlamada (maxfiy emas).
 */
class WidgetStore(private val context: Context) {
    data class Template(val id: String, val title: String, val amountLabel: String)

    data class State(
        val templates: List<Template>,
        val title: String,
        val locked: String,
        val empty: String,
    )

    private val blobs by lazy {
        SecureBlobStore(
            dir = File(context.noBackupFilesDir, "secure"),
            wrapper = AesGcmKeyWrapper(KeystoreKeys(context)::getOrCreateWrappingKey),
        )
    }

    private val prefs get() = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun saveState(state: State) = synchronized(LOCK) {
        val json = JSONObject()
            .put("title", state.title)
            .put("locked", state.locked)
            .put("empty", state.empty)
            .put(
                "templates",
                JSONArray().apply {
                    state.templates.forEach {
                        put(JSONObject().put("id", it.id).put("title", it.title).put("amount", it.amountLabel))
                    }
                },
            )
        blobs.write(BLOB_STATE, json.toString().toByteArray(Charsets.UTF_8))
    }

    fun state(): State = synchronized(LOCK) {
        val raw = runCatching { blobs.read(BLOB_STATE) }.getOrNull()
            ?: return State(emptyList(), "Baraka", "", "")
        val json = JSONObject(String(raw, Charsets.UTF_8))
        val list = json.getJSONArray("templates")
        State(
            templates = (0 until list.length()).map {
                val t = list.getJSONObject(it)
                Template(t.getString("id"), t.getString("title"), t.getString("amount"))
            },
            title = json.optString("title", "Baraka"),
            locked = json.optString("locked"),
            empty = json.optString("empty"),
        )
    }

    var visibleUntil: Long
        get() = prefs.getLong(KEY_VISIBLE_UNTIL, 0L)
        set(value) = prefs.edit().putLong(KEY_VISIBLE_UNTIL, value).apply()

    fun showAmounts(nowMillis: Long): Boolean = WidgetVisibility.showAmounts(visibleUntil, nowMillis)

    /** Vidjet tugmasi bosildi: navbatga (shifrlangan). */
    fun addPending(templateId: String, atMillis: Long) = synchronized(LOCK) {
        val list = readPending()
        if (list.length() >= MAX_PENDING) return@synchronized
        list.put(JSONObject().put("id", templateId).put("at", atMillis))
        blobs.write(BLOB_PENDING, list.toString().toByteArray(Charsets.UTF_8))
    }

    fun pendingCount(): Int = synchronized(LOCK) { readPending().length() }

    /** Navbatni oladi va tozalaydi. */
    fun takePending(): List<Pair<String, Long>> = synchronized(LOCK) {
        val list = readPending()
        blobs.delete(BLOB_PENDING)
        (0 until list.length()).map {
            val o = list.getJSONObject(it)
            o.getString("id") to o.getLong("at")
        }
    }

    private fun readPending(): JSONArray {
        val raw = runCatching { blobs.read(BLOB_PENDING) }.getOrNull() ?: return JSONArray()
        return JSONArray(String(raw, Charsets.UTF_8))
    }

    companion object {
        private val LOCK = Any()
        private const val PREFS = "widget"
        private const val KEY_VISIBLE_UNTIL = "visible_until"
        private const val BLOB_STATE = "widget_state"
        private const val BLOB_PENDING = "widget_pending"

        /** Ilova ochilmasa ham navbat cheksiz o'smasin. */
        const val MAX_PENDING = 50
    }
}

/** Sof qoida (JUnit bilan testlanadi). */
object WidgetVisibility {
    /** Summalar faqat ilova qulfdan ochiq (yoki qulf vaqti tugamagan) paytda. */
    fun showAmounts(visibleUntil: Long, nowMillis: Long): Boolean = visibleUntil > nowMillis
}
