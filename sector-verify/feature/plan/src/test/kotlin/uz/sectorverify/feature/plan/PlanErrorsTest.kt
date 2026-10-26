package uz.sectorverify.feature.plan

import android.content.Context
import android.content.res.Configuration
import androidx.test.core.app.ApplicationProvider
import io.kotest.matchers.string.shouldContain
import io.kotest.matchers.string.shouldNotContain
import java.util.Locale
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import uz.sectorverify.format.PlanError
import uz.sectorverify.format.PlanErrorCode

/** Har bir CSV xatosi uz/ru/en tillarida qatori, ustuni/qiymati bilan va ortiqcha format spetsifikatorlarisiz chiqadi. */
@RunWith(RobolectricTestRunner::class)
class PlanErrorsTest {
    @Test
    fun allCodesInAllLanguages() {
        val base: Context = ApplicationProvider.getApplicationContext()
        for (tag in listOf("uz", "ru", "en")) {
            val res = base.createConfigurationContext(
                Configuration(base.resources.configuration).apply {
                    setLocale(Locale.forLanguageTag(tag))
                },
            ).resources
            for (code in PlanErrorCode.entries) {
                val text = PlanError(42, code, "lat", "91.5").localized(res)
                text shouldContain "42"
                text shouldNotContain "%"
                if (code == PlanErrorCode.LAT_RANGE) text shouldContain "91.5"
                if (code == PlanErrorCode.MISSING_COLUMN) text shouldContain "lat"
            }
        }
    }
}
