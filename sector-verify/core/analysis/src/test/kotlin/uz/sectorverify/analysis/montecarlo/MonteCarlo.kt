package uz.sectorverify.analysis.montecarlo

import java.io.File
import kotlin.math.abs
import kotlin.random.Random
import uz.sectorverify.analysis.Angles
import uz.sectorverify.analysis.SessionAnalyzer
import uz.sectorverify.analysis.sim.Fault
import uz.sectorverify.analysis.sim.RouteShape
import uz.sectorverify.analysis.sim.SimResult
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.FindingType
import uz.sectorverify.model.SessionResult
import uz.sectorverify.model.Verdict

/** Monte-Carlo evaluation of AC-01…AC-04 on simulated sessions (bootstrap 50 iterations for speed, §6.4). */
object MonteCarlo {
    const val BOOTSTRAP = 50
    private val config = AnalysisConfig(bootstrapIterations = BOOTSTRAP)
    private val analyzer = SessionAnalyzer(config)

    data class Run(val sim: SimResult, val result: SessionResult)

    data class Ac(val id: String, val title: String, val value: Double, val target: String, val pass: Boolean, val n: Int, val note: String)

    fun scenario(seed: Long, coverage: ClosedFloatingPointRange<Double>, fault: (Random, Int, Int) -> Fault): SimScenario {
        val r = Random(seed * 7919 + 17)
        val nSectors = 3 + r.nextInt(4)
        val nArfcn = 1 + r.nextInt(3)
        return SimScenario(
            seed = seed,
            nSectors = nSectors,
            nArfcn = nArfcn,
            azimuthOffsetDeg = r.nextDouble() * 360,
            route = if (r.nextBoolean()) RouteShape.RING else RouteShape.SQUARE,
            radiusM = 150 + r.nextDouble() * 250,
            coverage = coverage.start + r.nextDouble() * (coverage.endInclusive - coverage.start),
            gapStartDeg = r.nextDouble() * 360,
            speedMps = if (r.nextDouble() < 0.8) 1.4 else 5.0,
            shadowSigmaDb = 6 + r.nextDouble() * 2,
            pNeighbor = 0.5 + r.nextDouble() * 0.5,
            fault = fault(r, nSectors, nArfcn),
        )
    }

    fun run(s: SimScenario): Run {
        val sim = Simulator.run(s)
        return Run(sim, analyzer.analyze(sim.plan, sim.samples, sim.fixes, BOOTSTRAP))
    }

    private fun swapFault(r: Random, nSectors: Int, nArfcn: Int): Fault {
        val sectors = (0 until nSectors).shuffled(r)
        return if (nArfcn > 1 && r.nextBoolean()) {
            Fault.BandSwap(r.nextInt(nArfcn), sectors[0], sectors[1])
        } else {
            Fault.FullSwap(sectors.take(if (r.nextBoolean()) 2 else 3))
        }
    }

    private fun noFault(r: Random, nSectors: Int, nArfcn: Int): Fault = if (r.nextDouble() < 0.2) {
        Fault.NeighborPciReuse(r.nextInt(nSectors), r.nextInt(nArfcn), 1200 + r.nextDouble() * 1300, r.nextDouble() * 360)
    } else {
        Fault.None
    }

    /** Swap detected = every expected swapped cell is in a SWAP finding with the right target label. */
    fun detected(run: Run): Boolean {
        val found = run.result.findings.filter { it.type == FindingType.SWAP }
        return run.sim.expected.swapMapping.all { (key, label) ->
            found.any { it.detail["arfcn"] == key.arfcn.toString() && it.detail["pci.${key.pci}"] == label }
        }
    }

    fun ac01(n: Int, base: Long = 10_000): Pair<Ac, List<Run>> {
        val runs = (0 until n).map { run(scenario(base + it, 0.70..1.0, ::swapFault)) }
        val rate = runs.count(::detected).toDouble() / n
        val causeOk = runs.count { r ->
            r.sim.expected.causes.all { (k, c) ->
                r.result.findings.any {
                    it.type == FindingType.SWAP &&
                        it.detail["pci.${k.pci}"] != null &&
                        it.detail["arfcn"] == "${k.arfcn}" &&
                        it.detail["cause"] == c.name
                }
            }
        }
        val sectorFail = runs.count { r ->
            r.sim.expected.causes.keys.all { k ->
                r.result.sectors.first { it.key == k }.verdict ==
                    Verdict.FAIL
            }
        }
        val note = "topilmadagi sabab to'g'ri: ${pct(causeOk.toDouble() / n)}; barcha almashgan sektorlar FAIL: ${pct(
            sectorFail.toDouble() / n,
        )}"
        return Ac("AC-01", "Almashinuvni aniqlash, qamrov ≥ 70%", rate, "≥ 95%", rate >= 0.95, n, note) to runs
    }

    fun ac02(n: Int, base: Long = 20_000): Pair<Ac, List<Run>> {
        val runs = (0 until n).map { run(scenario(base + it, 0.50..1.0, ::noFault)) }
        val rate = runs.count { it.result.verdict == Verdict.FAIL }.toDouble() / n
        val hi = runs.filter { it.result.overallCoverage >= config.minOverallCoverage }
        val pass = hi.count { it.result.verdict == Verdict.PASS }.toDouble() / hi.size
        val sectors = hi.flatMap { r -> r.result.sectors.filter { it.label != null } }
        val sectorPass = sectors.count { it.verdict == Verdict.PASS }.toDouble() / sectors.size
        val note = "ma'lumot uchun, umumiy qamrov yetarli (${hi.size}): sayt PASS ${pct(pass)}, sektor PASS ${pct(sectorPass)}"
        return Ac("AC-02", "Noto'g'ri FAIL (xato yo'q), qamrov 50–100%", rate, "≤ 3%", rate <= 0.03, n, note) to runs
    }

    fun ac03(n: Int, base: Long = 30_000): Pair<Ac, List<Run>> {
        val runs = (0 until n).map { run(scenario(base + it, 0.70..1.0, ::noFault)) }
        val errors = runs.flatMap { r ->
            r.result.sectors.filter { it.label != null }.mapNotNull { s ->
                s.estimate?.let { abs(Angles.diff(it.alphaDeg, r.sim.trueAzimuth.getValue(s.key))) }
            }
        }.sorted()
        val median = errors[errors.size / 2]
        val p90 = errors[(errors.size * 0.9).toInt()]
        return Ac(
            "AC-03",
            "Azimut xatosi medianasi, qamrov ≥ 70%",
            median,
            "≤ 10°",
            median <= 10.0,
            n,
            "P90: ${fmt(p90)}°, baholar: ${errors.size}",
        ) to
            runs
    }

    fun ac04(n: Int, base: Long = 40_000): Pair<Ac, List<Run>> {
        val runs = (0 until n).map { i ->
            run(scenario(base + i, 0.30..0.60) { r, ns, na -> if (i % 2 == 0) noFault(r, ns, na) else swapFault(r, ns, na) })
        }
        val ok = runs.count { r ->
            r.result.verdict == Verdict.INCONCLUSIVE &&
                r.result.sectors.filter { it.label != null }.all { it.verdict == Verdict.INCONCLUSIVE }
        }
        val rate = ok.toDouble() / n
        return Ac("AC-04", "Qamrov 30–60% → INCONCLUSIVE", rate, "100%", rate == 1.0, n, "yarmi almashinuvli") to runs
    }

    fun report(results: List<Ac>, iterations: Int, file: String = "montecarlo.md"): String {
        val md = buildString {
            appendLine("# Monte-Karlo natijalari ($iterations iteratsiya / AC, bootstrap $BOOTSTRAP)")
            appendLine()
            appendLine("| ID | Mezon | Natija | Maqsad | Holat | Izoh |")
            appendLine("|---|---|---|---|---|---|")
            for (a in results) {
                val v = if (a.id == "AC-03") "${fmt(a.value)}°" else pct(a.value)
                appendLine("| ${a.id} | ${a.title} | $v | ${a.target} | ${if (a.pass) "✅" else "❌"} | ${a.note} |")
            }
        }
        val dir = System.getProperty("sv.reportsDir") ?: "build/reports"
        File(dir).mkdirs()
        File(dir, file).writeText(md)
        return md
    }

    fun pct(x: Double) = "%.1f%%".format(x * 100)

    fun fmt(x: Double) = "%.1f".format(x)
}
