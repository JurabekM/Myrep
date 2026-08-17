package uz.buildcontrol.mobile.data.sync

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Supabase / PostgREST backend — the same `bc_changes` table the desktop uses.
 *
 * Plain HTTPS on port 443, so it works from any site office without extra
 * network configuration.
 */
class SupabaseTransport(
    baseUrl: String,
    private val apiKey: String,
    private val tenant: String = "buildcontrol",
    private val client: OkHttpClient = defaultClient,
) : SyncTransport {

    override val key: String = "supabase"

    private val url: String = baseUrl.trim().trimEnd('/')

    init {
        if (url.isEmpty() || apiKey.isBlank()) {
            throw TransportException("Supabase URL yoki API kaliti to'ldirilmagan")
        }
        if (url.toHttpUrlOrNull() == null) {
            throw TransportException("Supabase URL noto'g'ri: $url")
        }
    }

    private val endpoint get() = "$url/rest/v1/$TABLE"

    override fun describe(): String = "$url  ($tenant)"

    private fun Request.Builder.auth() = apply {
        header("apikey", apiKey)
        header("Authorization", "Bearer $apiKey")
    }

    private fun execute(request: Request): Pair<String, Map<String, String>> {
        val response = try {
            client.newCall(request).execute()
        } catch (exc: IOException) {
            throw TransportException("Serverga ulanib bo'lmadi: ${exc.message}", exc)
        }
        response.use {
            val body = it.body?.string().orEmpty()
            if (!it.isSuccessful) {
                val detail = body.take(300)
                when (it.code) {
                    401, 403 -> throw TransportException("Kirish rad etildi (${it.code}). $detail")
                    404 -> throw TransportException(
                        "'$TABLE' jadvali topilmadi — Supabase SQL editor'da sozlash skriptini bajaring."
                    )
                    else -> throw TransportException("Server xatosi ${it.code}: $detail")
                }
            }
            val headers = it.headers.toMultimap().mapValues { entry -> entry.value.joinToString() }
            return body to headers
        }
    }

    override fun check(): String {
        val target = "$endpoint?tenant=eq.$tenant&select=seq&order=seq.desc&limit=1"
        val (body, headers) = execute(
            Request.Builder().url(target).get().auth().header("Prefer", "count=exact").build()
        )
        val rows = parseArray(body)
        val last = rows.firstOrNull()?.jsonObject?.get("seq")?.jsonPrimitive?.content ?: "0"
        val total = headers["content-range"]?.substringAfterLast('/') ?: "?"
        return "OK · oxirgi seq=$last · jami=$total"
    }

    override fun push(changes: List<Change>): Int {
        if (changes.isEmpty()) return 0
        val payload = JsonArray(changes.map { it.toWire(tenant) })
        val body = SyncJson.encodeToString(JsonArray.serializer(), payload)
            .toRequestBody(JSON_MEDIA)
        execute(
            Request.Builder().url(endpoint).post(body).auth()
                .header("Prefer", "return=minimal").build()
        )
        return changes.size
    }

    override fun pull(after: String, limit: Int): List<Change> {
        val last = after.toLongOrNull() ?: 0L
        val target = "$endpoint?tenant=eq.$tenant&seq=gt.$last" +
            "&select=seq,device,entity,uid,op,payload,ts&order=seq.asc&limit=$limit"
        val (body, _) = execute(Request.Builder().url(target).get().auth().build())
        return parseArray(body).map { element ->
            val row = element.jsonObject
            Change.fromWire(row, row["seq"]?.jsonPrimitive?.content.orEmpty())
        }
    }

    private fun parseArray(body: String): List<kotlinx.serialization.json.JsonElement> =
        if (body.isBlank()) emptyList() else SyncJson.parseToJsonElement(body).jsonArray

    companion object {
        const val TABLE = "bc_changes"
        private val JSON_MEDIA = "application/json; charset=utf-8".toMediaType()

        val defaultClient: OkHttpClient by lazy {
            OkHttpClient.Builder()
                .connectTimeout(20, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .retryOnConnectionFailure(true)
                .build()
        }

        /** Statement the user runs once in the Supabase SQL editor. */
        val SETUP_SQL = """
            create table if not exists public.bc_changes (
                seq     bigserial primary key,
                tenant  text        not null,
                device  text        not null,
                entity  text        not null,
                uid     text        not null,
                op      text        not null default 'upsert',
                payload jsonb       not null default '{}'::jsonb,
                ts      timestamptz not null default now()
            );
            create index if not exists bc_changes_tenant_seq_idx
                on public.bc_changes (tenant, seq);
            alter table public.bc_changes enable row level security;
            drop policy if exists bc_changes_rw on public.bc_changes;
            create policy bc_changes_rw on public.bc_changes
                for all to anon, authenticated
                using (true) with check (true);
        """.trimIndent()
    }
}

/** Fallback used when replication is switched off. */
object DisabledTransport : SyncTransport {
    override val key = "off"
    override fun describe() = "—"
    override fun check(): String = throw TransportException("Sinxronizatsiya o'chirilgan")
    override fun push(changes: List<Change>) = 0
    override fun pull(after: String, limit: Int): List<Change> = emptyList()
}

/** JsonObject helper kept here so callers do not import kotlinx internals. */
fun emptyPayload(): JsonObject = JsonObject(emptyMap())
