package uz.sectorverify.analysis

import io.kotest.matchers.doubles.plusOrMinus
import io.kotest.matchers.nulls.shouldBeNull
import io.kotest.matchers.nulls.shouldNotBeNull
import io.kotest.matchers.shouldBe
import kotlin.math.log10
import org.junit.jupiter.api.Test
import uz.sectorverify.analysis.Fixtures.LAT
import uz.sectorverify.analysis.Fixtures.LON
import uz.sectorverify.analysis.Fixtures.SEC
import uz.sectorverify.analysis.Fixtures.fix
import uz.sectorverify.analysis.Fixtures.sample
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.Rat

class CleanerTest {
    private val config = AnalysisConfig()
    private val cleaner = Cleaner(config)
    private val fixes = (0..20).map { fix(it * SEC, 90.0, 300.0) }

    @Test
    fun `each filter of 6_1 drops its sample`() {
        val samples = listOf(
            sample(5 * SEC), // saqlanadi
            sample(5 * SEC, rsrp = null), // 1. rsrp yo'q
            sample(5 * SEC, rx = 5 * SEC + 3_001_000_000L), // 2. eskirgan
            sample(60 * SEC), // 3. yaqinda fix yo'q
            sample(6 * SEC, ta = 4), // 7. TA 4·78 m = 312 m vs 300 m: saqlanadi
            sample(6 * SEC, ta = 9), // 7. TA 703 m vs 300 m: boshqa sayt
        )
        val r = cleaner.clean(LAT, LON, samples, fixes)
        r.stats.total shouldBe 6
        r.stats.noRsrp shouldBe 1
        r.stats.stale shouldBe 1
        r.stats.noFix shouldBe 1
        r.stats.taMismatch shouldBe 1
        r.stats.kept shouldBe 2
        r.samples.first().distanceM shouldBe (300.0 plusOrMinus 0.01)
        r.samples.first().bearingDeg shouldBe (90.0 plusOrMinus 0.01)
        r.samples.first().y shouldBe (-90.0 plusOrMinus 1e-6)
    }

    @Test
    fun `NR samples ignore TA and out of range distances are dropped`() {
        val near = (0..5).map { fix(it * SEC, 0.0, 50.0) }
        val r = cleaner.clean(LAT, LON, listOf(sample(2 * SEC)), near)
        r.stats.outOfRange shouldBe 1
        val nr = sample(2 * SEC, ta = 50).copy(rat = Rat.NR)
        cleaner.clean(LAT, LON, listOf(nr), fixes).stats.kept shouldBe 1
    }

    @Test
    fun `bad fixes are excluded before interpolation`() {
        val bad = listOf(fix(0, 90.0, 300.0, acc = 20.0), fix(SEC, 90.0, 300.0, speed = 9.0), fix(2 * SEC, 90.0, 300.0, speed = null))
        val r = cleaner.clean(LAT, LON, listOf(sample(0), sample(SEC), sample(5 * SEC)), bad)
        r.stats.kept shouldBe 2 // t=0 va t=1 s 2 s dagi fix'dan foydalanadi (oraliq ≤ 2 s); t=5 s da 2 s ichida fix yo'q
        r.stats.noFix shouldBe 1
    }

    @Test
    fun `interpolation is linear between neighbouring fixes`() {
        val a = fix(0, 0.0, 300.0)
        val b = fix(2 * SEC, 90.0, 300.0)
        val list = listOf(a, b)
        val times = longArrayOf(0, 2 * SEC)
        val mid = cleaner.interpolate(list, times, SEC).shouldNotBeNull()
        mid.lat shouldBe ((a.lat + b.lat) / 2 plusOrMinus 1e-12)
        mid.lon shouldBe ((a.lon + b.lon) / 2 plusOrMinus 1e-12)
        cleaner.interpolate(list, times, 0)!!.lat shouldBe a.lat
        cleaner.interpolate(list, times, 4 * SEC)!!.lat shouldBe b.lat
        cleaner.interpolate(list, times, 4 * SEC + 1).shouldBeNull()
        cleaner.interpolate(emptyList(), LongArray(0), 0).shouldBeNull()
        // GNSS uzilishi: uzoqdagi qo'shni (60 s) interpolyatsiyada ishlatilmaydi.
        val far = fix(60 * SEC, 180.0, 300.0)
        cleaner.interpolate(listOf(a, far), longArrayOf(0, 60 * SEC), SEC)!!.lat shouldBe a.lat
    }

    @Test
    fun `normalisation follows 6_2`() {
        cleaner.normalise(-100.0, 600.0) shouldBe (-100.0 + 35 * log10(2.0) plusOrMinus 1e-9)
        Cleaner(AnalysisConfig.forPreset(uz.sectorverify.model.AnalysisPreset.RURAL)).normalise(-100.0, 600.0) shouldBe
            (-100.0 + 30 * log10(2.0) plusOrMinus 1e-9)
    }
}
