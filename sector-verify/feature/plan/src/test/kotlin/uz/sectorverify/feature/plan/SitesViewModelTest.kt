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

    private class FakeResumer(var allowed: Boolean = true) : SessionResumer {
        val resumed = ArrayList<String>()
        val abandoned = ArrayList<String>()
        override fun resume(sessionId: String): Boolean {
            if (allowed) resumed += sessionId
            return allowed
        }
        override suspend fun abandon(sessionId: String) {
            abandoned += sessionId
        }

        var recording = false

        override fun isRecording(sessionId: String) = recording
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
        val resumer = FakeResumer(allowed = false)
        val vm = SitesViewModel(plans, sessions, resumer)
        vm.resume.first { it != null }!!.siteCode shouldBe "NAV-2"
        vm.resume() shouldBe null // permission missing: offer stays, warning shown
        vm.resumeBlocked.value shouldBe true
        vm.resume.value!!.sessionId shouldBe id
        resumer.allowed = true
        vm.resume() shouldBe id
        resumer.resumed shouldBe listOf(id)
        vm.resume.value shouldBe null
        // A session the service is still recording is only opened, never abandoned.
        resumer.recording = true
        vm.checkRunning()
        vm.resume.value!!.recording shouldBe true
        vm.abandon()
        resumer.abandoned shouldBe emptyList()
        vm.resume() shouldBe id
        resumer.resumed shouldBe listOf(id) // not started a second time
        resumer.recording = false
        vm.checkRunning()
        vm.abandon()
        resumer.abandoned shouldBe listOf(id)
    }
}
