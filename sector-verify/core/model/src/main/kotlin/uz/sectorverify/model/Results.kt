package uz.sectorverify.model

import kotlinx.serialization.Serializable

/**
 * Azimuth estimate of one cell. [alphaDeg] — method A (pattern fit), [alphaBDeg] — method B
 * (power-weighted centroid). [ciLowDeg]/[ciHighDeg] are absolute bearings (0..360) of the 95 % bootstrap
 * interval; [ciHalfDeg] = max(|lo|, |hi|) of the offsets from [alphaDeg].
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

/** [detail] is a flat string map so it round-trips through `finding.detail_json` and report.json. */
@Serializable
data class Finding(
    val type: FindingType,
    val severity: Severity,
    val detail: Map<String, String> = emptyMap(),
)

@Serializable
data class SectorResult(
    val key: CellKey,
    /** Planned sector label; null for a cell that is not in the plan (PCI_UNEXPECTED). */
    val label: String?,
    val planAzimuthDeg: Double?,
    val estimate: AzimuthEstimate?,
    /** Signed estimate − plan in [-180, 180). */
    val errorDeg: Double?,
    val nSamples: Int,
    /** Fraction of the 18 bins in plan ± 90° that have coverage on this ARFCN. */
    val sectorCoverage: Double,
    /** Bin indices (0..35) in plan ± 90° without coverage — shown in UI as missing directions. */
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
    /** Fraction of 36 bins with ≥ 3 samples of any planned cell. */
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
