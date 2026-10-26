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
    fun `one live update is fast`() {
        val sim = Simulator.run(SimScenario(seed = 32, nSectors = 6, nArfcn = 3))
        live.snapshot(sim.plan, sim.samples, sim.fixes) // warm-up
        val t0 = System.nanoTime()
        live.snapshot(sim.plan, sim.samples, sim.fixes)
        val ms = (System.nanoTime() - t0) / 1e6
        (ms < 300.0) shouldBe true
    }
}
