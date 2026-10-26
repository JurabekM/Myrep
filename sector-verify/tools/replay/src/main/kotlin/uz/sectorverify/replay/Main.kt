package uz.sectorverify.replay

import java.io.File
import kotlin.system.exitProcess

private const val USAGE = """sv-replay — Sector Verify sessiyalarini qayta tahlil qilish
  analyze <session.zip> [--config cfg.json] [--out report.json]
  calibrate <zip-papka> <ground_truth.csv> [--out papka] [--quick]
  verify <session.zip>
  simulate <papka> [--n 20] [--seed 1]"""

private class UsageException : RuntimeException()

/** Returns the process exit code: 0 ok, 1 verification/analysis failure, 2 usage error. */
fun runCli(args: List<String>, print: (String) -> Unit = ::println): Int = try {
    val (positional, options, flags) = parseArgs(args)
    fun arg(i: Int): File = File(positional.getOrNull(i) ?: throw UsageException())
    when (positional.firstOrNull()) {
        "analyze" -> {
            Analyze.run(arg(1), loadConfig(options["--config"]?.let(::File)), options["--out"]?.let(::File), print)
            0
        }
        "calibrate" -> {
            val dir = arg(1)
            val outcome = Calibrate.run(dir, arg(2), File(options["--out"] ?: dir.path), "--quick" in flags, print = print)
            if (outcome.feasible) 0 else 1
        }
        "verify" -> if (Verify.run(arg(1), print)) 0 else 1
        "simulate" -> {
            Simulate.run(arg(1), options["--n"]?.toInt() ?: DEFAULT_N, options["--seed"]?.toLong() ?: 1L, print)
            0
        }
        else -> throw UsageException()
    }
} catch (ignored: UsageException) {
    print(USAGE.trimIndent())
    2
} catch (e: IllegalArgumentException) {
    print("Xato: ${e.message}")
    1
} catch (e: java.io.IOException) {
    print("Xato: ${e.message}")
    1
}

private val FLAGS = setOf("--quick")

/** Splits arguments into positionals, `--name value` options and boolean flags. */
internal fun parseArgs(args: List<String>): Triple<List<String>, Map<String, String>, Set<String>> {
    val positional = ArrayList<String>()
    val options = HashMap<String, String>()
    val flags = HashSet<String>()
    var i = 0
    while (i < args.size) {
        val a = args[i]
        when {
            a in FLAGS -> flags += a
            a.startsWith("--") -> {
                require(i + 1 < args.size) { "$a uchun qiymat yo'q" }
                options[a] = args[++i]
            }
            else -> positional += a
        }
        i++
    }
    return Triple(positional, options, flags)
}

private const val DEFAULT_N = 20

fun main(args: Array<String>) {
    exitProcess(runCli(args.toList()))
}
