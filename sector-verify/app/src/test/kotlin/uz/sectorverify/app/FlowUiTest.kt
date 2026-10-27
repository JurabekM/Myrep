package uz.sectorverify.app

import android.content.Context
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.hasAnyDescendant
import androidx.compose.ui.test.hasScrollAction
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import androidx.room.Room
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import dagger.hilt.android.testing.HiltTestApplication
import dagger.hilt.android.testing.UninstallModules
import dagger.hilt.components.SingletonComponent
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.runBlocking
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import uz.sectorverify.analysis.sim.Fault
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.data.db.SectorVerifyDatabase
import uz.sectorverify.data.di.DataProvidesModule
import uz.sectorverify.data.repo.Clock
import uz.sectorverify.data.repo.NewSession
import uz.sectorverify.data.repo.PlanRepository
import uz.sectorverify.data.repo.SessionRepository
import uz.sectorverify.feature.survey.PreCheckSource
import uz.sectorverify.feature.survey.SessionAnalysis
import uz.sectorverify.feature.survey.StartResult
import uz.sectorverify.feature.survey.SurveyController
import uz.sectorverify.feature.survey.SurveyLauncher
import uz.sectorverify.feature.survey.SurveyModule
import uz.sectorverify.format.PlanCsv
import uz.sectorverify.format.ReportSigner
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionStatus
import uz.sectorverify.telephony.SimInfo

private val SIM = Simulator.run(SimScenario(seed = 303, nArfcn = 1, fault = Fault.FullSwap(listOf(0, 1, 2))))

/** Soxta ma'lumotlarda UI oqimi (§9 3-bosqich): import qilingan reja → oldindan tekshiruv → o'lchov → FAIL verdiktli natija ekrani. */
@HiltAndroidTest
@UninstallModules(DataProvidesModule::class, SurveyModule::class)
@RunWith(RobolectricTestRunner::class)
@Config(application = HiltTestApplication::class, sdk = [34], qualifiers = "w411dp-h1600dp")
class FlowUiTest {
    @get:Rule(order = 0)
    val hilt = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val compose = createAndroidComposeRule<MainActivity>()

    @Inject lateinit var plans: PlanRepository

    @Module
    @InstallIn(SingletonComponent::class)
    object TestDataModule {
        @Provides
        @Singleton
        fun db(@ApplicationContext c: Context): SectorVerifyDatabase =
            Room.inMemoryDatabaseBuilder(c, SectorVerifyDatabase::class.java).allowMainThreadQueries().build()

        @Provides fun siteDao(db: SectorVerifyDatabase) = db.siteDao()

        @Provides fun sessionDao(db: SectorVerifyDatabase) = db.sessionDao()

        @Provides fun rawDao(db: SectorVerifyDatabase) = db.rawDao()

        @Provides fun resultDao(db: SectorVerifyDatabase) = db.resultDao()

        @Provides fun reportDao(db: SectorVerifyDatabase) = db.reportDao()

        @Provides
        @Singleton
        fun store(@ApplicationContext c: Context): DataStore<Preferences> =
            PreferenceDataStoreFactory.create { File(c.cacheDir, "flow-${System.nanoTime()}.preferences_pb") }

        @Provides fun clock(): Clock = Clock.SYSTEM

        @Provides
        fun signer(): ReportSigner = object : ReportSigner {
            override fun sign(data: ByteArray) = ByteArray(0)
            override fun certificateChain() = emptyList<ByteArray>()
        }
    }

    /** Rejadagi cell'larni yaxshi GPS fix bilan ko'radigan qurilma. */
    class FakeSource @Inject constructor() : PreCheckSource {
        override fun locationGranted() = true
        override fun phoneStateGranted() = true
        override fun notificationsGranted() = true
        override fun sims() = listOf(SimInfo(1, "434", "05", "Ucell", 0))
        override fun gpsEnabled() = true
        override fun fixes(): Flow<GnssFix> = flowOf(SIM.fixes.first())
        override fun cells(subscriptionId: Int): Flow<List<CellSample>> = flowOf(SIM.samples.take(20))
    }

    /** Servis o'rniga: simulyatsiya qilingan yurishni saqlaydi, tugatadi va tahlil qiladi. */
    class FakeLauncher @Inject constructor(
        private val sessions: SessionRepository,
        private val analysis: SessionAnalysis,
        private val controller: SurveyController,
    ) : SurveyLauncher {
        override suspend fun start(siteId: Long, mode: SessionMode, sim: SimInfo?, appVersion: String): StartResult {
            val id = sessions.create(
                NewSession(siteId, mode, "Robolectric", 34, null, appVersion, "1.0.0", AnalysisConfig(bootstrapIterations = 30), 1),
            )
            sessions.sink(id).write(SIM.samples, SIM.fixes)
            sessions.finish(id, SessionStatus.DONE)
            analysis.analyze(id)
            controller.finished(id)
            return StartResult.Started(id)
        }
        override fun resume(sessionId: String) = true
        override suspend fun abandon(sessionId: String) = Unit
        override fun stop() = Unit
    }

    @Module
    @InstallIn(SingletonComponent::class)
    abstract class TestSurveyModule {
        @Binds abstract fun launcher(impl: FakeLauncher): SurveyLauncher

        @Binds abstract fun source(impl: FakeSource): PreCheckSource
    }

    @Before
    fun setUp() {
        hilt.inject()
        runBlocking { plans.importCsv(PlanCsv.write(listOf(SIM.plan))) }
    }

    @Test
    fun importedPlanSurveyAndResult() {
        val site = "site-${SIM.plan.code}"
        compose.waitUntil(TIMEOUT) { compose.onAllNodes(hasTestTag(site)).fetchSemanticsNodes().isNotEmpty() }
        compose.onNodeWithTag(site).performClick()
        compose.waitUntil(TIMEOUT) { compose.onAllNodes(hasTestTag("precheck")).fetchSemanticsNodes().isNotEmpty() }
        compose.onNodeWithTag("precheck").performClick()
        compose.waitUntil(TIMEOUT) { compose.onAllNodes(hasScrollAction()).fetchSemanticsNodes().isNotEmpty() }
        compose.onNode(hasScrollAction()).performScrollToNode(hasTestTag("start"))
        compose.waitUntil(TIMEOUT) { runCatching { compose.onNodeWithTag("start").assertIsEnabled() }.isSuccess }
        compose.onNodeWithTag("start").performClick()
        compose.waitUntil(LONG_TIMEOUT) { compose.onAllNodes(hasTestTag("overall")).fetchSemanticsNodes().isNotEmpty() }
        compose.onNodeWithTag("overall").assert(hasAnyDescendant(hasText("FAIL")))
        compose.onAllNodesWithText("FAIL").assertCountEquals(1 + SIM.plan.sectors.size)
    }

    private companion object {
        const val TIMEOUT = 10_000L
        const val LONG_TIMEOUT = 60_000L
    }
}
