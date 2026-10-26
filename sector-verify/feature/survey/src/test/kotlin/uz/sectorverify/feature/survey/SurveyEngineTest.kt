package uz.sectorverify.feature.survey

import io.kotest.matchers.nulls.shouldNotBeNull
import io.kotest.matchers.shouldBe
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Test
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.data.BatchSink
import uz.sectorverify.data.BufferedSampleWriter
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.telephony.TrafficStatus

@OptIn(ExperimentalCoroutinesApi::class)
class SurveyEngineTest {
    private val sim = Simulator.run(SimScenario(seed = 7, nArfcn = 1))

    private class Sink : BatchSink {
        var samples = 0
        var fixes = 0

        override suspend fun write(samples: List<CellSample>, fixes: List<GnssFix>) {
            this.samples += samples.size
            this.fixes += fixes.size
        }
    }

    /** Replays the simulated walk at 1 Hz on virtual time. */
    private fun cells(): Flow<List<CellSample>> = flow {
        for ((_, batch) in sim.samples.groupBy { it.tNanos }) {
            emit(batch)
            delay(1000)
        }
    }

    private fun fixes(): Flow<GnssFix> = flow {
        for (f in sim.fixes) {
            emit(f)
            delay(1000)
        }
    }

    @Test
    fun `engine persists, measures rate and becomes ready`() = runTest {
        val sink = Sink()
        val engine = SurveyEngine("s1", sim.plan, AnalysisConfig(), BufferedSampleWriter(sink), StandardTestDispatcher(testScheduler))
        val scope = TestScope(testScheduler)
        engine.start(scope, cells(), fixes(), flowOf(TrafficStatus.Ok(204, 30)))
        advanceTimeBy(sim.fixes.size * 1000L + 6_000)
        runCurrent()
        val s = engine.state.value
        s.samples shouldBe sim.samples.size
        s.fixes shouldBe sim.fixes.size
        (s.rateHz in 0.9..1.1) shouldBe true
        s.traffic shouldBe TrafficStatus.Ok(204, 30)
        s.live.shouldNotBeNull().ready shouldBe true
        s.readyAtSamples.shouldNotBeNull()
        s.visibleCells.isNotEmpty() shouldBe true
        engine.stop()
        engine.state.value.running shouldBe false
        sink.samples shouldBe sim.samples.size
        sink.fixes shouldBe sim.fixes.size
        engine.measuredRateHz shouldBe s.rateHz
        scope.cancel()
    }

    @Test
    fun `resumed session starts from restored data`() = runTest {
        val engine = SurveyEngine("s2", sim.plan, AnalysisConfig(), BufferedSampleWriter(Sink()), StandardTestDispatcher(testScheduler))
        val scope = TestScope(testScheduler)
        engine.start(scope, flowOf(), flowOf(), flowOf(TrafficStatus.Disabled), sim.samples, sim.fixes)
        runCurrent()
        engine.state.value.live.shouldNotBeNull().ready shouldBe true
        (engine.state.value.rateHz == 0.0) shouldBe true // no new serving samples yet
        scope.cancel()
    }

    @Test
    fun `controller publishes and finishes`() {
        val c = SurveyController()
        c.publish(SurveyState(sessionId = "x", running = true))
        c.finished("x")
        c.state.value.running shouldBe false
        c.state.value.finishedSessionId shouldBe "x"
        c.reset()
        c.state.value shouldBe SurveyState()
    }
}
