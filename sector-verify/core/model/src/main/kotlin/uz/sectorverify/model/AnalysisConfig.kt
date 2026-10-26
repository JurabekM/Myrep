package uz.sectorverify.model

import kotlinx.serialization.Serializable

@Serializable
enum class AnalysisPreset {
    URBAN,
    SUBURBAN,
    RURAL,
}

/**
 * Every numeric threshold of the analysis (prompt §6). A full copy is stored with each session
 * (`session.config_json`) so a result can always be reproduced.
 */
@Serializable
data class AnalysisConfig(
    val preset: AnalysisPreset = AnalysisPreset.SUBURBAN,
    // 6.1 cleaning
    val maxSampleAgeMs: Long = 3000,
    val maxFixGapMs: Long = 2000,
    val maxAccuracyM: Double = 15.0,
    val maxSpeedMps: Double = 8.0,
    val rMinM: Double = 100.0,
    val rMaxM: Double = 1500.0,
    val taStepM: Double = 78.12,
    val taToleranceSteps: Double = 2.0,
    // 6.2 normalisation and binning
    val pathLossExponent: Double = 3.5,
    val dRefM: Double = 300.0,
    val binDeg: Int = 10,
    val minPerBin: Int = 3,
    // 6.3 method A
    val patternCoef: Double = 12.0,
    val patternMaxAttDb: Double = 30.0,
    val alphaStepDeg: Double = 1.0,
    val minBinsForFit: Int = 6,
    // 6.4 bootstrap
    val bootstrapIterations: Int = 200,
    val ciLowPercentile: Double = 2.5,
    val ciHighPercentile: Double = 97.5,
    // 6.5 method B
    val unreliableDiffDeg: Double = 30.0,
    // 6.6 coverage
    val minOverallCoverage: Double = 0.70,
    val minSectorCoverage: Double = 0.60,
    val sectorHalfWidthDeg: Double = 90.0,
    val minSamplesPerCoverageBin: Int = 3,
    // 6.7 swap
    val swapMaxErrDeg: Double = 30.0,
    val swapGainFactor: Double = 4.0,
    val swapGainOffset: Double = 1.0,
    val swapMaxSectors: Int = 6,
    // 6.8 causes
    val rotationMinDeg: Double = 20.0,
    val rotationMaxDeg: Double = 45.0,
    val rotationMaxSpreadDeg: Double = 10.0,
    val minSamplesPresent: Int = 20,
    val unexpectedMaxDistM: Double = 300.0,
    val unexpectedMinRegisteredFrac: Double = 0.30,
    // 6.9 verdict
    val passMaxErrDeg: Double = 20.0,
    val passMaxCiHalfDeg: Double = 20.0,
    val warnMaxErrDeg: Double = 45.0,
    val warnMaxCiHalfDeg: Double = 35.0,
    // 6.10 live
    val liveIntervalMs: Long = 5000,
    // pre-check (§8.1): minimal CellInfo update rate of the device (AC-05)
    val minDeviceRateHz: Double = 0.5,
    // reproducibility
    val seed: Long = DEFAULT_SEED,
) {
    val nBins: Int get() = FULL_CIRCLE / binDeg

    /** Returns human-readable problems; empty when the config is usable. */
    fun validate(): List<String> = buildList {
        if (binDeg <= 0 || FULL_CIRCLE % binDeg != 0) add("binDeg must divide 360")
        if (alphaStepDeg <= 0.0) add("alphaStepDeg must be > 0")
        if (rMinM < 0 || rMaxM <= rMinM) add("rMinM < rMaxM required")
        if (minPerBin < 1) add("minPerBin must be >= 1")
        if (minBinsForFit < 2) add("minBinsForFit must be >= 2")
        if (bootstrapIterations < 0) add("bootstrapIterations must be >= 0")
        if (ciLowPercentile !in 0.0..ciHighPercentile || ciHighPercentile > 100.0) add("bad CI percentiles")
        if (minOverallCoverage !in 0.0..1.0 || minSectorCoverage !in 0.0..1.0) add("coverage must be in 0..1")
        if (swapMaxSectors !in 2..MAX_SWAP_SECTORS) add("swapMaxSectors must be in 2..8")
        if (patternMaxAttDb <= 0 || patternCoef <= 0) add("pattern parameters must be > 0")
        if (dRefM <= 0) add("dRefM must be > 0")
    }

    companion object {
        const val FULL_CIRCLE = 360
        const val DEFAULT_SEED = 20_261_026L
        const val MAX_SWAP_SECTORS = 8
        const val URBAN_R_MAX_M = 600.0
        const val RURAL_PATH_LOSS_EXPONENT = 3.0

        fun forPreset(preset: AnalysisPreset): AnalysisConfig = when (preset) {
            AnalysisPreset.URBAN -> AnalysisConfig(preset = preset, rMaxM = URBAN_R_MAX_M)
            AnalysisPreset.SUBURBAN -> AnalysisConfig(preset = preset)
            AnalysisPreset.RURAL -> AnalysisConfig(preset = preset, pathLossExponent = RURAL_PATH_LOSS_EXPONENT)
        }
    }
}
