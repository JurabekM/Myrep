package uz.sectorverify.format

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionStatus

/** session.json: metadata plus the full [AnalysisConfig] used (reproducibility, §5.2). */
@Serializable
data class SessionMeta(
    val schema: String = SCHEMA,
    val id: String,
    val siteCode: String,
    val mode: SessionMode,
    val startedAtUtcMs: Long,
    val endedAtUtcMs: Long? = null,
    val deviceModel: String,
    val apiLevel: Int,
    val baseband: String? = null,
    val appVersion: String,
    val algoVersion: String,
    val measuredRateHz: Double? = null,
    val status: SessionStatus,
    val engineer: String? = null,
    val config: AnalysisConfig,
) {
    companion object {
        const val SCHEMA = "sector-verify/session/v1"
    }
}

object SvJson {
    val compact: Json = Json {
        encodeDefaults = true
        ignoreUnknownKeys = true
    }
    val pretty: Json = Json {
        encodeDefaults = true
        ignoreUnknownKeys = true
        prettyPrint = true
    }

    /** Parses a config JSON (calibration output); unknown keys ignored, missing keys take defaults. */
    fun parseConfig(text: String): AnalysisConfig = compact.decodeFromString(AnalysisConfig.serializer(), text)

    fun configToJson(config: AnalysisConfig): String = pretty.encodeToString(AnalysisConfig.serializer(), config)
}
