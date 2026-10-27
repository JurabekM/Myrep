package uz.sectorverify.replay

import io.kotest.matchers.collections.shouldContain
import io.kotest.matchers.shouldBe
import io.kotest.matchers.string.shouldContain
import java.io.File
import java.security.KeyFactory
import java.security.Signature
import java.security.spec.PKCS8EncodedKeySpec
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import uz.sectorverify.analysis.SessionAnalyzer
import uz.sectorverify.analysis.sim.Fault
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.format.ReportIntegrity
import uz.sectorverify.format.ReportJson
import uz.sectorverify.format.ReportSigner
import uz.sectorverify.format.SessionExport
import uz.sectorverify.format.SessionMeta
import uz.sectorverify.format.SessionZip
import uz.sectorverify.format.SvJson
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.Rat
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionStatus

class ReplayCliTest {
    private val out = ArrayList<String>()
    private val print: (String) -> Unit = { out += it }

    /** Test resurslaridagi faqat testlar uchun EC P-256 kalit. */
    private object Signer : ReportSigner {
        private fun res(n: String) = requireNotNull(Signer::class.java.getResourceAsStream("/$n")).readBytes()
        private val key = KeyFactory.getInstance("EC").generatePrivate(PKCS8EncodedKeySpec(res("test-key.pk8")))

        override fun sign(data: ByteArray): ByteArray = Signature.getInstance("SHA256withECDSA").run {
            initSign(key)
            update(data)
            sign()
        }

        override fun certificateChain() = listOf(res("test-cert.der"))
    }

    private fun meta(code: String, config: AnalysisConfig) = SessionMeta(
        id = "s1",
        siteCode = code,
        mode = SessionMode.FULL,
        startedAtUtcMs = 1,
        deviceModel = "t",
        apiLevel = 34,
        appVersion = "t",
        algoVersion = "1.0.0",
        status = SessionStatus.DONE,
        config = config,
    )

    private fun signedZip(dir: File): File {
        val sim = Simulator.run(SimScenario(seed = 303, fault = Fault.FullSwap(listOf(0, 1, 2))))
        val config = AnalysisConfig(bootstrapIterations = 30)
        val meta = meta(sim.plan.code, config)
        val result = SessionAnalyzer(config).analyze(sim.plan, sim.samples, sim.fixes)
        val json = ReportJson.toText(ReportIntegrity.seal(ReportJson.build(sim.plan, meta, result), Signer))
        val export = SessionExport(sim.plan, sim.samples, sim.fixes, meta, json)
        return File(dir, "s1.zip").also { f -> f.outputStream().use { SessionZip.write(export, it) } }
    }

    @Test
    fun `analyze re-runs the stored session and writes report json`(@TempDir dir: File) {
        val zip = signedZip(dir)
        runCli(listOf("analyze", zip.path), print) shouldBe 0
        out.joinToString("\n") shouldContain "verdikt FAIL"
        File(dir, "s1.replay.json").readText() shouldContain ReportJson.SCHEMA
        val cfg = File(dir, "cfg.json").apply { writeText(SvJson.configToJson(AnalysisConfig(bootstrapIterations = 10, rMaxM = 1200.0))) }
        runCli(listOf("analyze", zip.path, "--config", cfg.path, "--out", File(dir, "o.json").path), print) shouldBe 0
        File(dir, "o.json").readText() shouldContain "1200.0"
    }

    @Test
    fun `verify accepts the original and rejects a tampered report`(@TempDir dir: File) {
        val zip = signedZip(dir)
        runCli(listOf("verify", zip.path), print) shouldBe 0
        val export = zip.inputStream().use { SessionZip.read(it) }
        val bad = File(dir, "bad.zip")
        bad.outputStream().use { SessionZip.write(export.copy(reportJson = export.reportJson!!.replace("\"FAIL\"", "\"PASS\"")), it) }
        runCli(listOf("verify", bad.path), print) shouldBe 1
        val none = File(dir, "none.zip")
        none.outputStream().use { SessionZip.write(export.copy(reportJson = null), it) }
        runCli(listOf("verify", none.path), print) shouldBe 1
        out shouldContain "report.json yo'q"
    }

    @Test
    fun `calibrate runs on simulator ZIPs and writes a valid recommended config`(@TempDir dir: File) {
        runCli(listOf("simulate", dir.path, "--n", "8", "--seed", "77"), print) shouldBe 0
        val truth = GroundTruth.parse(File(dir, "ground_truth.csv").readText())
        truth.any { it.isSwap } shouldBe true
        val code =
            runCli(listOf("calibrate", dir.path, File(dir, "ground_truth.csv").path, "--out", File(dir, "cal").path, "--quick"), print)
        code shouldBe 0
        val cfg = SvJson.parseConfig(File(dir, "cal/recommended-config.json").readText())
        cfg.validate() shouldBe emptyList()
        cfg.bootstrapIterations shouldBe AnalysisConfig().bootstrapIterations
        val md = File(dir, "cal/calibration-report.md").readText()
        md shouldContain "AC-08"
        md shouldContain "tavsiya"
    }

    @Test
    fun `metrics and ranking prefer feasible, detecting configs`() {
        val sim = Simulator.run(SimScenario(seed = 303, fault = Fault.FullSwap(listOf(0, 1, 2))))
        val truth = sim.plan.sectors.map { TruthRow(sim.plan.code, it.key, sim.trueAzimuth[it.key], true, "SWAP") }
        val export = SessionExport(sim.plan, sim.samples, sim.fixes, meta(sim.plan.code, AnalysisConfig()))
        val m = Calibrate.evaluate(AnalysisConfig(bootstrapIterations = 20), listOf(export), truth)
        m.swapCells shouldBe 3
        m.detection shouldBe 1.0
        m.healthyCells shouldBe 0
        m.falseFailRate shouldBe 0.0
        val good = Candidate(AnalysisConfig(), Metrics(4, 4, 100, 1, 90, 4.0), 1)
        val noisy = Candidate(AnalysisConfig(), Metrics(4, 4, 100, 10, 80, 4.0), 0)
        val weak = Candidate(AnalysisConfig(), Metrics(4, 2, 100, 0, 95, 4.0), 0)
        Calibrate.rank(listOf(noisy, weak, good)) shouldBe listOf(good, weak, noisy)
        Calibrate.grid(AnalysisConfig(), quick = false).size shouldBe 162
    }

    @Test
    fun `usage, errors and ground truth parsing`(@TempDir dir: File) {
        runCli(emptyList(), print) shouldBe 2
        runCli(listOf("analyze"), print) shouldBe 2
        runCli(listOf("analyze", File(dir, "missing.zip").path), print) shouldBe 1
        runCli(listOf("analyze", "x", "--config"), print) shouldBe 1
        parseArgs(listOf("calibrate", "a", "--out", "o", "--quick", "b")) shouldBe
            Triple(listOf("calibrate", "a", "b"), mapOf("--out" to "o"), setOf("--quick"))
        val text = "site_code;rat;arfcn;pci;true_azimuth_deg;has_fault;fault_type\nA;lte;1300;1;12,5;ha;cell_config_swap\nA;NR;1;2;;0;\n"
        val rows = GroundTruth.parse(text)
        rows[0].key shouldBe CellKey(Rat.LTE, 1300, 1)
        rows[0].trueAzimuthDeg shouldBe 12.5
        rows[0].isSwap shouldBe true
        rows[1].hasFault shouldBe false
        rows[1].faultType shouldBe "NONE"
        GroundTruth.parse(GroundTruth.write(rows)) shouldBe rows
        runCatching { GroundTruth.parse("site_code\nA") }.isFailure shouldBe true
    }
}
