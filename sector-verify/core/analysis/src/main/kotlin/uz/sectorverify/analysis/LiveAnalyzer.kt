package uz.sectorverify.analysis

import kotlin.math.abs
import kotlin.random.Random
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Sector
import uz.sectorverify.model.SitePlan
import uz.sectorverify.model.Verdict

data class LiveCell(
    val key: CellKey,
    val label: String?,
    val planAzimuthDeg: Double?,
    val alphaDeg: Double?,
    val alphaBDeg: Double?,
    val lastRsrp: Double?,
    val nSamples: Int,
    val nBins: Int,
    /** Preliminary status from |δ| only: PASS ≤ 20°, WARN ≤ 45°, FAIL beyond, INCONCLUSIVE without estimate. */
    val status: Verdict,
)

data class LiveSnapshot(
    val coveredBins: List<Boolean>,
    val overallCoverage: Double,
    val cells: List<LiveCell>,
    val samplesKept: Int,
    /** Overall coverage reached and every planned cell has an estimate — "Natija tayyor". */
    val ready: Boolean,
)

/** §6.10: method B and method A without bootstrap on everything collected so far. */
class LiveAnalyzer(private val config: AnalysisConfig) {
    private val cleaner = Cleaner(config)
    private val binner = Binner(config)
    private val estimator = AzimuthEstimator(config)
    private val coverage = CoverageCalculator(config)

    fun snapshot(plan: SitePlan, samples: List<CellSample>, fixes: List<GnssFix>): LiveSnapshot {
        val cleaned = cleaner.clean(plan.lat, plan.lon, samples, fixes).samples
        val byKey = cleaned.groupBy { it.key }
        val planned = plan.sectors.associateBy { it.key }
        val counts = byKey.mapValues { binner.counts(it.value) }
        val covered = coverage.coveredBins(counts, planned.keys)
        val keys = (planned.keys + byKey.keys).sorted()
        val cells = keys.map { key ->
            val sector = planned[key]
            val list = byKey[key].orEmpty()
            val bins = binner.bins(list)
            val est = estimator.estimate(bins, sector?.hpbwDeg ?: Sector.DEFAULT_HPBW_DEG, 0, Random(config.seed))
            val err = if (est != null && sector != null) abs(Angles.diff(est.alphaDeg, sector.azimuthDeg)) else null
            LiveCell(
                key = key,
                label = sector?.label,
                planAzimuthDeg = sector?.azimuthDeg,
                alphaDeg = est?.alphaDeg,
                alphaBDeg = est?.alphaBDeg,
                lastRsrp = list.maxByOrNull { it.tNanos }?.rsrp,
                nSamples = list.size,
                nBins = bins.size,
                status = when {
                    err == null -> Verdict.INCONCLUSIVE
                    err <= config.passMaxErrDeg -> Verdict.PASS
                    err <= config.warnMaxErrDeg -> Verdict.WARN
                    else -> Verdict.FAIL
                },
            )
        }
        val fraction = coverage.fraction(covered)
        val ready = fraction >= config.minOverallCoverage && cells.filter { it.key in planned }.all { it.alphaDeg != null }
        return LiveSnapshot(covered.toList(), fraction, cells, cleaned.size, ready)
    }
}
