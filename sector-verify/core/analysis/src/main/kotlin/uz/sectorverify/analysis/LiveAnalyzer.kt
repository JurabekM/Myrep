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
    /** Faqat |δ| bo'yicha dastlabki holat: PASS ≤ 20°, WARN ≤ 45°, undan katta — FAIL, baho bo'lmasa — INCONCLUSIVE. */
    val status: Verdict,
)

data class LiveSnapshot(
    val coveredBins: List<Boolean>,
    val overallCoverage: Double,
    val cells: List<LiveCell>,
    val samplesKept: Int,
    /** Umumiy qamrovga erishildi va har bir rejalashtirilgan yacheykaning bahosi bor — "Natija tayyor". */
    val ready: Boolean,
)

/**
 * §6.10: hozirgacha yig'ilgan hamma narsa bo'yicha B usuli va bootstrap'siz A usuli.
 *
 * Inkremental: [snapshot] sessiya davomida namunalar ro'yxati faqat oxiriga qo'shilib o'sishini kutadi (o'lchov dvigateli
 * uni shunday beradi). Namunaning GNSS oralig'i endi o'zgara olmaydigan bo'lishi bilan u bir marta va butunlay tozalanadi;
 * har chaqiruvda faqat oxirgi bir necha soniya qayta tozalanadi. Boshqa har qanday ro'yxat (qisqaroq, boshqa sessiya) keshni
 * nolga qaytaradi, shuning uchun natija doim hammasini noldan tozalash natijasi bilan bir xil bo'ladi.
 */
class LiveAnalyzer(private val config: AnalysisConfig) {
    private val cleaner = Cleaner(config)
    private val binner = Binner(config)
    private val estimator = AzimuthEstimator(config)
    private val coverage = CoverageCalculator(config)
    private val maxGapNanos = config.maxFixGapMs * NANOS_PER_MS

    private var siteCode: String? = null
    private var firstSample: CellSample? = null
    private var consumed = 0
    private val final = HashMap<CellKey, MutableList<CleanSample>>()

    fun snapshot(plan: SitePlan, samples: List<CellSample>, fixes: List<GnssFix>): LiveSnapshot {
        if (!continues(plan, samples)) reset(plan)
        firstSample = samples.firstOrNull()
        val good = fixes.filter { f -> f.accM <= config.maxAccuracyM && (f.speedMps?.let { it <= config.maxSpeedMps } ?: true) }
        val lastGoodFix = good.maxOfOrNull { it.tNanos } ?: Long.MIN_VALUE
        val latest = maxOf(fixes.maxOfOrNull { it.tNanos } ?: Long.MIN_VALUE, samples.lastOrNull()?.tNanos ?: Long.MIN_VALUE)
        // Keyinroq yaxshi fix paydo bo'lgach yoki kelajakdagi hech bir fix undan maxFixGap ichida bo'la olmaganda — yakuniy.
        var end = consumed
        while (end < samples.size && (samples[end].tNanos <= lastGoodFix || latest - samples[end].tNanos > maxGapNanos)) end++
        if (end > consumed) {
            for (c in cleaner.clean(plan.lat, plan.lon, samples.subList(consumed, end), fixes).samples) {
                final.getOrPut(c.key) { ArrayList() } += c
            }
            consumed = end
        }
        val pending = cleaner.clean(plan.lat, plan.lon, samples.subList(consumed, samples.size), fixes).samples.groupBy { it.key }
        val byKey = (final.keys + pending.keys).associateWith { k -> final[k].orEmpty() + pending[k].orEmpty() }
        return build(plan, byKey)
    }

    /** [samples] shu saytning oldingi chaqiruvida ko'rilgan ro'yxatni davom ettirsa true. */
    private fun continues(plan: SitePlan, samples: List<CellSample>): Boolean =
        plan.code == siteCode && samples.size >= consumed && (consumed == 0 || samples.first() == firstSample)

    private fun reset(plan: SitePlan) {
        siteCode = plan.code
        consumed = 0
        final.clear()
    }

    private fun build(plan: SitePlan, byKey: Map<CellKey, List<CleanSample>>): LiveSnapshot {
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
        return LiveSnapshot(covered.toList(), fraction, cells, byKey.values.sumOf { it.size }, ready)
    }

    private companion object {
        const val NANOS_PER_MS = 1_000_000L
    }
}
