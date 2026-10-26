package uz.sectorverify.model

import kotlinx.serialization.Serializable

/**
 * Bitta yacheykaning azimut bahosi. [alphaDeg] — A usuli (pattern moslash), [alphaBDeg] — B usuli
 * (quvvat bo'yicha vaznlangan markaz). [ciLowDeg]/[ciHighDeg] — 95 % bootstrap intervalining absolyut yo'nalishlari
 * (0..360); [ciHalfDeg] = [alphaDeg] dan og'ishlarning max(|lo|, |hi|) qiymati.
 */
@Serializable
data class AzimuthEstimate(
    val alphaDeg: Double,
    val ciLowDeg: Double,
    val ciHighDeg: Double,
    val ciHalfDeg: Double,
    val alphaBDeg: Double,
    val rmseDb: Double,
    val nSamples: Int,
    val nBins: Int,
    val unreliable: Boolean,
)

@Serializable
enum class Verdict {
    PASS,
    WARN,
    FAIL,
    INCONCLUSIVE,
}

@Serializable
enum class CauseCode {
    NONE,
    BAND_PORT_SWAP,
    CELL_CONFIG_SWAP,
    ANTENNA_ROTATED,
    PCI_MISSING,
    PCI_UNEXPECTED,
    LOW_COVERAGE,
}

@Serializable
enum class Severity {
    INFO,
    WARN,
    CRITICAL,
}

@Serializable
enum class FindingType {
    SWAP,
    PCI_MISSING,
    PCI_UNEXPECTED,
    ANTENNA_ROTATED,
    LOW_COVERAGE,
    UNRELIABLE_ESTIMATE,
}

/** [detail] — tekis string map, shuning uchun `finding.detail_json` va report.json orqali o'zgarishsiz o'tadi. */
@Serializable
data class Finding(
    val type: FindingType,
    val severity: Severity,
    val detail: Map<String, String> = emptyMap(),
)

@Serializable
data class SectorResult(
    val key: CellKey,
    /** Rejadagi sektor yorlig'i; rejada yo'q yacheyka uchun null (PCI_UNEXPECTED). */
    val label: String?,
    val planAzimuthDeg: Double?,
    val estimate: AzimuthEstimate?,
    /** Ishorali baho − plan, [-180, 180) oralig'ida. */
    val errorDeg: Double?,
    val nSamples: Int,
    /** plan ± 90° dagi 18 ta bindan shu ARFCN'da qamrovga ega bo'lganlari ulushi. */
    val sectorCoverage: Double,
    /** plan ± 90° dagi qamrovsiz bin indekslari (0..35) — UI'da yetishmayotgan yo'nalishlar sifatida ko'rsatiladi. */
    val missingBins: List<Int>,
    val verdict: Verdict,
    val cause: CauseCode,
)

@Serializable
data class CleaningStats(
    val total: Int,
    val noRsrp: Int,
    val stale: Int,
    val noFix: Int,
    val outOfRange: Int,
    val taMismatch: Int,
    val kept: Int,
)

@Serializable
data class SessionResult(
    val siteCode: String,
    val verdict: Verdict,
    val sectors: List<SectorResult>,
    val findings: List<Finding>,
    /** 36 ta bindan istalgan rejalashtirilgan yacheykaning ≥ 3 ta namunasi bor binlar ulushi. */
    val overallCoverage: Double,
    val coveredBins: List<Boolean>,
    val cleaning: CleaningStats,
    val seed: Long,
    val algoVersion: String,
)

@Serializable
enum class SessionMode {
    FULL,
    RECHECK,
}

@Serializable
enum class SessionStatus {
    RUNNING,
    DONE,
    ABORTED,
}
