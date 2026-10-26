package uz.sectorverify.format

import io.kotest.matchers.shouldBe
import io.kotest.matchers.string.shouldContain
import java.io.ByteArrayInputStream
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.jupiter.api.Test
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.AzimuthEstimate
import uz.sectorverify.model.CauseCode
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.CleaningStats
import uz.sectorverify.model.DeviceCapabilities
import uz.sectorverify.model.Finding
import uz.sectorverify.model.FindingType
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Rat
import uz.sectorverify.model.Sector
import uz.sectorverify.model.SectorResult
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionResult
import uz.sectorverify.model.SessionStatus
import uz.sectorverify.model.Severity
import uz.sectorverify.model.SitePlan
import uz.sectorverify.model.Verdict

class SessionFormatTest {
    private val plan = SitePlan("NAV-0123", "Navoiy", 40.1032, 65.3685, "43405", listOf(Sector("S1", Rat.LTE, "B3", 1300, 141, 0.0)))
    private val samples = listOf(
        CellSample(1, Rat.LTE, 1300, 141, true, -90.0, -10.0, 5.5, 3, 12345, 101, 2),
        CellSample(2, Rat.NR, 636666, 7, false, null, null, null, null, null, null, null),
    )
    private val fixes = listOf(GnssFix(1, 1_790_000_000_000, 40.1, 65.3, 4.5, 1.4, 90.0), GnssFix(2, 1_790_000_001_000, 40.2, 65.4, 3.0))
    private val meta = SessionMeta(
        id = "6b1f8c1e-0000-4000-8000-000000000001",
        siteCode = plan.code,
        mode = SessionMode.FULL,
        startedAtUtcMs = 1_790_000_000_000,
        endedAtUtcMs = 1_790_000_900_000,
        deviceModel = "Pixel 8",
        apiLevel = 35,
        appVersion = "1.0.0",
        algoVersion = "1.0.0",
        measuredRateHz = 0.98,
        status = SessionStatus.DONE,
        config = AnalysisConfig(seed = 3),
    )
    private val est = AzimuthEstimate(3.04, 355.0, 9.0, 8.0, 5.0, 4.2, 300, 30, false)
    private val result = SessionResult(
        siteCode = plan.code,
        verdict = Verdict.PASS,
        sectors = listOf(
            SectorResult(CellKey(Rat.LTE, 1300, 141), "S1", 0.0, est, 3.04, 300, 1.0, emptyList(), Verdict.PASS, CauseCode.NONE),
        ),
        findings = listOf(Finding(FindingType.PCI_UNEXPECTED, Severity.INFO, mapOf("pci" to "9"))),
        overallCoverage = 0.8333,
        coveredBins = List(36) { true },
        cleaning = CleaningStats(10, 1, 0, 0, 0, 0, 9),
        seed = 3,
        algoVersion = "1.0.0",
    )

    @Test
    fun `samples and fixes round-trip through CSV`() {
        SessionCsv.readSamples(buildString { SessionCsv.writeSamples(samples, this) }) shouldBe samples
        SessionCsv.readFixes(buildString { SessionCsv.writeFixes(fixes, this) }) shouldBe fixes
        SessionCsv.readSamples("") shouldBe emptyList()
    }

    @Test
    fun `report json follows schema v1 and is signed and verified`() {
        val report = ReportJson.build(plan, meta, result)
        report["schema"]!!.jsonPrimitive.content shouldBe ReportJson.SCHEMA
        val sector = (report["sectors"] as kotlinx.serialization.json.JsonArray).first().jsonObject
        sector["estAzimuth"]!!.jsonPrimitive.content shouldBe "3.0"
        report["session"]!!.jsonObject["coveragePct"]!!.jsonPrimitive.content shouldBe "83.3"
        report["session"]!!.jsonObject["startedAt"]!!.jsonPrimitive.content shouldBe "2026-09-21T14:13:20Z"

        val sealed = ReportIntegrity.seal(report, TestSigner)
        val text = ReportJson.toText(sealed)
        text shouldContain ReportJson.KEY_ALG
        ReportIntegrity.verify(text).ok shouldBe true

        val tampered = text.replace("\"PASS\"", "\"FAIL\"")
        ReportIntegrity.verify(tampered).let {
            it.hashOk shouldBe false
            it.signatureOk shouldBe false
            it.ok shouldBe false
        }
        ReportIntegrity.verify(ReportJson.toText(report)).message shouldBe "integrity bloki yo'q"
        ReportIntegrity.verify("{").ok shouldBe false
        val noChain = JsonObject(sealed + ("integrity" to JsonObject(sealed["integrity"]!!.jsonObject - "attestationChain")))
        ReportIntegrity.verify(ReportJson.toText(noChain)).message shouldBe "sertifikat zanjiri yo'q"
    }

    @Test
    fun `canonical form sorts keys and ignores whitespace`() {
        val a = ReportJson.parse("""{"b": 1.50, "a": {"y": [1, 2], "x": "s"}}""")
        String(CanonicalJson.bytes(a)) shouldBe """{"a":{"x":"s","y":[1,2]},"b":1.50}"""
        CanonicalJson.sha256Hex("abc".toByteArray()) shouldBe "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        CanonicalJson.canonicalize(JsonPrimitive(1)) shouldBe JsonPrimitive(1)
    }

    @Test
    fun `session zip round-trips`() {
        val caps = DeviceCapabilities("Pixel 8", "Google", 35, "Tensor G3", null, 60, 1.0, true, true, true, false, 1_790_000_000_000)
        val export = SessionExport(plan, samples, fixes, meta, "{}", byteArrayOf(1, 2, 3), caps)
        val back = SessionZip.read(ByteArrayInputStream(SessionZip.toBytes(export)))
        back shouldBe export
        back.hashCode() shouldBe export.hashCode()
        val minimal = export.copy(reportJson = null, reportPdf = null, capabilities = null)
        SessionZip.read(ByteArrayInputStream(SessionZip.toBytes(minimal))) shouldBe minimal
        (minimal == export) shouldBe false
    }

    @Test
    fun `config json import ignores unknown keys`() {
        val c = SvJson.parseConfig("""{"rMaxM": 600.0, "unknown": 1}""")
        c.rMaxM shouldBe 600.0
        SvJson.parseConfig(SvJson.configToJson(c)) shouldBe c
    }
}
