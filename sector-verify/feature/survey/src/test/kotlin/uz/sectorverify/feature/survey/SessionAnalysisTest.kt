package uz.sectorverify.feature.survey

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import io.kotest.matchers.shouldBe
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import uz.sectorverify.analysis.sim.Fault
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.data.db.SectorVerifyDatabase
import uz.sectorverify.data.repo.Clock
import uz.sectorverify.data.repo.NewSession
import uz.sectorverify.data.repo.RoomPlanRepository
import uz.sectorverify.data.repo.RoomSessionRepository
import uz.sectorverify.format.PlanCsv
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionStatus
import uz.sectorverify.model.Verdict

/** Stored raw data → final analysis → stored result (the service's finish path). */
@RunWith(RobolectricTestRunner::class)
class SessionAnalysisTest {
    private val db = Room.inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext(), SectorVerifyDatabase::class.java)
        .allowMainThreadQueries()
        .build()

    @After
    fun close() = db.close()

    @Test
    fun swapIsFoundFromStoredSession() = runTest {
        val sim = Simulator.run(SimScenario(seed = 303, nArfcn = 1, fault = Fault.FullSwap(listOf(0, 1, 2))))
        val plans = RoomPlanRepository(db.siteDao(), Clock.SYSTEM)
        val sessions = RoomSessionRepository(db.sessionDao(), db.rawDao(), db.resultDao(), db.siteDao(), Clock.SYSTEM)
        plans.importCsv(PlanCsv.write(listOf(sim.plan))).ok shouldBe true
        val site = plans.siteByCode(sim.plan.code)!!
        val config = AnalysisConfig(bootstrapIterations = 50)
        val id = sessions.create(NewSession(site.id, SessionMode.FULL, "sim", 35, null, "t", "1.0.0", config, 1))
        sessions.sink(id).write(sim.samples, sim.fixes)
        sessions.finish(id, SessionStatus.DONE)
        val result = SessionAnalysis(sessions, StandardTestDispatcher(testScheduler)).analyze(id)
        result.verdict shouldBe Verdict.FAIL
        val stored = sessions.result(id)!!
        stored.session.verdict shouldBe Verdict.FAIL
        stored.sectors shouldBe result.sectors
    }
}
