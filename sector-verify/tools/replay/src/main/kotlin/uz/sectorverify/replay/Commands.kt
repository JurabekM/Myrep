package uz.sectorverify.replay

import java.io.File
import kotlin.math.abs
import kotlin.math.roundToInt
import kotlin.random.Random
import uz.sectorverify.analysis.ALGO_VERSION
import uz.sectorverify.analysis.Angles
import uz.sectorverify.analysis.SessionAnalyzer
import uz.sectorverify.analysis.sim.Fault
import uz.sectorverify.analysis.sim.RouteShape
import uz.sectorverify.analysis.sim.SimScenario
import uz.sectorverify.analysis.sim.Simulator
import uz.sectorverify.format.ReportIntegrity
import uz.sectorverify.format.ReportJson
import uz.sectorverify.format.SessionExport
import uz.sectorverify.format.SessionMeta
import uz.sectorverify.format.SessionZip
import uz.sectorverify.format.SvJson
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionResult
import uz.sectorverify.model.SessionStatus

/** `analyze <session.zip> [--config cfg.json] [--out report.json]`: re-runs the analysis on a recorded session. */
object Analyze {
    fun run(zip: File, config: AnalysisConfig?, out: File?, print: (String) -> Unit): SessionResult {
        val export = zip.inputStream().use { SessionZip.read(it) }
        val cfg = config ?: export.meta.config
        val result = SessionAnalyzer(cfg).analyze(export.plan, export.samples, export.fixes)
        print(summary(export, result))
        val target = out ?: File(zip.parentFile, zip.nameWithoutExtension + ".replay.json")
        target.writeText(
            ReportJson.toText(ReportJson.build(export.plan, export.meta.copy(config = cfg, algoVersion = ALGO_VERSION), result)),
        )
        print("report.json → ${target.path} (imzosiz: replay natijasi)")
        return result
    }

    fun summary(e: SessionExport, r: SessionResult): String = buildString {
        appendLine(
            "Sayt ${e.plan.code} · sessiya ${e.meta.id} · verdikt ${r.verdict} · qamrov ${(r.overallCoverage * PERCENT).roundToInt()}%",
        )
        appendLine("Namunalar: ${r.cleaning.total} jami, ${r.cleaning.kept} ishlatildi")
        for (s in r.sectors) {
            val est = s.estimate?.let { "${it.alphaDeg.roundToInt()}° ±${it.ciHalfDeg.roundToInt()}°" } ?: "—"
            appendLine(
                "  %-4s %-16s reja %5s  o'lchov %-10s xato %5s  %-12s %s".format(
                    s.label ?: "?",
                    s.key,
                    s.planAzimuthDeg?.roundToInt() ?: "—",
                    est,
                    s.errorDeg?.roundToInt() ?: "—",
                    s.verdict,
                    s.cause,
                ),
            )
        }
        for (f in r.findings) appendLine("  [${f.severity}] ${f.type} ${f.detail}")
    }

    private const val PERCENT = 100
}

/** `verify <session.zip>`: report.json hash and signature. */
object Verify {
    fun run(zip: File, print: (String) -> Unit): Boolean {
        val export = zip.inputStream().use { SessionZip.read(it) }
        val json = export.reportJson ?: return false.also { print("report.json yo'q") }
        val r = ReportIntegrity.verify(json)
        print("${if (r.ok) "OK" else "XATO"}: ${r.message} (sertifikatlar: ${r.chainLength})")
        r.keyFingerprint?.let { print("Kalit SHA-256: $it") }
        return r.ok
    }
}

/** `simulate <out-dir> [--n N] [--seed S]`: simulator sessions as ZIPs plus ground_truth.csv (testing calibrate). */
object Simulate {
    fun run(dir: File, n: Int, seed: Long, print: (String) -> Unit): List<File> {
        dir.mkdirs()
        val truth = ArrayList<TruthRow>()
        val files = (0 until n).map { i ->
            val r = Random(seed + i)
            val nArfcn = 1 + r.nextInt(2)
            val fault = when (i % FAULT_CYCLE) {
                0 -> Fault.FullSwap(listOf(0, 1))
                1 -> if (nArfcn > 1) Fault.BandSwap(1, 0, 2) else Fault.Rotation(2, ROTATION_DEG)
                else -> Fault.None
            }
            val sim = Simulator.run(
                SimScenario(
                    seed = seed + i,
                    nArfcn = nArfcn,
                    azimuthOffsetDeg = r.nextDouble() * 360,
                    route = if (r.nextBoolean()) RouteShape.RING else RouteShape.SQUARE,
                    radiusM = MIN_RADIUS_M + r.nextDouble() * RADIUS_SPAN_M,
                    coverage = MIN_COVERAGE + r.nextDouble() * (1 - MIN_COVERAGE),
                    gapStartDeg = r.nextDouble() * 360,
                    fault = fault,
                ),
            )
            for (s in sim.plan.sectors) {
                val cause = sim.expected.causes[s.key]
                truth += TruthRow(sim.plan.code, s.key, sim.trueAzimuth[s.key], cause != null, cause?.name ?: "NONE")
            }
            val meta = SessionMeta(
                id = "sim-${seed + i}",
                siteCode = sim.plan.code,
                mode = SessionMode.FULL,
                startedAtUtcMs = SIM_EPOCH_MS,
                endedAtUtcMs = SIM_EPOCH_MS + (sim.durationS * MS).toLong(),
                deviceModel = "simulator",
                apiLevel = 0,
                appVersion = "sim",
                algoVersion = ALGO_VERSION,
                measuredRateHz = 1.0,
                status = SessionStatus.DONE,
                config = AnalysisConfig(),
            )
            File(dir, "${sim.plan.code}.zip").also { f ->
                f.outputStream().use { SessionZip.write(SessionExport(sim.plan, sim.samples, sim.fixes, meta), it) }
            }
        }
        File(dir, "ground_truth.csv").writeText(GroundTruth.write(truth))
        print("${files.size} ta ZIP va ground_truth.csv → ${dir.path}")
        return files
    }

    private const val SIM_EPOCH_MS = 1_790_000_000_000L
    private const val FAULT_CYCLE = 4
    private const val MIN_COVERAGE = 0.75
    private const val MIN_RADIUS_M = 150.0
    private const val RADIUS_SPAN_M = 250.0
    private const val ROTATION_DEG = 30.0
    private const val MS = 1000
}

internal fun absErr(est: Double, truth: Double) = abs(Angles.diff(est, truth))

internal fun loadConfig(file: File?): AnalysisConfig? = file?.let { SvJson.parseConfig(it.readText()) }
