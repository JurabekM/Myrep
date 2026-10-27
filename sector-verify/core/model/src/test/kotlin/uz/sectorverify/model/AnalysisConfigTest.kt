package uz.sectorverify.model

import io.kotest.matchers.collections.shouldBeEmpty
import io.kotest.matchers.collections.shouldNotBeEmpty
import io.kotest.matchers.shouldBe
import kotlinx.serialization.json.Json
import org.junit.jupiter.api.Test

class AnalysisConfigTest {
    @Test
    fun `defaults are valid and match the spec`() {
        val c = AnalysisConfig()
        c.validate().shouldBeEmpty()
        c.nBins shouldBe 36
        c.rMaxM shouldBe 1500.0
        c.pathLossExponent shouldBe 3.5
        c.bootstrapIterations shouldBe 200
    }

    @Test
    fun `presets change only their parameter`() {
        AnalysisConfig.forPreset(AnalysisPreset.URBAN).rMaxM shouldBe 600.0
        AnalysisConfig.forPreset(AnalysisPreset.RURAL).pathLossExponent shouldBe 3.0
        AnalysisConfig.forPreset(AnalysisPreset.SUBURBAN) shouldBe AnalysisConfig()
    }

    @Test
    fun `invalid configs are reported`() {
        AnalysisConfig(binDeg = 7).validate().shouldNotBeEmpty()
        AnalysisConfig(rMinM = 500.0, rMaxM = 400.0).validate().shouldNotBeEmpty()
        AnalysisConfig(ciLowPercentile = 99.0, ciHighPercentile = 1.0).validate().shouldNotBeEmpty()
        AnalysisConfig(swapMaxSectors = 1).validate().shouldNotBeEmpty()
        AnalysisConfig(minOverallCoverage = 1.5).validate().shouldNotBeEmpty()
        AnalysisConfig(alphaStepDeg = 0.0, minPerBin = 0, minBinsForFit = 1, bootstrapIterations = -1, dRefM = 0.0, patternCoef = 0.0)
            .validate().size shouldBe 6
    }

    @Test
    fun `config round-trips through JSON`() {
        val c = AnalysisConfig(seed = 7, preset = AnalysisPreset.URBAN)
        Json.decodeFromString<AnalysisConfig>(Json.encodeToString(AnalysisConfig.serializer(), c)) shouldBe c
    }

    @Test
    fun `cell key ordering and pci limits`() {
        val a = CellKey(Rat.LTE, 1300, 10)
        val b = CellKey(Rat.LTE, 1300, 11)
        (a < b) shouldBe true
        a.toString() shouldBe "LTE/1300/10"
        Rat.LTE.maxPci shouldBe 503
        Rat.NR.maxPci shouldBe 1007
        val s = Sector("S1", Rat.LTE, "B3", 1300, 10, 0.0)
        s.hpbwDeg shouldBe 65.0
        SitePlan("X", "X", 0.0, 0.0, "43405", listOf(s)).sectorFor(a) shouldBe s
    }
}
