package uz.sectorverify.analysis

import io.kotest.matchers.doubles.plusOrMinus
import io.kotest.matchers.nulls.shouldBeNull
import io.kotest.matchers.nulls.shouldNotBeNull
import io.kotest.matchers.shouldBe
import io.kotest.property.Arb
import io.kotest.property.arbitrary.double
import io.kotest.property.arbitrary.int
import io.kotest.property.arbitrary.list
import io.kotest.property.checkAll
import kotlin.random.Random
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Test
import uz.sectorverify.model.AnalysisConfig

class EstimatorTest {
    private val config = AnalysisConfig()
    private val fitter = PatternFitter(config)

    private fun idealBins(alpha: Double, p0: Double = -85.0, hpbw: Double = 65.0, skip: Set<Int> = emptySet()) =
        (0 until 36).filter { it !in skip }.map { i ->
            val c = i * 10 + 5.0
            Bin(i, c, p0 + fitter.pattern(c - alpha, hpbw), 10)
        }

    @Test
    fun `pattern follows 6_3`() {
        fitter.pattern(0.0, 65.0) shouldBe (0.0 plusOrMinus 1e-12)
        fitter.pattern(65.0, 65.0) shouldBe -12.0
        fitter.pattern(-65.0, 65.0) shouldBe -12.0
        fitter.pattern(180.0, 65.0) shouldBe -30.0
        fitter.pattern(350.0, 65.0) shouldBe (-12.0 * (10.0 / 65.0) * (10.0 / 65.0) plusOrMinus 1e-12)
    }

    @Test
    fun `noise-free bins recover the azimuth exactly`() {
        for (alpha in listOf(0.0, 47.0, 123.0, 359.0)) {
            val fit = fitter.fit(idealBins(alpha), 65.0)
            fit.alphaDeg shouldBe alpha
            fit.p0 shouldBe (-85.0 plusOrMinus 1e-9)
            fit.rmseDb shouldBe (0.0 plusOrMinus 1e-9)
        }
        CentroidEstimator.estimate(idealBins(47.0)) shouldBe (47.0 plusOrMinus 1.0)
        CentroidEstimator.estimate(idealBins(355.0)) shouldBe (355.0 plusOrMinus 1.0)
    }

    @Test
    fun `method A is invariant to rotating every bin`() = runBlocking {
        checkAll(60, Arb.list(Arb.double(-120.0, -60.0), 36..36), Arb.int(0, 359)) { values, theta ->
            val bins = values.mapIndexed { i, v -> Bin(i, i * 10 + 5.0, v, 3 + i % 5) }
            val rotated = bins.map { it.copy(centerDeg = it.centerDeg + theta) }
            val a = fitter.fit(bins, 65.0).alphaDeg
            val b = fitter.fit(rotated, 65.0).alphaDeg
            Angles.diff(b, a + theta) shouldBe (0.0 plusOrMinus 1e-9)
        }
    }

    @Test
    fun `estimate combines A, B and the bootstrap`() {
        val est = AzimuthEstimator(config).estimate(idealBins(200.0), 65.0, 50, Random(1)).shouldNotBeNull()
        est.alphaDeg shouldBe 200.0
        est.ciHalfDeg shouldBe 0.0
        est.ciLowDeg shouldBe 200.0
        est.nBins shouldBe 36
        est.nSamples shouldBe 360
        est.unreliable shouldBe false
        AzimuthEstimator(config).estimate(idealBins(200.0).take(5), 65.0, 50, Random(1)).shouldBeNull()
    }

    @Test
    fun `A and B disagreeing by more than 30 degrees marks the estimate unreliable`() {
        // Strong back-lobe bins pull the centroid (B) away while the curvature fit (A) keeps the main lobe.
        val bins = idealBins(90.0).map { if (it.index in 25..27) it.copy(median = -80.0) else it }
        val est = AzimuthEstimator(config).estimate(bins, 65.0, 0, Random(1)).shouldNotBeNull()
        est.unreliable shouldBe true
    }

    @Test
    fun `bootstrap percentiles use linear interpolation`() {
        val s = doubleArrayOf(1.0, 2.0, 3.0, 4.0, 5.0)
        Bootstrap.percentile(s, 0.0) shouldBe 1.0
        Bootstrap.percentile(s, 50.0) shouldBe 3.0
        Bootstrap.percentile(s, 100.0) shouldBe 5.0
        Bootstrap.percentile(s, 2.5) shouldBe (1.1 plusOrMinus 1e-12)
        Bootstrap(config, fitter).ci(idealBins(10.0), 65.0, 10.0, 0, Random(1)) shouldBe BootstrapCi(0.0, 0.0)
        BootstrapCi(-12.0, 7.0).halfDeg shouldBe 12.0
    }

    @Test
    fun `noisy bootstrap is deterministic for a seed`() {
        val r = Random(5)
        val noisy = idealBins(150.0).map { it.copy(median = it.median + r.nextDouble(-6.0, 6.0)) }
        val e1 = AzimuthEstimator(config).estimate(noisy, 65.0, 200, Random(9))!!
        val e2 = AzimuthEstimator(config).estimate(noisy, 65.0, 200, Random(9))!!
        e1 shouldBe e2
        e1.alphaDeg shouldBe (150.0 plusOrMinus 10.0)
        (e1.ciHalfDeg > 0.0) shouldBe true
    }

    @Test
    fun `binner uses median and drops sparse bins`() {
        val b = Binner(config)
        b.index(0.0) shouldBe 0
        b.index(359.99) shouldBe 35
        b.index(-5.0) shouldBe 35
        b.center(3) shouldBe 35.0
        Binner.median(listOf(3.0, 1.0, 2.0)) shouldBe 2.0
        Binner.median(listOf(4.0, 1.0, 2.0, 3.0)) shouldBe 2.5
        val key = Fixtures.sample(0).key
        fun s(bearing: Double, y: Double) = CleanSample(key, 0, 300.0, bearing, y, y, false)
        val bins = b.bins(listOf(s(1.0, -90.0), s(2.0, -80.0), s(3.0, -70.0), s(15.0, -60.0)))
        bins.size shouldBe 1
        bins[0].median shouldBe -80.0
        bins[0].count shouldBe 3
        b.counts(listOf(s(1.0, 0.0), s(15.0, 0.0)))[1] shouldBe 1
    }
}
