package uz.sectorverify.data

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import io.kotest.matchers.collections.shouldHaveSize
import io.kotest.matchers.nulls.shouldBeNull
import io.kotest.matchers.nulls.shouldNotBeNull
import io.kotest.matchers.shouldBe
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import uz.sectorverify.data.db.SectorVerifyDatabase
import uz.sectorverify.data.repo.Clock
import uz.sectorverify.data.repo.NewSession
import uz.sectorverify.data.repo.RoomPlanRepository
import uz.sectorverify.data.repo.RoomSessionRepository
import uz.sectorverify.format.PlanCsv
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.AzimuthEstimate
import uz.sectorverify.model.CauseCode
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.CleaningStats
import uz.sectorverify.model.Finding
import uz.sectorverify.model.FindingType
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Rat
import uz.sectorverify.model.SectorResult
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionResult
import uz.sectorverify.model.SessionStatus
import uz.sectorverify.model.Severity
import uz.sectorverify.model.Verdict

/** Room DAOs and repositories on Robolectric's SQLite (SQLCipher itself is covered by androidTest). */
@RunWith(RobolectricTestRunner::class)
class RoomRepositoryTest {
    private val db = Room.inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext(), SectorVerifyDatabase::class.java)
        .allowMainThreadQueries()
        .build()
    private val clock = Clock { 1_790_000_000_000 }
    private val plans = RoomPlanRepository(db.siteDao(), clock)
    private val sessions = RoomSessionRepository(db.sessionDao(), db.rawDao(), db.resultDao(), db.siteDao(), clock)
    private val header = PlanCsv.HEADER.joinToString(",")
    private val csv = "$header\n" +
        "NAV-1,Navoiy,40.1,65.3,43405,S1,LTE,B3,1300,141,0,65,,,\n" +
        "NAV-1,Navoiy,40.1,65.3,43405,S2,LTE,B3,1300,142,120,65,,,\n"

    @After
    fun close() = db.close()

    private fun newSession(siteId: Long) = NewSession(siteId, SessionMode.FULL, "Pixel", 35, null, "1.0", "1.0.0", AnalysisConfig(), 1)

    @Test
    fun importReplacesSectorsOfExistingSite() = runTest {
        plans.importCsv(csv).ok shouldBe true
        plans.importCsv(csv.replace("142,120", "143,120")).ok shouldBe true
        val site = plans.siteByCode("NAV-1").shouldNotBeNull()
        site.plan.sectors.map { it.pci } shouldBe listOf(141, 143)
        site.sectorId(Rat.LTE, 1300, 141).shouldNotBeNull()
        plans.observeSites().first() shouldHaveSize 1
        plans.observeSites("zzz").first() shouldHaveSize 0
        plans.importCsv("$header\nX,X,91,0,1,S1,LTE,B3,1,1,0,65,,,").ok shouldBe false
        plans.siteByCode("X").shouldBeNull()
        plans.site(999).shouldBeNull()
    }

    @Test
    fun sessionLifecycleAndRawData() = runTest {
        plans.importCsv(csv)
        val site = plans.siteByCode("NAV-1")!!
        val id = sessions.create(newSession(site.id))
        sessions.running().single().id shouldBe id
        val sample = CellSample(1, Rat.LTE, 1300, 141, true, -90.0, null, null, 3, null, null, 2)
        val fix = GnssFix(1, 2, 40.1, 65.3, 4.0)
        sessions.sink(id).write(listOf(sample, sample.copy(tNanos = 2)), listOf(fix))
        sessions.sampleCount(id) shouldBe 2
        sessions.samples(id).first() shouldBe sample
        sessions.fixes(id).single() shouldBe fix
        sessions.setMeasuredRate(id, 0.9)
        sessions.finish(id, SessionStatus.DONE)
        sessions.running() shouldHaveSize 0
        sessions.session(id)!!.measuredRateHz shouldBe 0.9
        sessions.meta(id, "Ali")!!.let {
            it.siteCode shouldBe "NAV-1"
            it.engineer shouldBe "Ali"
            it.config shouldBe AnalysisConfig()
        }
        sessions.meta("missing", null).shouldBeNull()
        sessions.result("missing").shouldBeNull()
    }

    @Test
    fun resultsAreReplacedAndShownAsLastVerdict() = runTest {
        plans.importCsv(csv)
        val site = plans.siteByCode("NAV-1")!!
        val id = sessions.create(newSession(site.id))
        val est = AzimuthEstimate(2.0, 355.0, 9.0, 7.0, 4.0, 3.0, 100, 30, false)
        val sector = SectorResult(CellKey(Rat.LTE, 1300, 141), "S1", 0.0, est, 2.0, 100, 1.0, listOf(3), Verdict.PASS, CauseCode.NONE)
        val unexpected = sector.copy(key = CellKey(Rat.LTE, 1300, 200), label = null, cause = CauseCode.PCI_UNEXPECTED)
        val result = SessionResult(
            "NAV-1",
            Verdict.WARN,
            listOf(sector, unexpected),
            listOf(Finding(FindingType.SWAP, Severity.CRITICAL, mapOf("pci.141" to "S2"))),
            0.8,
            List(36) { true },
            CleaningStats(1, 0, 0, 0, 0, 0, 1),
            1,
            "1.0.0",
        )
        sessions.saveResult(id, result, AnalysisConfig(seed = 9))
        sessions.saveResult(id, result, AnalysisConfig(seed = 9)) // re-analysis replaces
        sessions.finish(id, SessionStatus.DONE)
        val stored = sessions.result(id)!!
        stored.sectors shouldBe listOf(sector, unexpected)
        stored.findings.single().detail["pci.141"] shouldBe "S2"
        stored.session.verdict shouldBe Verdict.WARN
        stored.session.coveragePct shouldBe 80.0
        db.resultDao().results(id).first { it.pci == 200 }.sectorId.shouldBeNull()
        plans.observeSites().first().single().lastVerdict shouldBe Verdict.WARN
        sessions.observeForSite(site.id).first() shouldHaveSize 1
        sessions.observe(id).first()!!.status shouldBe SessionStatus.DONE
    }
}
