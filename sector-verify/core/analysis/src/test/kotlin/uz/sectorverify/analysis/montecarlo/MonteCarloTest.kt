package uz.sectorverify.analysis.montecarlo

import io.kotest.matchers.doubles.shouldBeGreaterThanOrEqual
import io.kotest.matchers.doubles.shouldBeLessThanOrEqual
import io.kotest.matchers.shouldBe
import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test

/** Har biri 200 ta simulyatsiya sessiyasida AC-01…AC-04 (CI). 1000 iteratsiyali varianti "slow" tegi bilan belgilangan. */
class MonteCarloTest {
    @Test
    fun `acceptance criteria hold on 200 simulated sessions`() = check(200, "montecarlo.md")

    @Test
    @Tag("slow")
    fun `acceptance criteria hold on 1000 simulated sessions`() = check(1000, "montecarlo-1000.md")

    private fun check(n: Int, file: String) {
        val ac = listOf(MonteCarlo.ac01(n).first, MonteCarlo.ac02(n).first, MonteCarlo.ac03(n).first, MonteCarlo.ac04(n).first)
        println(MonteCarlo.report(ac, n, file))
        ac[0].value shouldBeGreaterThanOrEqual 0.95
        ac[1].value shouldBeLessThanOrEqual 0.03
        ac[2].value shouldBeLessThanOrEqual 10.0
        ac[3].value shouldBe 1.0
    }
}
