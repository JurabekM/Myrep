package uz.sectorverify.feature.survey

import androidx.lifecycle.SavedStateHandle
import app.cash.turbine.test
import io.kotest.matchers.nulls.shouldNotBeNull
import io.kotest.matchers.shouldBe
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import uz.sectorverify.data.db.SectorEntity
import uz.sectorverify.data.repo.PlanRepository
import uz.sectorverify.data.repo.SiteSummary
import uz.sectorverify.data.repo.StoredSite
import uz.sectorverify.data.settings.Settings
import uz.sectorverify.data.settings.SettingsRepository
import uz.sectorverify.feature.survey.ui.PreCheckViewModel
import uz.sectorverify.format.PlanImport
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Rat
import uz.sectorverify.model.Sector
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SitePlan
import uz.sectorverify.telephony.SimInfo

@OptIn(ExperimentalCoroutinesApi::class)
class PreCheckViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    private val plan = SitePlan("NAV-1", "N", 40.0, 65.0, "43405", listOf(Sector("S1", Rat.LTE, "B3", 1300, 141, 0.0)))

    private class FakePlans(private val plan: SitePlan) : PlanRepository {
        override suspend fun importCsv(text: String) = PlanImport(emptyList(), emptyList())
        override fun observeSites(query: String): Flow<List<SiteSummary>> = flowOf(emptyList())
        override suspend fun site(id: Long) = StoredSite(id, plan, emptyMap<SectorEntity, Long>())
        override suspend fun siteByCode(code: String) = site(1)
    }

    private class FakeSettings : SettingsRepository {
        override val settings = MutableStateFlow(Settings(trafficUrl = "https://example.com"))
        override suspend fun update(transform: (Settings) -> Settings) {
            settings.value = transform(settings.value)
        }
    }

    private class FakeSource(var location: Boolean) : PreCheckSource {
        val fixFlow = MutableSharedFlow<GnssFix>(replay = 1)
        val cellFlow = MutableSharedFlow<List<CellSample>>(replay = 1)
        override fun locationGranted() = location
        override fun phoneStateGranted() = true
        override fun notificationsGranted() = true
        override fun sims() = listOf(SimInfo(5, "434", "05", "Ucell", 0))
        override fun gpsEnabled() = true
        override fun fixes(): Flow<GnssFix> = if (location) fixFlow else emptyFlow()
        override fun cells(subscriptionId: Int): Flow<List<CellSample>> = if (location) cellFlow else emptyFlow()
    }

    class FakeLauncher : SurveyLauncher {
        val started = ArrayList<Pair<Long, SessionMode>>()
        override suspend fun start(siteId: Long, mode: SessionMode, sim: SimInfo?, appVersion: String): StartResult {
            started += siteId to mode
            return StartResult.Started("session-1")
        }
        override fun resume(sessionId: String) = true
        override suspend fun abandon(sessionId: String) = Unit
        override fun stop() = Unit
    }

    @BeforeEach
    fun setUp() = Dispatchers.setMain(dispatcher)

    @AfterEach
    fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `checks update with GNSS and cells, then start launches a RECHECK session`() = runTest(dispatcher) {
        val source = FakeSource(location = false)
        val launcher = FakeLauncher()
        val vm =
            PreCheckViewModel(
                SavedStateHandle(mapOf("siteId" to 1L, "mode" to "RECHECK")),
                FakePlans(plan),
                FakeSettings(),
                source,
                launcher,
            )
        advanceUntilIdle()
        vm.ui.value.result.shouldNotBeNull().canStart shouldBe false

        source.location = true
        vm.refresh()
        advanceUntilIdle()
        source.fixFlow.emit(GnssFix(1, 1, 40.0, 65.0, 4.0))
        source.cellFlow.emit(listOf(CellSample(1, Rat.LTE, 1300, 141, true, -90.0)))
        advanceUntilIdle()
        val r = vm.ui.value.result.shouldNotBeNull()
        r.canStart shouldBe true
        r.items.first { it.id == CheckId.PLANNED_CELLS }.status shouldBe CheckStatus.OK
        r.items.first { it.id == CheckId.GPS_ACCURACY }.status shouldBe CheckStatus.OK

        vm.ui.test {
            awaitItem()
            vm.start("1.0")
            awaitItem().startedSessionId shouldBe "session-1"
            vm.consumeStarted()
            awaitItem().startedSessionId shouldBe null
        }
        launcher.started.single() shouldBe (1L to SessionMode.RECHECK)
    }
}
