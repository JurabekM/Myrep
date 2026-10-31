package uz.epiradar.engine.json

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.add
import kotlinx.serialization.json.addJsonObject
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonArray
import kotlinx.serialization.json.putJsonObject
import uz.epiradar.engine.geo.Countries
import uz.epiradar.engine.knowledge.DiseaseCatalog
import uz.epiradar.engine.model.Anomaly
import uz.epiradar.engine.model.OutbreakEvent
import uz.epiradar.engine.model.Settings
import uz.epiradar.engine.model.Signal
import uz.epiradar.engine.model.SignalFlag
import uz.epiradar.engine.model.Snapshot
import uz.epiradar.engine.model.SourceId
import uz.epiradar.engine.model.SourceStatus
import uz.epiradar.engine.model.ThreatLevel
import uz.epiradar.engine.model.TrendPoint
import uz.epiradar.engine.model.TrendSeries
import uz.epiradar.engine.model.TrendStatus
import java.time.Instant

/** Saqlanadigan xom holat: hodisalar va baholar har safar shundan qayta hisoblanadi. */
data class StoredState(
    val generatedAt: Instant,
    val signals: List<Signal>,
    val trends: List<TrendSeries>,
    val trendsFetchedAt: Instant?,
    val sources: List<SourceStatus>,
)

/**
 * Snapshot ↔ JSON. Bitta format ham diskda saqlash, ham Flutter'ga (MethodChannel) uzatish uchun:
 * UI maydonlari (nomlar, darajalar, sabablar) o'zbekcha tayyor holda yuboriladi.
 */
class Codec(
    private val catalog: DiseaseCatalog,
    private val countries: Countries,
) {
    // ---------- Snapshot → JSON ----------

    fun encode(s: Snapshot): JsonObject =
        buildJsonObject {
            put("schema", SCHEMA)
            put("generatedAt", s.generatedAt.toString())
            put("country", s.country)
            put("countryName", countries.nameUz(s.country))
            put("global", level(s.globalScore))
            put("personal", level(s.personalScore))
            put("trendsFetchedAt", s.trendsFetchedAt?.toString())
            putJsonArray("events") { s.events.forEach { add(event(it)) } }
            putJsonArray("trends") { s.trends.forEach { add(trend(it)) } }
            putJsonArray("sources") { s.sources.forEach { add(source(it)) } }
            putJsonArray("signals") { s.signals.forEach { add(signal(it)) } }
        }

    fun level(score: Int): JsonObject {
        val l = ThreatLevel.of(score)
        return buildJsonObject {
            put("score", score)
            put("level", l.name)
            put("name", l.uz)
            put("advice", l.advice)
        }
    }

    private fun event(e: OutbreakEvent): JsonObject =
        buildJsonObject {
            val d = catalog[e.diseaseId]
            put("id", e.id)
            put("diseaseId", e.diseaseId)
            put("diseaseName", d.name)
            put("title", e.title)
            putJsonArray("countries") {
                e.countries.forEach { c ->
                    addJsonObject {
                        put("iso3", c)
                        put("name", countries.nameUz(c))
                    }
                }
            }
            put("firstSeen", e.firstSeen.toString())
            put("lastUpdated", e.lastUpdated.toString())
            putJsonArray("flags") { e.flags.sortedByDescending { it.weight }.forEach { add(it.uz) } }
            put("travelLevel", e.travelLevel)
            put("global", level(e.assessment.globalScore))
            put("personal", level(e.assessment.personalScore))
            put("distanceKm", e.assessment.distanceKm)
            putJsonArray("reasons") { e.assessment.reasons.forEach { add(it) } }
            putJsonArray("signals") { e.signals.forEach { add(signal(it)) } }
        }

    fun signal(s: Signal): JsonObject =
        buildJsonObject {
            put("id", s.id)
            put("source", s.source.name)
            put("sourceTitle", s.source.title)
            put("title", s.title)
            put("summary", s.summary)
            put("url", s.url)
            put("publishedAt", s.publishedAt.toString())
            putJsonArray("countries") { s.countries.forEach { add(it) } }
            put("diseaseId", s.diseaseId)
            putJsonArray("flags") { s.flags.forEach { add(it.name) } }
            put("travelLevel", s.travelLevel)
        }

    private fun trend(t: TrendSeries): JsonObject =
        buildJsonObject {
            put("id", t.id)
            put("country", t.country)
            put("countryName", countries.nameUz(t.country))
            put("title", t.title)
            put("unit", t.unit)
            put("status", t.status.name)
            put("statusName", t.status.uz)
            put("note", t.note)
            putJsonArray("novelFluWeeks") { t.novelFluWeeks.forEach { add(it) } }
            putJsonArray("points") {
                t.points.forEach { p ->
                    addJsonObject {
                        put("week", p.weekStart)
                        put("value", p.value)
                        put("tested", p.tested)
                    }
                }
            }
            putJsonArray("anomalies") {
                t.anomalies.forEach { a ->
                    addJsonObject {
                        put("week", a.weekStart)
                        put("value", a.value)
                        put("expected", a.expected)
                        put("threshold", a.threshold)
                        put("method", a.method)
                    }
                }
            }
        }

    private fun source(s: SourceStatus): JsonObject =
        buildJsonObject {
            put("id", s.source.name)
            put("title", s.source.title)
            put("homepage", s.source.homepage)
            put("ok", s.ok)
            put("itemCount", s.itemCount)
            put("fetchedAt", s.fetchedAt.toString())
            put("error", s.error)
            put("stale", s.stale)
        }

    // ---------- JSON → StoredState ----------

    fun decodeState(text: String): StoredState? =
        runCatching {
            val o = Json.parseToJsonElement(text).jsonObject
            if (o.int("schema") != SCHEMA) return null
            StoredState(
                generatedAt = Instant.parse(o.str("generatedAt")),
                signals = o.arr("signals").map { decodeSignal(it.jsonObject) },
                trends = o.arr("trends").map { decodeTrend(it.jsonObject) },
                trendsFetchedAt = o.str("trendsFetchedAt")?.let(Instant::parse),
                sources = o.arr("sources").mapNotNull { decodeSource(it.jsonObject) },
            )
        }.getOrNull()

    private fun decodeSignal(o: JsonObject) =
        Signal(
            id = o.str("id")!!,
            source = SourceId.valueOf(o.str("source")!!),
            title = o.str("title").orEmpty(),
            summary = o.str("summary").orEmpty(),
            url = o.str("url").orEmpty(),
            publishedAt = Instant.parse(o.str("publishedAt")),
            countries = o.arr("countries").map { (it as JsonPrimitive).content },
            diseaseId = o.str("diseaseId") ?: DiseaseCatalog.OTHER,
            flags = o.arr("flags").mapNotNull { f -> SignalFlag.entries.firstOrNull { it.name == (f as JsonPrimitive).content } }.toSet(),
            travelLevel = o.int("travelLevel"),
        )

    private fun decodeTrend(o: JsonObject) =
        TrendSeries(
            id = o.str("id")!!,
            country = o.str("country")!!,
            title = o.str("title").orEmpty(),
            unit = o.str("unit").orEmpty(),
            points =
                o.arr("points").map {
                    val p = it.jsonObject
                    TrendPoint(p.str("week")!!, p.dbl("value") ?: 0.0, p.int("tested") ?: 0)
                },
            anomalies =
                o.arr("anomalies").map {
                    val a = it.jsonObject
                    Anomaly(a.str("week")!!, a.dbl("value") ?: 0.0, a.dbl("expected") ?: 0.0, a.dbl("threshold") ?: 0.0, a.str("method").orEmpty())
                },
            status = TrendStatus.entries.firstOrNull { it.name == o.str("status") } ?: TrendStatus.NO_DATA,
            novelFluWeeks = o.arr("novelFluWeeks").map { (it as JsonPrimitive).content },
            note = o.str("note").orEmpty(),
        )

    private fun decodeSource(o: JsonObject): SourceStatus? {
        val id = SourceId.entries.firstOrNull { it.name == o.str("id") } ?: return null
        return SourceStatus(
            source = id,
            ok = o["ok"]?.let { (it as? JsonPrimitive)?.booleanOrNull } ?: false,
            itemCount = o.int("itemCount") ?: 0,
            fetchedAt = Instant.parse(o.str("fetchedAt")),
            error = o.str("error"),
            stale = (o["stale"] as? JsonPrimitive)?.booleanOrNull ?: false,
        )
    }

    // ---------- Settings ----------

    fun encodeSettings(s: Settings): JsonObject =
        buildJsonObject {
            put("country", s.country)
            put("notificationsEnabled", s.notificationsEnabled)
            put("alertThreshold", s.alertThreshold.name)
            put("syncHours", s.syncHours)
            putJsonArray("watchCountries") { s.watchCountries.forEach { add(it) } }
            putJsonArray("checklistDone") { s.checklistDone.forEach { add(it) } }
            put("onboardingDone", s.onboardingDone)
            put("lightTheme", s.lightTheme)
        }

    /** Noto'g'ri qiymatlar xavfsiz standartlarga qaytariladi (UI'dan kelgan ma'lumotga ishonmaymiz). */
    fun decodeSettings(text: String?): Settings {
        val d = Settings()
        if (text.isNullOrBlank()) return d
        val o = runCatching { Json.parseToJsonElement(text).jsonObject }.getOrNull() ?: return d
        val country = o.str("country")?.takeIf { countries[it] != null } ?: d.country
        return Settings(
            country = country,
            notificationsEnabled = (o["notificationsEnabled"] as? JsonPrimitive)?.booleanOrNull ?: d.notificationsEnabled,
            alertThreshold = ThreatLevel.parse(o.str("alertThreshold"))?.takeIf { it > ThreatLevel.CALM } ?: d.alertThreshold,
            syncHours = o.int("syncHours")?.takeIf { it in Settings.SYNC_CHOICES } ?: d.syncHours,
            watchCountries = o.arr("watchCountries").mapNotNull { (it as? JsonPrimitive)?.content }.filter { countries[it] != null && it != country }.distinct().take(10),
            checklistDone = o.arr("checklistDone").mapNotNull { (it as? JsonPrimitive)?.content }.distinct().take(100),
            onboardingDone = (o["onboardingDone"] as? JsonPrimitive)?.booleanOrNull ?: false,
            lightTheme = (o["lightTheme"] as? JsonPrimitive)?.booleanOrNull ?: false,
        )
    }

    // ---------- Ma'lumotnomalar (Flutter uchun) ----------

    fun diseases(): JsonArray = buildJsonArray { catalog.all.forEach { add(it.json) } }

    fun countryList(): JsonArray =
        buildJsonArray {
            countries.all.sortedBy { it.nameUz }.forEach { c ->
                addJsonObject {
                    put("iso3", c.iso3)
                    put("name", c.nameUz)
                    put("nameEn", c.nameEn)
                }
            }
        }

    fun levels(): JsonArray =
        buildJsonArray {
            ThreatLevel.entries.forEach { l ->
                addJsonObject {
                    put("level", l.name)
                    put("name", l.uz)
                    put("minScore", l.minScore)
                    put("advice", l.advice)
                }
            }
        }

    companion object {
        const val SCHEMA = 1

        private fun JsonObject.str(key: String): String? = (this[key] as? JsonPrimitive)?.takeUnless { it is JsonNull }?.content

        private fun JsonObject.int(key: String): Int? = (this[key] as? JsonPrimitive)?.intOrNull

        private fun JsonObject.dbl(key: String): Double? = (this[key] as? JsonPrimitive)?.doubleOrNull

        private fun JsonObject.arr(key: String): JsonArray = (this[key] as? JsonArray) ?: JsonArray(emptyList())
    }
}
