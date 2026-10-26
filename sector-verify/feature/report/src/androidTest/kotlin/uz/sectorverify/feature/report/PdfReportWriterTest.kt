package uz.sectorverify.feature.report

import android.content.Context
import android.content.res.Configuration
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.io.File
import java.util.Locale
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import uz.sectorverify.analysis.ALGO_VERSION
import uz.sectorverify.analysis.SessionAnalyzer
import uz.sectorverify.analysis.sim.Fault
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.format.SessionMeta
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionStatus

/** §9 phase 3: the PDF is created and has pages, in each report language. */
@RunWith(AndroidJUnit4::class)
class PdfReportWriterTest {
    private val context: Context = ApplicationProvider.getApplicationContext()

    @Test
    fun pdfHasPagesInEveryLanguage() {
        val sim = Simulator.run(SimScenario(seed = 404, nArfcn = 2, fault = Fault.BandSwap(1, 0, 2)))
        val config = AnalysisConfig(bootstrapIterations = 30)
        val result = SessionAnalyzer(config).analyze(sim.plan, sim.samples, sim.fixes)
        val meta = SessionMeta(
            id = "pdf-test",
            siteCode = sim.plan.code,
            mode = SessionMode.FULL,
            startedAtUtcMs = 1_790_000_000_000,
            endedAtUtcMs = 1_790_001_000_000,
            deviceModel = "emulator",
            apiLevel = 34,
            appVersion = "test",
            algoVersion = ALGO_VERSION,
            measuredRateHz = 1.0,
            status = SessionStatus.DONE,
            engineer = "Test",
            config = config,
        )
        for (tag in listOf("uz", "ru", "en")) {
            val locale = Locale.forLanguageTag(tag)
            val localized = context.createConfigurationContext(Configuration(context.resources.configuration).apply { setLocale(locale) })
            val writer = PdfReportWriter(localized, locale)
            val bytes = writer.write(PdfInput(sim.plan, meta, result, sim.fixes, "ab".repeat(32), "c2ln"))
            assertEquals("%PDF", String(bytes.copyOf(4), Charsets.US_ASCII))
            assertTrue(writer.pages > 0)
            val file = File(context.cacheDir, "test-$tag.pdf").apply { writeBytes(bytes) }
            ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
                PdfRenderer(fd).use { assertEquals(writer.pages, it.pageCount) }
            }
        }
    }
}
