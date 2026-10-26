package uz.sectorverify.feature.plan

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import app.cash.turbine.test
import io.kotest.matchers.shouldBe
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import uz.sectorverify.data.db.SectorVerifyDatabase
import uz.sectorverify.data.repo.Clock
import uz.sectorverify.data.repo.NewSession
import uz.sectorverify.data.repo.RoomPlanRepository
import uz.sectorverify.data.repo.RoomSessionRepository
import uz.sectorverify.format.PlanCsv
import uz.sectorverify.format.PlanErrorCode
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.SessionMode

@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(RobolectricTestRunner::class)
class SitesViewModelTest {
    private val db = Room.inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext(), SectorVerifyDatabase::class.java)
        .allowMainThreadQueries()
        .build()
    private val plans = RoomPlanRepository(db.siteDao(), Clock.SYSTEM)
    private val sessions = RoomSessionRepository(db.sessionDao(), db.rawDao(), db.resultDao(), db.siteDao(), Clock.SYSTEM)
    private val header = PlanCsv.HEADER.joinToString(",")

    private class FakeResumer : SessionResumer {
        val resumed = ArrayList<String>()
        val abandoned = ArrayList<String>()
        override fun resume(sessionId: String) {
            resumed += sessionId
        }
        override suspend fun abandon(sessionId: String) {
            abandoned += sessionId
        }
    }

    @Before
    fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())

    @After
    fun tearDown() {
        Dispatchers.resetMain()
        db.close()
    }

    @Test
    fun importShowsSitesAndErrors() = runTest {
        val vm = SitesViewModel(plans, sessions, FakeResumer())
        vm.sites.test {
            awaitItem() shouldBe emptyList()
            vm.importCsv("$header\nNAV-1,Navoiy,40.1,65.3,43405,S1,LTE,B3,1300,141,0,65,,,\n")
            awaitItem().single().code shouldBe "NAV-1"
            vm.import.first { it != null }!!.imported shouldBe 1
            vm.dismissImport()
            vm.import.value shouldBe null
            vm.importCsv("$header\nX,X,95,65,43405,S1,LTE,B3,1300,141,0,65,,,\n")
            vm.import.first { it != null }!!.errors.single().code shouldBe PlanErrorCode.LAT_RANGE
            vm.setQuery("zzz")
            awaitItem() shouldBe emptyList()
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun runningSessionIsOfferedForResume() = runTest {
        plans.importCsv("$header\nNAV-2,N,40.1,65.3,43405,S1,LTE,B3,1300,141,0,65,,,\n")
        val id = sessions.create(NewSession(plans.siteByCode("NAV-2")!!.id, SessionMode.FULL, "t", 35, null, "1", "1", AnalysisConfig(), 1))
        val resumer = FakeResumer()
        val vm = SitesViewModel(plans, sessions, resumer)
        vm.resume.first { it != null }!!.siteCode shouldBe "NAV-2"
        vm.resume()
        resumer.resumed shouldBe listOf(id)
        vm.resume.value shouldBe null
        vm.checkRunning()
        vm.abandon()
        resumer.abandoned shouldBe listOf(id)
    }
}
