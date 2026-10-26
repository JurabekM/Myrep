package uz.sectorverify.analysis

import io.kotest.matchers.shouldBe
import org.junit.jupiter.api.Test
import uz.sectorverify.analysis.sim.Fault
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.Verdict

class LiveAnalyzerTest {
    private val live = LiveAnalyzer(AnalysisConfig())

    @Test
    fun `snapshot grows with the walk and becomes ready`() {
        val sim = Simulator.run(SimScenario(seed = 31, nArfcn = 1, fault = Fault.FullSwap(listOf(0, 1))))
        val first = live.snapshot(sim.plan, sim.samples.take(30), sim.fixes.take(10))
        first.ready shouldBe false
        first.cells.filter { it.label != null }.all { it.status == Verdict.INCONCLUSIVE } shouldBe true
        val full = live.snapshot(sim.plan, sim.samples, sim.fixes)
        full.ready shouldBe true
        full.overallCoverage shouldBe 1.0
        full.coveredBins.size shouldBe 36
        full.cells.first { it.label == "S3" }.status shouldBe Verdict.PASS
        full.cells.filter { it.key in sim.expected.swapMapping }.all { it.status == Verdict.FAIL } shouldBe true
        full.cells.all { it.lastRsrp != null && it.nSamples > 0 } shouldBe true
    }

    @Test
    fun `incremental snapshots equal a fresh full computation`() {
        val sim = Simulator.run(SimScenario(seed = 33, nArfcn = 2, fault = Fault.Rotation(1, 30.0)))
        val inc = LiveAnalyzer(AnalysisConfig())
        var last: LiveSnapshot? = null
        for (secs in listOf(60, 300, 301, 700, Int.MAX_VALUE)) {
            val s = sim.samples.filter { it.tNanos - Simulator.T0_NANOS < secs * 1_000_000_000L }
            val f = sim.fixes.filter { it.tNanos - Simulator.T0_NANOS < secs * 1_000_000_000L }
            last = inc.snapshot(sim.plan, s, f)
            last shouldBe LiveAnalyzer(AnalysisConfig()).snapshot(sim.plan, s, f)
        }
        // A different (shorter) list resets the cache.
        inc.snapshot(sim.plan, sim.samples.take(100), sim.fixes.take(40)) shouldBe
            LiveAnalyzer(AnalysisConfig()).snapshot(sim.plan, sim.samples.take(100), sim.fixes.take(40))
        (last!!.samplesKept > 0) shouldBe true
    }
}
