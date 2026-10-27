package uz.sectorverify.feature.settings

import io.kotest.matchers.shouldBe
import org.junit.jupiter.api.Test
import uz.sectorverify.model.AnalysisConfig

class ThresholdsTest {
    @Test
    fun `fields round-trip and apply to the base config`() {
        val base = AnalysisConfig(seed = 5)
        val t = Thresholds.of(base).copy(rMaxM = "600", pathLossExponent = "3,2")
        val c = t.applyTo(base).getOrThrow()
        c.rMaxM shouldBe 600.0
        c.pathLossExponent shouldBe 3.2
        c.seed shouldBe 5
    }

    @Test
    fun `invalid input is rejected`() {
        val base = AnalysisConfig()
        Thresholds.of(base).copy(rMaxM = "abc").applyTo(base).isFailure shouldBe true
        Thresholds.of(base).copy(minOverallCoverage = "1.5").applyTo(base).isFailure shouldBe true
        Thresholds.of(base).copy(passMaxErrDeg = "50").applyTo(base).isFailure shouldBe true
    }
}
