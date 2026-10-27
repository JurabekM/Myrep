package uz.sectorverify.replay

import java.io.File
import kotlin.math.roundToInt
import uz.sectorverify.analysis.SessionAnalyzer
import uz.sectorverify.format.SessionExport
import uz.sectorverify.format.SessionZip
import uz.sectorverify.format.SvJson
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CauseCode
import uz.sectorverify.model.FindingType
import uz.sectorverify.model.Verdict

data class Metrics(
    val swapCells: Int,
    val swapDetected: Int,
    val healthyCells: Int,
    val falseFail: Int,
    val healthyPass: Int,
    val medianErrDeg: Double,
) {
    /** AC-08: aniqlangan tasdiqlangan swap'lar ulushi (pilotda swap bo'lmasa 1.0). */
    val detection: Double get() = if (swapCells == 0) 1.0 else swapDetected.toDouble() / swapCells
    val falseFailRate: Double get() = if (healthyCells == 0) 0.0 else falseFail.toDouble() / healthyCells
    val passRate: Double get() = if (healthyCells == 0) 0.0 else healthyPass.toDouble() / healthyCells
}

data class Candidate(val config: AnalysisConfig, val metrics: Metrics, val changes: Int)

data class CalibrationOutcome(val best: Candidate, val ranked: List<Candidate>, val baseline: Candidate, val feasible: Boolean)

/** `calibrate <dir-of-zips> <ground_truth.csv> [--out dir] [--quick]` (§9, 4-bosqich). */
object Calibrate {
    const val MAX_FALSE_FAIL = 0.03
    private const val GRID_BOOTSTRAP = 50
    private const val TOP = 10

    private val SWAP_CAUSES = setOf(CauseCode.CELL_CONFIG_SWAP, CauseCode.BAND_PORT_SWAP)

    /** Qidiriladigan qiymatlar (§9, 4-bosqich: chegaralar va n). Tezkor grid asosiy xulosa chegaralarini saqlaydi. */
    private val GRID_N = listOf(3.0, 3.5, 4.0)
    private val QUICK_N = listOf(3.0, 3.5)
    private val GRID_PASS = listOf(15.0, 20.0, 25.0)
    private val GRID_WARN = listOf(40.0, 45.0, 50.0)
    private val GRID_SWAP = listOf(25.0, 30.0, 35.0)
    private val QUICK_SWAP = listOf(30.0, 35.0)
    private val GRID_SECTOR_COV = listOf(0.5, 0.6)

    fun grid(base: AnalysisConfig, quick: Boolean): List<AnalysisConfig> {
        val ns = if (quick) QUICK_N else GRID_N
        val pass = if (quick) listOf(base.passMaxErrDeg) else GRID_PASS
        val warn = if (quick) listOf(base.warnMaxErrDeg) else GRID_WARN
        val swap = if (quick) QUICK_SWAP else GRID_SWAP
        val cov = if (quick) listOf(base.minSectorCoverage) else GRID_SECTOR_COV
        val combos = ns.flatMap { n ->
            pass.flatMap { p -> warn.flatMap { w -> swap.flatMap { s -> cov.map { c -> Combo(n, p, w, s, c) } } } }
        }
        return combos.filter { it.pass < it.warn }.map {
            base.copy(
                pathLossExponent = it.n,
                passMaxErrDeg = it.pass,
                warnMaxErrDeg = it.warn,
                swapMaxErrDeg = it.swap,
                minSectorCoverage = it.cov,
            )
        }
    }

    private data class Combo(val n: Double, val pass: Double, val warn: Double, val swap: Double, val cov: Double)

    /** Grid qidirayotgan parametrlarni [from] dan oladi; qolganlari (preset, rMax, ...) sessiyaning o'zinikicha qoladi. */
    fun AnalysisConfig.withSearched(from: AnalysisConfig) = copy(
        pathLossExponent = from.pathLossExponent,
        passMaxErrDeg = from.passMaxErrDeg,
        warnMaxErrDeg = from.warnMaxErrDeg,
        swapMaxErrDeg = from.swapMaxErrDeg,
        minSectorCoverage = from.minSectorCoverage,
        bootstrapIterations = from.bootstrapIterations,
    )

    /** Har sessiya o'zi yozilgan config bilan, faqat qidirilayotgan parametrlari [config] dan olinib tahlil qilinadi. */
    fun evaluate(config: AnalysisConfig, sessions: List<SessionExport>, truth: List<TruthRow>): Metrics {
        val byKey = truth.associateBy { it.siteCode to it.key }
        var swapCells = 0
        var swapDetected = 0
        var healthy = 0
        var falseFail = 0
        var healthyPass = 0
        val errors = ArrayList<Double>()
        for (e in sessions) {
            val r = SessionAnalyzer(e.meta.config.withSearched(config)).analyze(e.plan, e.samples, e.fixes)
            for (s in r.sectors.filter { it.label != null }) {
                val t = byKey[e.plan.code to s.key] ?: continue
                if (t.isSwap) {
                    swapCells++
                    // AC-01 bilan bir xil ta'rif: yacheyka o'z ARFCN'idagi CRITICAL SWAP topilmasida uchraydi.
                    val found = r.findings.any {
                        it.type == FindingType.SWAP &&
                            it.detail["rat"] == s.key.rat.name &&
                            it.detail["arfcn"] == s.key.arfcn.toString() &&
                            it.detail["pci.${s.key.pci}"] != null
                    }
                    if (found || s.cause in SWAP_CAUSES) swapDetected++
                }
                if (!t.hasFault) {
                    healthy++
                    if (s.verdict == Verdict.FAIL) falseFail++
                    if (s.verdict == Verdict.PASS) healthyPass++
                }
                val est = s.estimate
                if (est != null && t.trueAzimuthDeg != null) errors += absErr(est.alphaDeg, t.trueAzimuthDeg)
            }
        }
        errors.sort()
        val median = if (errors.isEmpty()) Double.NaN else errors[errors.size / 2]
        return Metrics(swapCells, swapDetected, healthy, falseFail, healthyPass, median)
    }

    private fun changes(c: AnalysisConfig, base: AnalysisConfig) = listOf(
        c.pathLossExponent != base.pathLossExponent,
        c.passMaxErrDeg != base.passMaxErrDeg,
        c.warnMaxErrDeg != base.warnMaxErrDeg,
        c.swapMaxErrDeg != base.swapMaxErrDeg,
        c.minSectorCoverage != base.minSectorCoverage,
    ).count { it }

    /** Maqbul = noto'g'ri FAIL ≤ 3 %; keyin maks. aniqlash, min. noto'g'ri FAIL, maks. PASS, [base] dan eng kam farq. */
    fun rank(cands: List<Candidate>): List<Candidate> = cands.sortedWith(
        compareByDescending<Candidate> { it.metrics.falseFailRate <= MAX_FALSE_FAIL }
            .thenByDescending { it.metrics.detection }
            .thenBy { it.metrics.falseFailRate }
            .thenByDescending { it.metrics.passRate }
            .thenBy { it.changes },
    )

    fun run(
        dir: File,
        truthFile: File,
        out: File,
        quick: Boolean,
        base: AnalysisConfig? = null,
        print: (String) -> Unit,
    ): CalibrationOutcome {
        val zips = dir.listFiles { f -> f.extension.equals("zip", ignoreCase = true) }.orEmpty().sortedBy { it.name }
        require(zips.isNotEmpty()) { "${dir.path} ichida ZIP yo'q" }
        val sessions = zips.map { z -> z.inputStream().use { SessionZip.read(it) } }
        val truth = GroundTruth.parse(truthFile.readText())
        print("${sessions.size} ta sessiya, ground truth: ${truth.size} cell")
        // Tavsiya eng ko'p ishlatilgan sessiya configi ustiga quriladi (preset va rMax saqlanadi).
        val base = base ?: sessions.groupingBy { it.meta.config }.eachCount().maxBy { it.value }.key
        print("Asos config: ${base.preset}, rMax ${base.rMaxM} m")
        val gridBase = base.copy(bootstrapIterations = GRID_BOOTSTRAP)
        val configs = grid(gridBase, quick)
        print("Grid: ${configs.size} ta konfiguratsiya…")
        val cands = configs.parallelStream()
            .map { c -> Candidate(c, evaluate(c, sessions, truth), changes(c, gridBase)) }
            .toList()
        val ranked = rank(cands)
        val chosen = ranked.first()
        // Asosiy config'ning to'liq bootstrap'i bilan yakuniy raqamlar.
        val finalConfig = chosen.config.copy(bootstrapIterations = base.bootstrapIterations)
        val best = Candidate(finalConfig, evaluate(finalConfig, sessions, truth), chosen.changes)
        val baseline = Candidate(base, evaluate(base, sessions, truth), 0)
        val outcome = CalibrationOutcome(best, ranked, baseline, best.metrics.falseFailRate <= MAX_FALSE_FAIL)
        out.mkdirs()
        File(out, "recommended-config.json").writeText(SvJson.configToJson(finalConfig))
        File(out, "calibration-report.md").writeText(report(outcome, sessions.size, truth.size))
        print("Tavsiya: ${File(out, "recommended-config.json").path}")
        print(
            "AC-08 aniqlash ${pct(best.metrics.detection)} · noto'g'ri FAIL ${pct(best.metrics.falseFailRate)} · " +
                "mediana xato ${"%.1f".format(best.metrics.medianErrDeg)}°",
        )
        if (!outcome.feasible) print("OGOHLANTIRISH: hech bir konfiguratsiyada noto'g'ri FAIL ≤ 3% bo'lmadi")
        return outcome
    }

    fun report(o: CalibrationOutcome, nSessions: Int, nTruth: Int): String = buildString {
        appendLine("# Kalibrlash hisoboti")
        appendLine()
        appendLine("Sessiyalar: $nSessions · ground truth cell'lar: $nTruth · grid: ${o.ranked.size} konfiguratsiya")
        appendLine()
        appendLine("| | n | PASS ≤ | WARN ≤ | swapErr | sektor qamrovi | AC-08 aniqlash | noto'g'ri FAIL | sog' PASS | mediana xato |")
        appendLine("|---|---|---|---|---|---|---|---|---|---|")
        fun row(label: String, c: Candidate) {
            val k = c.config
            val m = c.metrics
            val cells = listOf(
                label, k.pathLossExponent, k.passMaxErrDeg, k.warnMaxErrDeg, k.swapMaxErrDeg, k.minSectorCoverage,
                "${pct(m.detection)} (${m.swapDetected}/${m.swapCells})",
                "${pct(m.falseFailRate)} (${m.falseFail}/${m.healthyCells})",
                pct(m.passRate),
                "%.1f°".format(m.medianErrDeg),
            )
            appendLine(cells.joinToString(" | ", "| ", " |"))
        }
        row("**tavsiya**", o.best)
        row("joriy standart", o.baseline)
        o.ranked.take(TOP).forEachIndexed { i, c -> row("#${i + 1}", c) }
        appendLine()
        val verdict = if (o.feasible) "Shart bajarildi." else "**Shart bajarilmadi** — ma'lumotni ko'paytiring."
        appendLine("Maqsad: AC-08 = 100%, noto'g'ri FAIL ≤ 3%. $verdict")
        appendLine()
        appendLine("Standart configni o'zgartirish faqat shu hisobot asosida va `docs/DECISIONS.md` ga yozilgan holda (§11).")
    }

    fun pct(x: Double) = "${(x * PERCENT).roundToInt()}%"

    private const val PERCENT = 100
}
