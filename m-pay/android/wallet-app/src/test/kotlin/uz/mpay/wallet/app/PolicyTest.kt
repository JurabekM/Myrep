package uz.mpay.wallet.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Manba siyosatlari: islomiy grafika qoidasi (jonzot, piggy bank, qimor, alkogol, bank binosi va foiz
 * belgilari yo'q), uch tilda bir xil matn kalitlari va formatlar, release'da sinov ko'prigi yo'q.
 */
class PolicyTest {
    private val src = File("src")

    private fun files(ext: String) = src.walkTopDown().filter { it.isFile && it.extension == ext }.toList()

    @Test
    fun iconPolicy() {
        val deny = Regex(
            "Savings|Person|People|Group|Face|AccountCircle|Pets|Child|Mood|Sentiment|Emoji|Casino|Dice|WineBar|LocalBar|" +
                "SportsBar|Liquor|Nightlife|Church|Mosque|Temple|AccountBalance|Percent|Cake|BugReport|Pig",
        )
        val icon = Regex("""Icons\.(?:AutoMirrored\.)?(?:Default|Filled|Outlined|Rounded|Sharp|TwoTone)\.(\w+)""")
        val bad = files("kt").flatMap { f -> icon.findAll(f.readText()).map { it.groupValues[1] }.filter { deny.containsMatchIn(it) }.map { "${f.name}: $it" } }
        assertTrue("taqiqlangan ikonkalar: $bad", bad.isEmpty())
        val drawables = files("xml").filter { it.parentFile.name.startsWith("drawable") }.map { it.name }
        assertTrue(drawables.toString(), drawables.none { deny.containsMatchIn(it.replaceFirstChar(Char::uppercase)) })
    }

    private fun strings(dir: String): Map<String, String> {
        val re = Regex("""<string name="([a-z0-9_]+)">(.*?)</string>""")
        return re.findAll(File(src, "main/res/$dir/strings.xml").readText()).associate { it.groupValues[1] to it.groupValues[2] }
    }

    @Test
    fun stringsParity() {
        val uz = strings("values")
        assertTrue(uz.size > 100)
        val fmt = Regex("""%\d\$[sd]""")
        for (lang in listOf("values-ru", "values-en")) {
            val other = strings(lang)
            assertEquals("$lang kalitlari", uz.keys, other.keys)
            for ((k, v) in uz) {
                assertEquals("$lang/$k formatlari", fmt.findAll(v).map { it.value }.toSet(), fmt.findAll(other.getValue(k)).map { it.value }.toSet())
                assertTrue("$lang/$k bo'sh", other.getValue(k).isNotBlank())
            }
        }
        // Ochiq apostrof — aapt xatosi yoki matn kesilishi.
        val raw = Regex("""(?<!\\)'""")
        listOf("values", "values-ru", "values-en").forEach { d ->
            strings(d).forEach { (k, v) -> assertTrue("$d/$k: ochiq apostrof", !raw.containsMatchIn(v)) }
        }
    }

    @Test
    fun virtualNfcOnlyInDebug() {
        val main = files("kt").filter { it.path.contains("main") }
        assertTrue(main.none { it.readText().contains("class VirtualNfcService") })
        assertTrue(File(src, "debug/kotlin/uz/mpay/wallet/app/VirtualNfcService.kt").isFile)
        assertTrue(!File(src, "main/AndroidManifest.xml").readText().contains("VirtualNfcService"))
    }

    @Test
    fun noSecretsInLogs() {
        // Log chaqiruvlarida PAN/kalit/OTP o'zgaruvchilari yo'q (faqat sinf nomi va kodlar).
        val log = Regex("""Log\.[diwe]\([^)]*\b(pan|otp|pin|luk|key|dpan|fpan)\b""", RegexOption.IGNORE_CASE)
        val bad = files("kt").filter { log.containsMatchIn(it.readText()) }.map { it.name }
        assertTrue("logda sir bo'lishi mumkin: $bad", bad.isEmpty())
    }
}
