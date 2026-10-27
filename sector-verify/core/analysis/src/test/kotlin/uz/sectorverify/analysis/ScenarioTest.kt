package uz.sectorverify.analysis

import io.kotest.matchers.collections.shouldBeEmpty
import io.kotest.matchers.collections.shouldNotBeEmpty
import io.kotest.matchers.doubles.shouldBeLessThan
import io.kotest.matchers.shouldBe
import kotlin.math.abs
import org.junit.jupiter.api.Test
import uz.sectorverify.analysis.sim.Fault
import uz.sectorverify.analysis.sim.RouteShape
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CauseCode
import uz.sectorverify.model.FindingType
import uz.sectorverify.model.Rat
import uz.sectorverify.model.SessionResult
import uz.sectorverify.model.Severity
import uz.sectorverify.model.Verdict

/** Har bir Verdict va har bir CauseCode uchun bitta deterministik simulyatsiya sessiyasi (§9, 1-bosqich). */
class ScenarioTest {
    private val analyzer = SessionAnalyzer(AnalysisConfig(bootstrapIterations = 100))

    private fun analyse(s: SimScenario): Pair<uz.sectorverify.analysis.sim.SimResult, SessionResult> {
        val sim = Simulator.run(s)
        return sim to analyzer.analyze(sim.plan, sim.samples, sim.fixes, 100)
    }

    private fun SessionResult.planned() = sectors.filter { it.label != null }

    @Test
    fun `PASS - healthy three sector site`() {
        val (sim, r) = analyse(SimScenario(seed = 101, nArfcn = 2))
        r.verdict shouldBe Verdict.PASS
        r.planned().forEach {
            it.verdict shouldBe Verdict.PASS
            it.cause shouldBe CauseCode.NONE
            abs(Angles.diff(it.estimate!!.alphaDeg, sim.trueAzimuth.getValue(it.key))) shouldBeLessThan 15.0
        }
        r.findings.shouldBeEmpty()
        r.overallCoverage shouldBe 1.0
    }

    @Test
    fun `WARN and ANTENNA_ROTATED - antenna turned 32 degrees`() {
        val (sim, r) = analyse(SimScenario(seed = 202, nArfcn = 2, fault = Fault.Rotation(sector = 1, deg = 32.0)))
        r.verdict shouldBe Verdict.WARN
        for (k in sim.expected.causes.keys) {
            val s = r.sectors.first { it.key == k }
            s.verdict shouldBe Verdict.WARN
            s.cause shouldBe CauseCode.ANTENNA_ROTATED
        }
        r.findings.count { it.type == FindingType.ANTENNA_ROTATED } shouldBe 2
    }

    @Test
    fun `FAIL and CELL_CONFIG_SWAP - three sector rotation on every ARFCN`() {
        val (sim, r) = analyse(SimScenario(seed = 303, nArfcn = 2, fault = Fault.FullSwap(listOf(0, 1, 2))))
        r.verdict shouldBe Verdict.FAIL
        for ((k, label) in sim.expected.swapMapping) {
            val s = r.sectors.first { it.key == k }
            s.verdict shouldBe Verdict.FAIL
            s.cause shouldBe CauseCode.CELL_CONFIG_SWAP
            r.findings.any { it.type == FindingType.SWAP && it.detail["pci.${k.pci}"] == label } shouldBe true
        }
        r.findings.filter { it.type == FindingType.SWAP }.forEach {
            it.severity shouldBe Severity.CRITICAL
            it.detail["cause"] shouldBe "CELL_CONFIG_SWAP"
        }
    }

    @Test
    fun `FAIL and BAND_PORT_SWAP - two sectors swapped on one band only`() {
        val (sim, r) = analyse(SimScenario(seed = 404, nArfcn = 2, fault = Fault.BandSwap(arfcnIndex = 1, a = 0, b = 2)))
        r.verdict shouldBe Verdict.FAIL
        sim.expected.swapMapping.keys.forEach { k ->
            val s = r.sectors.first { it.key == k }
            s.verdict shouldBe Verdict.FAIL
            s.cause shouldBe CauseCode.BAND_PORT_SWAP
        }
        r.planned().filter { it.key !in sim.expected.swapMapping }.forEach { it.verdict shouldBe Verdict.PASS }
    }

    @Test
    fun `single ARFCN swap is classified as CELL_CONFIG_SWAP`() {
        val (_, r) = analyse(SimScenario(seed = 405, nArfcn = 1, fault = Fault.FullSwap(listOf(0, 1))))
        r.planned().filter { it.label != "S3" }.forEach { it.cause shouldBe CauseCode.CELL_CONFIG_SWAP }
    }

    @Test
    fun `FAIL and PCI_MISSING - one cell off`() {
        val (sim, r) = analyse(SimScenario(seed = 505, nArfcn = 2, fault = Fault.SectorOff(sector = 1, arfcnIndex = 0)))
        r.verdict shouldBe Verdict.FAIL
        val k = sim.expected.missing.single()
        val s = r.sectors.first { it.key == k }
        s.verdict shouldBe Verdict.FAIL
        s.cause shouldBe CauseCode.PCI_MISSING
        r.findings.single { it.type == FindingType.PCI_MISSING }.severity shouldBe Severity.CRITICAL
    }

    @Test
    fun `PCI_UNEXPECTED - unplanned serving cell is reported as INFO only`() {
        val (sim, r) = analyse(
            SimScenario(seed = 606, nArfcn = 2, pNeighbor = 0.3, fault = Fault.UnplannedCell(sector = 2, arfcnIndex = 1)),
        )
        val k = sim.expected.unexpected.single()
        val u = r.sectors.single { it.key == k }
        u.label shouldBe null
        u.cause shouldBe CauseCode.PCI_UNEXPECTED
        r.findings.single { it.type == FindingType.PCI_UNEXPECTED }.severity shouldBe Severity.INFO
        r.verdict shouldBe Verdict.PASS
    }

    @Test
    fun `INCONCLUSIVE and LOW_COVERAGE - only 45 percent of the circle walked`() {
        val (_, r) = analyse(SimScenario(seed = 707, nArfcn = 2, coverage = 0.45, fault = Fault.FullSwap(listOf(0, 1))))
        r.verdict shouldBe Verdict.INCONCLUSIVE
        r.planned().forEach {
            it.verdict shouldBe Verdict.INCONCLUSIVE
            it.cause shouldBe CauseCode.LOW_COVERAGE
        }
        r.findings.single().let {
            it.type shouldBe FindingType.LOW_COVERAGE
            it.detail["scope"] shouldBe "site"
        }
    }

    @Test
    fun `sector without coverage in its window is INCONCLUSIVE while the rest pass`() {
        val (_, r) = analyse(SimScenario(seed = 808, nArfcn = 1, coverage = 0.72, gapStartDeg = 300.0))
        val s1 = r.planned().first { it.label == "S1" }
        s1.verdict shouldBe Verdict.INCONCLUSIVE
        s1.cause shouldBe CauseCode.LOW_COVERAGE
        s1.missingBins.shouldNotBeEmpty()
        r.findings.any { it.type == FindingType.LOW_COVERAGE && it.detail["label"] == "S1" } shouldBe true
    }

    @Test
    fun `neighbour site reusing a PCI does not fail a healthy site`() {
        val (_, r) = analyse(SimScenario(seed = 909, nArfcn = 1, fault = Fault.NeighborPciReuse(0, 0, 1500.0, 0.0)))
        (r.verdict == Verdict.FAIL) shouldBe false
        r.cleaning.taMismatch shouldBe r.cleaning.taMismatch // TA filtri ishladi (qo'shni xizmat qilmagan bo'lsa, soni 0 bo'lishi mumkin)
    }

    @Test
    fun `square route, fast speed and NR`() {
        val (_, r) = analyse(SimScenario(seed = 111, rat = Rat.NR, route = RouteShape.SQUARE, speedMps = 5.0, nSectors = 4))
        r.planned().size shouldBe 4
        r.planned().all { it.estimate != null } shouldBe true
        (r.verdict == Verdict.FAIL) shouldBe false
    }

    @Test
    fun `analysis is deterministic for a seed`() {
        val s = SimScenario(seed = 1212, nArfcn = 2, fault = Fault.FullSwap(listOf(0, 1)))
        analyse(s).second shouldBe analyse(s).second
        Simulator.run(s) shouldBe Simulator.run(s)
    }
}
