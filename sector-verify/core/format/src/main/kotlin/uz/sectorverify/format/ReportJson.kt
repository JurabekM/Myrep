package uz.sectorverify.format

import java.time.Instant
import kotlin.math.roundToLong
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonArray
import kotlinx.serialization.json.putJsonObject
import uz.sectorverify.model.SectorResult
import uz.sectorverify.model.SessionResult
import uz.sectorverify.model.SitePlan

/** report.json, sxema `sector-verify/report/v1` (§5.5). */
object ReportJson {
    const val SCHEMA = "sector-verify/report/v1"
    const val KEY_ALG = "EC-P256/SHA256withECDSA"
    const val INTEGRITY = "integrity"

    /** Hisobotni integrity blokisiz quradi; literallar barqaror bo'lishi uchun sonlar 0.1 gacha yaxlitlanadi. */
    fun build(plan: SitePlan, meta: SessionMeta, result: SessionResult): JsonObject = buildJsonObject {
        put("schema", SCHEMA)
        putJsonObject("site") {
            put("code", plan.code)
            put("name", plan.name)
            put("lat", plan.lat)
            put("lon", plan.lon)
        }
        putJsonObject("session") {
            put("id", meta.id)
            put("mode", meta.mode.name)
            put("startedAt", iso(meta.startedAtUtcMs))
            put("endedAt", meta.endedAtUtcMs?.let(::iso))
            put("device", meta.deviceModel)
            put("apiLevel", meta.apiLevel)
            put("appVersion", meta.appVersion)
            put("algoVersion", meta.algoVersion)
            put("measuredRateHz", meta.measuredRateHz?.let(::r1))
            put("coveragePct", r1(result.overallCoverage * 100))
            put("engineer", meta.engineer)
        }
        put("verdict", result.verdict.name)
        put("sectors", JsonArray(result.sectors.map(::sectorJson)))
        putJsonArray("findings") {
            for (f in result.findings) {
                add(
                    buildJsonObject {
                        put("type", f.type.name)
                        put("severity", f.severity.name)
                        put("detail", JsonObject(f.detail.mapValues { JsonPrimitive(it.value) }))
                    },
                )
            }
        }
        put("config", SvJson.compact.encodeToJsonElement(uz.sectorverify.model.AnalysisConfig.serializer(), meta.config))
        putJsonObject("cleaning") {
            val c = result.cleaning
            put("total", c.total)
            put("noRsrp", c.noRsrp)
            put("stale", c.stale)
            put("noFix", c.noFix)
            put("outOfRange", c.outOfRange)
            put("taMismatch", c.taMismatch)
            put("kept", c.kept)
        }
        put("seed", result.seed)
    }

    private fun sectorJson(s: SectorResult): JsonObject = buildJsonObject {
        val e = s.estimate
        put("label", s.label)
        put("rat", s.key.rat.name)
        put("arfcn", s.key.arfcn)
        put("pci", s.key.pci)
        put("planAzimuth", s.planAzimuthDeg?.let(::r1))
        put("estAzimuth", e?.alphaDeg?.let(::r1))
        put("ci95", e?.let { JsonArray(listOf(JsonPrimitive(r1(it.ciLowDeg)), JsonPrimitive(r1(it.ciHighDeg)))) } ?: JsonNull)
        put("ciHalfDeg", e?.ciHalfDeg?.let(::r1))
        put("azimuthB", e?.alphaBDeg?.let(::r1))
        put("errorDeg", s.errorDeg?.let(::r1))
        put("nSamples", s.nSamples)
        put("nBins", e?.nBins ?: 0)
        put("rmseDb", e?.rmseDb?.let(::r1))
        put("unreliable", e?.unreliable)
        put("coveragePct", r1(s.sectorCoverage * 100))
        put("missingBins", JsonArray(s.missingBins.map(::JsonPrimitive)))
        put("verdict", s.verdict.name)
        put("cause", s.cause.name)
    }

    fun withoutIntegrity(report: JsonObject): JsonObject = JsonObject(report.filterKeys { it != INTEGRITY })

    fun parse(text: String): JsonObject = SvJson.compact.parseToJsonElement(text).jsonObject

    fun toText(report: JsonElement): String = SvJson.pretty.encodeToString(JsonElement.serializer(), report)

    private fun iso(ms: Long) = Instant.ofEpochMilli(ms).toString()

    private fun r1(x: Double): Double = (x * 10).roundToLong() / 10.0
}
