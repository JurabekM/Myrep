package uz.havoradar.engine.json

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
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
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonArray
import uz.havoradar.engine.geo.Places
import uz.havoradar.engine.knowledge.Guide
import uz.havoradar.engine.model.AirSeries
import uz.havoradar.engine.model.DayReport
import uz.havoradar.engine.model.HazardAssessment
import uz.havoradar.engine.model.HourPoint
import uz.havoradar.engine.model.PlaceReport
import uz.havoradar.engine.model.RiskLevel
import uz.havoradar.engine.model.Settings
import uz.havoradar.engine.model.Snapshot
import uz.havoradar.engine.model.SourceId
import uz.havoradar.engine.model.SourceStatus
import uz.havoradar.engine.model.StoredState
import uz.havoradar.engine.model.UvCategory
import uz.havoradar.engine.model.Vulnerability
import uz.havoradar.engine.model.WeatherSeries
import java.time.Instant
import java.time.LocalDateTime
import kotlin.math.round

/**
 * JSON formatlar: (1) diskdagi xom holat [StoredState], (2) Flutter'ga uzatiladigan [Snapshot] —
 * UI matnlari (darajalar, sabablar, tavsiyalar) o'zbekcha tayyor holda, (3) sozlamalar va ma'lumotnomalar.
 * Dart tomoni: lib/data/models.dart.
 */
class Codec(
    private val places: Places,
    private val guide: Guide,
) {
    // ---------- Snapshot → JSON (Flutter) ----------

    fun encode(s: Snapshot): JsonObject =
        buildJsonObject {
            put("schema", SCHEMA)
            put("generatedAt", s.generatedAt.toString())
            putJsonArray("profile") { s.profile.forEach { add(it.name) } }
            putJsonArray("places") { s.places.forEach { add(place(it)) } }
            putJsonArray("sources") { s.sources.forEach { add(source(it)) } }
        }

    fun level(score: Int): JsonObject {
        val l = RiskLevel.of(score)
        return buildJsonObject {
            put("score", score)
            put("level", l.name)
            put("name", l.uz)
            put("advice", l.advice)
        }
    }

    private fun place(r: PlaceReport): JsonObject =
        buildJsonObject {
            put("id", r.place.id)
            put("name", r.place.name)
            put("localNow", r.localNow.toString())
            put("weatherFetchedAt", r.weatherFetchedAt?.toString())
            put("airFetchedAt", r.airFetchedAt?.toString())
            put("today", r.today?.personalScore?.let(::level) ?: JsonNull)
            put("current", r.current?.let(::hour) ?: JsonNull)
            putJsonArray("days") { r.days.forEach { add(day(it)) } }
            putJsonArray("hours") { r.hours.forEach { add(hour(it)) } }
        }

    private fun day(d: DayReport): JsonObject =
        buildJsonObject {
            put("date", d.date.toString())
            put("overall", d.personalScore?.let(::level) ?: JsonNull)
            put("tempMax", d.tempMax.r1())
            put("tempMin", d.tempMin.r1())
            put("feelsMax", d.feelsMax.r1())
            put("feelsPeakHour", d.feelsPeakHour)
            put("uvMax", d.uvMax.r1())
            put(
                "uv",
                d.uvMax?.let {
                    val c = UvCategory.of(it)
                    buildJsonObject {
                        put("category", c.name)
                        put("name", c.uz)
                        put("advice", c.advice)
                    }
                } ?: JsonNull,
            )
            put(
                "air",
                d.air?.let { a ->
                    buildJsonObject {
                        put("pm25", a.pm25Mean.r1())
                        put("pm10", a.pm10Mean.r1())
                        put("ozone8h", a.ozoneMax8h.r1())
                        put("no2", a.no2Mean.r1())
                        put("no2Max", a.no2Max.r1())
                        put("dustShare", a.dustShare?.let { round(it * 100) / 100 })
                        put("worstHour", a.worstHour)
                    }
                } ?: JsonNull,
            )
            put("heatRisk", d.heatRisk?.let(::hazard) ?: JsonNull)
            put("airRisk", d.airRisk?.let(::hazard) ?: JsonNull)
        }

    private fun hazard(h: HazardAssessment): JsonObject =
        buildJsonObject {
            put("hazard", h.hazard.name)
            put("name", h.hazard.uz)
            put("base", level(h.baseScore))
            put("personal", level(h.personalScore))
            putJsonArray("reasons") { h.reasons.forEach { add(it) } }
            putJsonArray("advice") { h.advice.forEach { add(it) } }
        }

    private fun hour(h: HourPoint): JsonObject =
        buildJsonObject {
            put("time", h.time.toString())
            put("temp", h.temp.r1())
            put("feels", h.feels.r1())
            put("humidity", h.humidity.r1())
            put("uv", h.uv.r1())
            put("pm25", h.pm25.r1())
            put("pm10", h.pm10.r1())
        }

    private fun source(s: SourceStatus): JsonObject =
        buildJsonObject {
            put("id", s.source.name)
            put("title", s.source.title)
            put("homepage", s.source.homepage)
            put("ok", s.ok)
            put("fetchedAt", s.fetchedAt.toString())
            put("error", s.error)
            put("stale", s.stale)
        }

    // ---------- StoredState ↔ JSON (disk) ----------

    fun encodeState(s: StoredState): JsonObject =
        buildJsonObject {
            put("schema", SCHEMA)
            put("generatedAt", s.generatedAt.toString())
            putJsonArray("weather") {
                s.weather.forEach { w ->
                    addJsonObject {
                        series(w.placeId, w.fetchedAt, w.utcOffsetSeconds, w.times)
                        put("temp", nums(w.temp))
                        put("humidity", nums(w.humidity))
                        put("uv", nums(w.uv))
                    }
                }
            }
            putJsonArray("air") {
                s.air.forEach { a ->
                    addJsonObject {
                        series(a.placeId, a.fetchedAt, a.utcOffsetSeconds, a.times)
                        put("pm25", nums(a.pm25))
                        put("pm10", nums(a.pm10))
                        put("ozone", nums(a.ozone))
                        put("no2", nums(a.no2))
                        put("dust", nums(a.dust))
                    }
                }
            }
            putJsonArray("sources") { s.sources.forEach { add(source(it)) } }
        }

    fun decodeState(text: String): StoredState? =
        runCatching {
            val o = Json.parseToJsonElement(text).jsonObject
            if (o.int("schema") != SCHEMA) return null
            StoredState(
                generatedAt = Instant.parse(o.str("generatedAt")),
                weather =
                    o.arr("weather").map {
                        val w = it.jsonObject
                        val times = w.times()
                        WeatherSeries(
                            w.str("placeId")!!,
                            Instant.parse(w.str("fetchedAt")),
                            w.int("offset") ?: 0,
                            times,
                            w.nums("temp", times.size),
                            w.nums("humidity", times.size),
                            w.nums("uv", times.size),
                        )
                    },
                air =
                    o.arr("air").map {
                        val a = it.jsonObject
                        val times = a.times()
                        AirSeries(
                            a.str("placeId")!!,
                            Instant.parse(a.str("fetchedAt")),
                            a.int("offset") ?: 0,
                            times,
                            a.nums("pm25", times.size),
                            a.nums("pm10", times.size),
                            a.nums("ozone", times.size),
                            a.nums("no2", times.size),
                            a.nums("dust", times.size),
                        )
                    },
                sources =
                    o.arr("sources").mapNotNull {
                        val s = it.jsonObject
                        val id = SourceId.entries.firstOrNull { e -> e.name == s.str("id") } ?: return@mapNotNull null
                        SourceStatus(id, s.bool("ok") ?: false, Instant.parse(s.str("fetchedAt")), s.str("error"), s.bool("stale") ?: false)
                    },
            )
        }.getOrNull()

    private fun kotlinx.serialization.json.JsonObjectBuilder.series(
        placeId: String,
        fetchedAt: Instant,
        offset: Int,
        times: List<LocalDateTime>,
    ) {
        put("placeId", placeId)
        put("fetchedAt", fetchedAt.toString())
        put("offset", offset)
        // Soatlar ketma-ket: boshlanish vaqti va soni yetarli (holat fayli kichik bo'ladi).
        put("start", times.firstOrNull()?.toString())
        put("count", times.size)
        val contiguous = times.zipWithNext().all { (a, b) -> b == a.plusHours(1) }
        if (!contiguous) putJsonArray("times") { times.forEach { add(it.toString()) } }
    }

    private fun JsonObject.times(): List<LocalDateTime> {
        (this["times"] as? JsonArray)?.let { arr -> return arr.map { LocalDateTime.parse((it as JsonPrimitive).content) } }
        val start = str("start")?.let(LocalDateTime::parse) ?: return emptyList()
        return List(int("count") ?: 0) { start.plusHours(it.toLong()) }
    }

    private fun nums(values: List<Double?>): JsonArray = JsonArray(values.map { v -> v?.let { JsonPrimitive(round(it * 100) / 100) } ?: JsonNull })

    private fun JsonObject.nums(
        key: String,
        size: Int,
    ): List<Double?> {
        val arr = arr(key)
        return List(size) { i -> (arr.getOrNull(i) as? JsonPrimitive)?.takeUnless { it is JsonNull }?.doubleOrNull }
    }

    // ---------- Settings ----------

    fun encodeSettings(s: Settings): JsonObject =
        buildJsonObject {
            put("placeId", s.placeId)
            putJsonArray("extraPlaces") { s.extraPlaces.forEach { add(it) } }
            putJsonArray("profile") { s.profile.forEach { add(it.name) } }
            put("notificationsEnabled", s.notificationsEnabled)
            put("alertThreshold", s.alertThreshold.name)
            put("syncHours", s.syncHours)
            put("quietHours", s.quietHours)
            put("onboardingDone", s.onboardingDone)
            put("lightTheme", s.lightTheme)
        }

    /** Noto'g'ri qiymatlar xavfsiz standartlarga qaytariladi (UI'dan kelgan ma'lumotga ishonmaymiz). */
    fun decodeSettings(text: String?): Settings {
        val d = Settings()
        if (text.isNullOrBlank()) return d
        val o = runCatching { Json.parseToJsonElement(text).jsonObject }.getOrNull() ?: return d
        val placeId = o.str("placeId")?.takeIf { places[it] != null } ?: d.placeId
        return Settings(
            placeId = placeId,
            extraPlaces =
                o
                    .arr("extraPlaces")
                    .mapNotNull { (it as? JsonPrimitive)?.content }
                    .filter { places[it] != null && it != placeId }
                    .distinct()
                    .take(Settings.MAX_EXTRA_PLACES),
            profile = o.arr("profile").mapNotNull { v -> Vulnerability.entries.firstOrNull { it.name == (v as? JsonPrimitive)?.content } }.toSet(),
            notificationsEnabled = o.bool("notificationsEnabled") ?: d.notificationsEnabled,
            alertThreshold = RiskLevel.parse(o.str("alertThreshold"))?.takeIf { it > RiskLevel.CALM } ?: d.alertThreshold,
            syncHours = o.int("syncHours")?.takeIf { it in Settings.SYNC_CHOICES } ?: d.syncHours,
            quietHours = o.bool("quietHours") ?: d.quietHours,
            onboardingDone = o.bool("onboardingDone") ?: false,
            lightTheme = o.bool("lightTheme") ?: false,
        )
    }

    // ---------- Ma'lumotnomalar (Flutter uchun) ----------

    fun catalog(): JsonObject =
        buildJsonObject {
            putJsonArray("places") {
                places.all.forEach { p ->
                    addJsonObject {
                        put("id", p.id)
                        put("name", p.name)
                        put("abroad", p.abroad)
                    }
                }
            }
            putJsonArray("levels") {
                RiskLevel.entries.forEach { l ->
                    addJsonObject {
                        put("level", l.name)
                        put("name", l.uz)
                        put("minScore", l.minScore)
                        put("advice", l.advice)
                    }
                }
            }
            putJsonArray("vulnerabilities") {
                Vulnerability.entries.forEach { v ->
                    addJsonObject {
                        put("id", v.name)
                        put("name", v.uz)
                        put("heat", v.heat)
                        put("air", v.air)
                    }
                }
            }
            putJsonArray("uvCategories") {
                UvCategory.entries.forEach { c ->
                    addJsonObject {
                        put("category", c.name)
                        put("name", c.uz)
                        put("min", c.min)
                        put("advice", c.advice)
                    }
                }
            }
            put("guide", guide.json)
        }

    companion object {
        const val SCHEMA = 1

        private fun Double?.r1(): JsonElement = this?.let { JsonPrimitive(round(it * 10) / 10) } ?: JsonNull

        private fun JsonObject.str(key: String): String? = (this[key] as? JsonPrimitive)?.takeUnless { it is JsonNull }?.content

        private fun JsonObject.int(key: String): Int? = (this[key] as? JsonPrimitive)?.intOrNull

        private fun JsonObject.bool(key: String): Boolean? = (this[key] as? JsonPrimitive)?.booleanOrNull

        private fun JsonObject.arr(key: String): JsonArray = (this[key] as? JsonArray) ?: JsonArray(emptyList())
    }
}
