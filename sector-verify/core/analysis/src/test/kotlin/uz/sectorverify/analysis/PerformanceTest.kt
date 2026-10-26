package uz.sectorverify.analysis

import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.model.AnalysisConfig

/**
 * §5 unumdorlik: o'rta toifali telefonda yakuniy tahlil < 10 s va bitta jonli yangilanish < 300 ms. JVM'da
 * eng yomon holat (18 yacheyka, 400 m halqa, to'liq bootstrap) shu byudjetlarning 1/5 qismidan oshmasligi kerak — bu
 * bir necha marta sekinroq telefon CPU'si uchun zaxira qoldiradi; qurilmadagi raqamlar H2 da tasdiqlanadi.
 */
@Tag("perf")
class PerformanceTest {
    private val sim = Simulator.run(SimScenario(seed = 9, nSectors = 6, nArfcn = 3, radiusM = 400.0))

    private fun timeMs(block: () -> Unit): Double {
        repeat(WARMUP) { block() } // JIT qizdirish
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
        // Real chaqiruv: analizatorda sessiya oxirgi 5 s (bitta jonli interval) dan tashqari allaqachon bor.
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
