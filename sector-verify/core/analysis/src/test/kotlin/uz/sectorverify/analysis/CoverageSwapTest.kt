package uz.sectorverify.analysis

import io.kotest.matchers.collections.shouldContainExactly
import io.kotest.matchers.nulls.shouldBeNull
import io.kotest.matchers.nulls.shouldNotBeNull
import io.kotest.matchers.shouldBe
import org.junit.jupiter.api.Test
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.Rat

class CoverageSwapTest {
    private val config = AnalysisConfig()
    private val cov = CoverageCalculator(config)
    private fun key(pci: Int) = CellKey(Rat.LTE, 1300, pci)

    @Test
    fun `sector window is the 18 bins nearest to the plan azimuth`() {
        cov.window(0.0) shouldContainExactly (0..8).toList() + (27..35).toList()
        cov.window(5.0).size shouldBe 18
        cov.window(185.0).first() shouldBe 9
    }

    @Test
    fun `coverage counts bins with at least 3 samples of any listed cell`() {
        val counts = mapOf(key(1) to IntArray(36) { if (it < 18) 3 else 0 }, key(2) to IntArray(36) { if (it == 20) 5 else 2 })
        val covered = cov.coveredBins(counts, listOf(key(1), key(2), key(3)))
        cov.fraction(covered) shouldBe 19.0 / 36
        cov.coveredBins(counts, listOf(key(2))).count { it } shouldBe 1
        val s = cov.sector(90.0, covered)
        s.fraction shouldBe 1.0
        s.missingBins shouldBe emptyList()
        cov.sector(270.0, covered).missingBins.size shouldBe 17
    }

    @Test
    fun `three sector rotation is detected with mapping`() {
        val d = SwapDetector(config)
        val entries = listOf(
            SwapEntry(key(1), "S1", 0.0, 122.0),
            SwapEntry(key(2), "S2", 120.0, 238.0),
            SwapEntry(key(3), "S3", 240.0, 3.0),
        )
        val r = d.detect(entries).shouldNotBeNull()
        r.mapping shouldBe mapOf(key(1) to "S2", key(2) to "S3", key(3) to "S1")
        (r.costIdentity >= 4 * r.costBest + 1) shouldBe true
    }

    @Test
    fun `no swap when the plan already fits or the evidence is weak`() {
        val d = SwapDetector(config)
        d.detect(listOf(SwapEntry(key(1), "S1", 0.0, 5.0), SwapEntry(key(2), "S2", 120.0, 110.0))).shouldBeNull()
        // Better under swap, but one error exceeds 30° → not a confident swap.
        d.detect(listOf(SwapEntry(key(1), "S1", 0.0, 80.0), SwapEntry(key(2), "S2", 120.0, 0.0))).shouldBeNull()
        // Sectors 20° apart: cost(id) = 288 < 4 · cost(swap) + 1 = 513.
        d.detect(listOf(SwapEntry(key(1), "S1", 0.0, 12.0), SwapEntry(key(2), "S2", 20.0, 8.0))).shouldBeNull()
        // Same geometry with stronger evidence: 392 ≥ 4 · 72 + 1 → swap.
        d.detect(listOf(SwapEntry(key(1), "S1", 0.0, 14.0), SwapEntry(key(2), "S2", 20.0, 6.0))).shouldNotBeNull()
        d.detect(listOf(SwapEntry(key(1), "S1", 0.0, 120.0))).shouldBeNull()
        d.detect((1..7).map { SwapEntry(key(it), "S$it", it * 50.0, it * 50.0) }).shouldBeNull()
    }

    @Test
    fun `two cells with the same label on one ARFCN never produce an empty mapping`() {
        val d = SwapDetector(config)
        d.detect(listOf(SwapEntry(key(1), "S1", 0.0, 120.0), SwapEntry(key(2), "S1", 120.0, 0.0))).shouldBeNull()
    }
}
