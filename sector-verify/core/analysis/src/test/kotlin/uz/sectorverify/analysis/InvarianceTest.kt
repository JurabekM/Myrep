package uz.sectorverify.analysis

import io.kotest.matchers.doubles.plusOrMinus
import io.kotest.matchers.shouldBe
import io.kotest.property.Arb
import io.kotest.property.arbitrary.int
import io.kotest.property.arbitrary.long
import io.kotest.property.checkAll
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Test
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.model.AnalysisConfig

/** Property: rotating the whole world (plan azimuths and every GNSS position) by θ rotates every α̂ by θ. */
class InvarianceTest {
    private val analyzer = SessionAnalyzer(AnalysisConfig(bootstrapIterations = 20))

    @Test
    fun `estimates rotate with the site`() = runBlocking {
        checkAll(12, Arb.long(1L, 1_000_000L), Arb.int(1, 35)) { seed, steps ->
            val theta = steps * 10.0 // multiple of binDeg keeps every sample in the same relative bin
            val sim = Simulator.run(SimScenario(seed = seed, nArfcn = 1, coverage = 0.9, gapStartDeg = (seed % 360).toDouble()))
            val plan = sim.plan
            val rotatedPlan = plan.copy(sectors = plan.sectors.map { it.copy(azimuthDeg = Angles.norm360(it.azimuthDeg + theta)) })
            val rotatedFixes = sim.fixes.map { f ->
                val d = Geo.distanceM(plan.lat, plan.lon, f.lat, f.lon)
                val b = Geo.bearingDeg(plan.lat, plan.lon, f.lat, f.lon)
                val p = Geo.destination(plan.lat, plan.lon, b + theta, d)
                f.copy(lat = p.lat, lon = p.lon)
            }
            val a = analyzer.analyze(plan, sim.samples, sim.fixes)
            val b = analyzer.analyze(rotatedPlan, sim.samples, rotatedFixes)
            a.sectors.zip(b.sectors).forEach { (x, y) ->
                val ex = x.estimate ?: return@forEach
                Angles.diff(y.estimate!!.alphaDeg, ex.alphaDeg + theta) shouldBe (0.0 plusOrMinus 1.0)
            }
        }
    }
}
