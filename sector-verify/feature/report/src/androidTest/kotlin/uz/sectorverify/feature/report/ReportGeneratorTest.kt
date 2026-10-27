package uz.sectorverify.feature.report

import android.content.Context
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.io.File
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import uz.sectorverify.analysis.SessionAnalyzer
import uz.sectorverify.analysis.sim.Fault
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.data.db.SectorVerifyDatabase
import uz.sectorverify.data.repo.Clock
import uz.sectorverify.data.repo.NewSession
import uz.sectorverify.data.repo.RoomPlanRepository
import uz.sectorverify.data.repo.RoomReportRepository
import uz.sectorverify.data.repo.RoomSessionRepository
import uz.sectorverify.data.repo.SessionExporter
import uz.sectorverify.data.security.KeystoreReportSigner
import uz.sectorverify.data.settings.DataStoreSettingsRepository
import uz.sectorverify.format.PlanCsv
import uz.sectorverify.format.ReportIntegrity
import uz.sectorverify.format.SessionZip
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionStatus

/** Saqlangan sessiya → imzolangan report.json + PDF + ZIP; imzo tasdiqlanadi (§8.3) va ZIP qayta o'qiladi (§5.4). */
@RunWith(AndroidJUnit4::class)
class ReportGeneratorTest {
    private val context: Context = ApplicationProvider.getApplicationContext()

    @Test
    fun generatesVerifiableReport(): Unit = runBlocking {
        val db = Room.inMemoryDatabaseBuilder(context, SectorVerifyDatabase::class.java).build()
        val plans = RoomPlanRepository(db.siteDao(), Clock.SYSTEM)
        val sessions = RoomSessionRepository(db.sessionDao(), db.rawDao(), db.resultDao(), db.siteDao(), Clock.SYSTEM)
        val store = PreferenceDataStoreFactory.create { File(context.cacheDir, "report-test-${System.nanoTime()}.preferences_pb") }
        val settings = DataStoreSettingsRepository(store)
        settings.update { it.copy(engineerName = "Test", reportLanguage = "ru") }
        val sim = Simulator.run(SimScenario(seed = 303, nArfcn = 1, fault = Fault.FullSwap(listOf(0, 1, 2))))
        plans.importCsv(PlanCsv.write(listOf(sim.plan)))
        val config = AnalysisConfig(bootstrapIterations = 30)
        val id = sessions.create(
            NewSession(plans.siteByCode(sim.plan.code)!!.id, SessionMode.FULL, "emu", 34, null, "t", "1.0.0", config, 1),
        )
        sessions.sink(id).write(sim.samples, sim.fixes)
        sessions.finish(id, SessionStatus.DONE)
        sessions.saveResult(id, SessionAnalyzer(config).analyze(sim.plan, sim.samples, sim.fixes), config)

        val generator = ReportGenerator(
            context,
            sessions,
            settings,
            RoomReportRepository(db.reportDao()),
            SessionExporter(sessions),
            KeystoreReportSigner(context, "sv_test_generator_key"),
            Clock.SYSTEM,
        )
        val r = generator.generate(id)
        assertTrue(r.pages > 0)
        assertTrue(ReportIntegrity.verify(r.json.readText()).ok)
        val export = r.zip.inputStream().use { SessionZip.read(it) }
        assertEquals(sim.samples.size, export.samples.size)
        assertTrue(ReportIntegrity.verify(export.reportJson!!).ok)
        assertEquals("%PDF", String(export.reportPdf!!.copyOf(4), Charsets.US_ASCII))
        db.close()
    }
}
