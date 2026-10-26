package uz.sectorverify.analysis

import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.model.AnalysisConfig

/**
 * §5 performance: final analysis < 10 s and one live update < 300 ms on a mid-range phone. On the JVM the
 * worst case (18 cells, 400 m ring, full bootstrap) must stay within 1/5 of those budgets, leaving room
 * for a phone CPU that is several times slower; the on-device numbers are confirmed in H2.
 */
@Tag("perf")
class PerformanceTest {
    private val sim = Simulator.run(SimScenario(seed = 9, nSectors = 6, nArfcn = 3, radiusM = 400.0))

    private fun timeMs(block: () -> Unit): Double {
        repeat(WARMUP) { block() } // JIT warm-up
        val t0 = System.nanoTime()
        repeat(RUNS) { block() }
        return (System.nanoTime() - t0) / 1e6 / RUNS
    }

    @Test
    fun `final analysis of the worst case fits the budget`() {
        val analyzer = SessionAnalyzer(AnalysisConfig())
        val ms = timeMs { analyzer.analyze(sim.plan, sim.samples, sim.fixes) }
        println("final analysis: %.0f ms, %d samples, %d cells".format(ms, sim.samples.size, sim.plan.sectors.size))
        assertTrue(ms < FINAL_BUDGET_MS / PHONE_FACTOR, "final analysis took $ms ms")
    }

    @Test
    fun `live update of the worst case fits the budget`() {
        // Realistic call: the analyzer already holds the session minus the last 5 s (one live interval).
        val cut = sim.samples.last().tNanos - LIVE_INTERVAL_NANOS
        val before = sim.samples.filter { it.tNanos <= cut }
        val fixesBefore = sim.fixes.filter { it.tNanos <= cut }
        val times = (0 until WARMUP + RUNS).map {
            val live = LiveAnalyzer(AnalysisConfig())
            live.snapshot(sim.plan, before, fixesBefore)
            val t0 = System.nanoTime()
            live.snapshot(sim.plan, sim.samples, sim.fixes)
            (System.nanoTime() - t0) / 1e6
        }
        val ms = times.drop(WARMUP).average()
        println("live update: %.0f ms".format(ms))
        assertTrue(ms < LIVE_BUDGET_MS / PHONE_FACTOR, "live update took $ms ms")
    }

    private companion object {
        const val WARMUP = 3
        const val RUNS = 3
        const val LIVE_INTERVAL_NANOS = 5_000_000_000L
        const val FINAL_BUDGET_MS = 10_000.0
        const val LIVE_BUDGET_MS = 300.0
        const val PHONE_FACTOR = 5.0
    }
}
