package uz.sectorverify.analysis

import kotlin.math.abs
import kotlin.math.roundToInt
import kotlin.random.Random
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.AzimuthEstimate
import uz.sectorverify.model.CauseCode
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.Finding
import uz.sectorverify.model.FindingType
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Rat
import uz.sectorverify.model.Sector
import uz.sectorverify.model.SectorResult
import uz.sectorverify.model.SessionResult
import uz.sectorverify.model.Severity
import uz.sectorverify.model.SitePlan
import uz.sectorverify.model.Verdict

const val ALGO_VERSION = "1.0.0"

/** Full post-session analysis (§6.1–6.9). Deterministic for a given input and [AnalysisConfig.seed]. */
class SessionAnalyzer(private val config: AnalysisConfig) {
    private val cleaner = Cleaner(config)
    private val binner = Binner(config)
    private val estimator = AzimuthEstimator(config)
    private val coverage = CoverageCalculator(config)
    private val swapDetector = SwapDetector(config)

    private class OverallCoverage(val ok: Boolean, val fraction: Double, val covered: BooleanArray)

    private class Measured(
        val sector: Sector,
        val nSamples: Int,
        val estimate: AzimuthEstimate?,
        val sectorCoverage: SectorCoverage,
        /** Bins covered by any planned cell of the same ARFCN. */
        val arfcnCovered: BooleanArray,
    ) {
        val errorDeg: Double? get() = estimate?.let { Angles.diff(it.alphaDeg, sector.azimuthDeg) }
    }

    fun analyze(
        plan: SitePlan,
        samples: List<CellSample>,
        fixes: List<GnssFix>,
        bootstrapIterations: Int = config.bootstrapIterations,
    ): SessionResult {
        val cleaned = cleaner.clean(plan.lat, plan.lon, samples, fixes)
        val byKey = cleaned.samples.groupBy { it.key }
        val counts = byKey.mapValues { binner.counts(it.value) }
        val plannedKeys = plan.sectors.map { it.key }.toSet()
        val overallCovered = coverage.coveredBins(counts, plannedKeys)
        val overallFraction = coverage.fraction(overallCovered)
        val overallOk = overallFraction >= config.minOverallCoverage

        val measured = plan.sectors.map { s ->
            val own = byKey[s.key].orEmpty()
            val sameArfcn = plannedKeys.filter { it.rat == s.rat && it.arfcn == s.arfcn }
            val arfcnCovered = coverage.coveredBins(counts, sameArfcn)
            Measured(
                sector = s,
                nSamples = own.size,
                estimate = estimator.estimate(binner.bins(own), s.hpbwDeg, bootstrapIterations, randomFor(s.key)),
                sectorCoverage = coverage.sector(s.azimuthDeg, arfcnCovered),
                arfcnCovered = arfcnCovered,
            )
        }

        // No swap search without overall coverage: "qamrov yo'q bo'lsa FAIL berilmaydi".
        val swaps = if (!overallOk) {
            emptyList()
        } else {
            measured.groupBy { it.sector.rat to it.sector.arfcn }.mapNotNull { (_, group) ->
                val entries = group.mapNotNull { m ->
                    m.estimate?.let { SwapEntry(m.sector.key, m.sector.label, m.sector.azimuthDeg, it.alphaDeg) }
                }
                swapDetector.detect(entries)
            }
        }
        val swapTarget: Map<CellKey, String> = swaps.flatMap { it.mapping.entries }.associate { it.key to it.value }

        val baseVerdict = measured.associate { it.sector.key to verdictOf(it, overallOk, null, CauseCode.NONE).first }
        val rotated = rotatedKeys(measured, swapTarget)
        val swapCauses = measured.filter { it.sector.key in swapTarget }
            .associate { it.sector.key to swapCause(it, measured, swapTarget, baseVerdict) }
        val results = measured.map { m ->
            val target = swapTarget[m.sector.key]?.let { label ->
                measured.first {
                    it.sector.label == label &&
                        it.sector.rat == m.sector.rat &&
                        it.sector.arfcn == m.sector.arfcn
                }
            }
            val rotationCause = if (m.sector.key in rotated) CauseCode.ANTENNA_ROTATED else CauseCode.NONE
            val (verdict, cause) = verdictOf(m, overallOk, target, swapCauses[m.sector.key] ?: rotationCause)
            SectorResult(
                key = m.sector.key,
                label = m.sector.label,
                planAzimuthDeg = m.sector.azimuthDeg,
                estimate = m.estimate,
                errorDeg = m.errorDeg,
                nSamples = m.nSamples,
                sectorCoverage = m.sectorCoverage.fraction,
                missingBins = m.sectorCoverage.missingBins,
                verdict = verdict,
                cause = cause,
            )
        }

        val unexpected = unexpectedCells(plan, plannedKeys, byKey)
        val findings =
            buildFindings(plan, results, swaps, swapCauses, OverallCoverage(overallOk, overallFraction, overallCovered), unexpected)
        val sessionVerdict = sessionVerdict(results, findings)
        return SessionResult(
            siteCode = plan.code,
            verdict = sessionVerdict,
            sectors = results + unexpected,
            findings = findings,
            overallCoverage = overallFraction,
            coveredBins = overallCovered.toList(),
            cleaning = cleaned.stats,
            seed = config.seed,
            algoVersion = ALGO_VERSION,
        )
    }

    /**
     * §6.9 with priority INCONCLUSIVE > FAIL > WARN > PASS; PCI_MISSING only when overall coverage is sufficient.
     * A swapped cell radiates into [swapTarget]'s sector, so its coverage is checked around that plan azimuth (ADR-008).
     */
    private fun verdictOf(m: Measured, overallOk: Boolean, swapTarget: Measured?, cause: CauseCode): Pair<Verdict, CauseCode> {
        val est = m.estimate
        val err = m.errorDeg?.let { abs(it) }
        val swapped = swapTarget != null
        val windowCoverage = swapTarget?.let { coverage.sector(it.sector.azimuthDeg, m.arfcnCovered).fraction } ?: m.sectorCoverage.fraction
        return when {
            !overallOk -> Verdict.INCONCLUSIVE to CauseCode.LOW_COVERAGE
            m.nSamples < config.minSamplesPresent -> Verdict.FAIL to CauseCode.PCI_MISSING
            est == null || err == null || windowCoverage < config.minSectorCoverage ->
                Verdict.INCONCLUSIVE to CauseCode.LOW_COVERAGE
            est.unreliable || est.ciHalfDeg > config.warnMaxCiHalfDeg -> Verdict.INCONCLUSIVE to cause.takeIf { swapped }.orNone()
            swapped -> Verdict.FAIL to cause
            err > config.warnMaxErrDeg -> Verdict.FAIL to CauseCode.NONE
            err > config.passMaxErrDeg || est.ciHalfDeg > config.passMaxCiHalfDeg -> Verdict.WARN to cause
            else -> Verdict.PASS to CauseCode.NONE
        }
    }

    private fun CauseCode?.orNone() = this ?: CauseCode.NONE

    /** §6.8 swap cause, comparing the same sector label across ARFCNs. */
    private fun swapCause(
        m: Measured,
        all: List<Measured>,
        swapTarget: Map<CellKey, String>,
        baseVerdict: Map<CellKey, Verdict>,
    ): CauseCode {
        val others = all.filter { it.sector.label == m.sector.label && it.sector.key != m.sector.key }
        if (others.isEmpty()) return CauseCode.CELL_CONFIG_SWAP
        val target = swapTarget[m.sector.key]
        return when {
            others.all { it.sector.key !in swapTarget && baseVerdict[it.sector.key] == Verdict.PASS } -> CauseCode.BAND_PORT_SWAP
            others.all { swapTarget[it.sector.key] == target } -> CauseCode.CELL_CONFIG_SWAP
            else -> CauseCode.BAND_PORT_SWAP
        }
    }

    /** §6.8 antenna rotation: same-sign 20–45° offset on every estimated ARFCN of a label, spread ≤ 10°. */
    private fun rotatedKeys(all: List<Measured>, swapTarget: Map<CellKey, String>): Set<CellKey> =
        all.filter { it.estimate != null && it.sector.key !in swapTarget }
            .groupBy { it.sector.label }
            .values
            .filter { group ->
                val errs = group.mapNotNull { it.errorDeg }
                errs.isNotEmpty() &&
                    errs.all { abs(it) > config.rotationMinDeg && abs(it) <= config.rotationMaxDeg } &&
                    (errs.all { it > 0 } || errs.all { it < 0 }) &&
                    errs.max() - errs.min() <= config.rotationMaxSpreadDeg
            }
            .flatten()
            .map { it.sector.key }
            .toSet()

    /** §6.8 PCI_UNEXPECTED: an unplanned cell on a planned ARFCN, registered in ≥ 30 % of samples within 300 m. */
    private fun unexpectedCells(plan: SitePlan, plannedKeys: Set<CellKey>, byKey: Map<CellKey, List<CleanSample>>): List<SectorResult> {
        val plannedArfcns = plan.arfcns.toSet()
        return byKey.filterKeys { it !in plannedKeys && (it.rat to it.arfcn) in plannedArfcns }
            .mapNotNull { (key, list) ->
                val near = list.filter { it.distanceM <= config.unexpectedMaxDistM }
                val regFrac = if (near.isEmpty()) 0.0 else near.count { it.registered }.toDouble() / near.size
                if (near.size < config.minSamplesPresent || regFrac < config.unexpectedMinRegisteredFrac) return@mapNotNull null
                val est = estimator.estimate(binner.bins(list), Sector.DEFAULT_HPBW_DEG, 0, randomFor(key))
                SectorResult(key, null, null, est, null, list.size, 0.0, emptyList(), Verdict.INCONCLUSIVE, CauseCode.PCI_UNEXPECTED)
            }
            .sortedBy { it.key }
    }

    private fun buildFindings(
        plan: SitePlan,
        results: List<SectorResult>,
        swaps: List<SwapResult>,
        swapCauses: Map<CellKey, CauseCode>,
        overall: OverallCoverage,
        unexpected: List<SectorResult>,
    ): List<Finding> = buildList {
        val overallOk = overall.ok
        if (!overallOk) {
            val detail = mapOf("scope" to "site", "coveragePct" to pct(overall.fraction), "missingBins" to missingBins(overall.covered))
            add(Finding(FindingType.LOW_COVERAGE, Severity.WARN, detail))
        }
        for (swap in swaps) {
            val first = swap.mapping.keys.first()
            val detail = linkedMapOf("rat" to first.rat.name, "arfcn" to first.arfcn.toString())
            detail["cause"] = swapCauses.getValue(first).name
            swap.mapping.toSortedMap().forEach { (k, label) ->
                detail["pci.${k.pci}"] = label
            }
            detail["mapping"] = swap.mapping.toSortedMap().entries.joinToString(", ") { (k, label) ->
                "${k.pci}(${plan.sectorFor(k)?.label}) → $label"
            }
            add(Finding(FindingType.SWAP, Severity.CRITICAL, detail))
        }
        for (r in results) {
            when {
                r.cause == CauseCode.PCI_MISSING -> add(Finding(FindingType.PCI_MISSING, Severity.CRITICAL, r.describe()))
                r.cause == CauseCode.ANTENNA_ROTATED -> add(Finding(FindingType.ANTENNA_ROTATED, Severity.WARN, r.describe()))
                overallOk && r.cause == CauseCode.LOW_COVERAGE ->
                    add(Finding(FindingType.LOW_COVERAGE, Severity.WARN, r.describe() + ("missingBins" to r.missingBins.joinToString(" "))))
            }
            if (r.estimate?.unreliable == true && r.cause != CauseCode.LOW_COVERAGE && overallOk) {
                add(Finding(FindingType.UNRELIABLE_ESTIMATE, Severity.WARN, r.describe()))
            }
        }
        for (u in unexpected) add(Finding(FindingType.PCI_UNEXPECTED, Severity.INFO, u.describe()))
    }

    private fun SectorResult.describe(): Map<String, String> = buildMap {
        label?.let { put("label", it) }
        put("rat", key.rat.name)
        put("arfcn", key.arfcn.toString())
        put("pci", key.pci.toString())
        put("nSamples", nSamples.toString())
        errorDeg?.let { put("errorDeg", it.roundToInt().toString()) }
        estimate?.let {
            put("alphaDeg", it.alphaDeg.roundToInt().toString())
            put("alphaBDeg", it.alphaBDeg.roundToInt().toString())
        }
    }

    private fun sessionVerdict(results: List<SectorResult>, findings: List<Finding>): Verdict {
        val v = results.map { it.verdict }
        return when {
            Verdict.FAIL in v || findings.any { it.severity == Severity.CRITICAL } -> Verdict.FAIL
            Verdict.INCONCLUSIVE in v -> Verdict.INCONCLUSIVE
            Verdict.WARN in v -> Verdict.WARN
            else -> Verdict.PASS
        }
    }

    private fun pct(f: Double) = (f * 100).roundToInt().toString()

    private fun missingBins(covered: BooleanArray) = covered.indices.filterNot { covered[it] }.joinToString(" ")

    /** Stable per-cell random stream (independent of map iteration order). */
    private fun randomFor(key: CellKey): Random = Random(config.seed xor stableHash(key))

    companion object {
        private const val HASH_RAT = 1_000_003L
        private const val HASH_ARFCN = 10_007L
        private const val HASH_NR = 7L

        fun stableHash(key: CellKey): Long =
            key.rat.ordinal * HASH_RAT + key.arfcn * HASH_ARFCN + key.pci + if (key.rat == Rat.NR) HASH_NR else 0L
    }
}
