package uz.rostor.rostor2

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import uz.rostor.rostor2.crypto.Hybrid
import uz.rostor.rostor2.crypto.toHex
import uz.rostor.rostor2.report.ReportCodec
import java.io.File
import java.util.Base64

/** F3: hisobot formati, Python vositasi (tools/rostor_report) bilan ikki tomonlama moslik. */
class ReportCodecTest {
    private val dbKat = JSONObject(javaClass.classLoader!!.getResource("db-kat.json")!!.readText())
    private val kat = JSONObject(javaClass.classLoader!!.getResource("report-kat.json")!!.readText())
    private val edSeed = ByteArray(32) { it.toByte() }
    private val mlSeed = ByteArray(32) { (it + 32).toByte() }

    private val input = ReportCodec.Input(
        category = "T2", targetType = "phone", targetValue = "90 123 45 67", claimedOrg = "Uzcard",
        amountUzs = 1_500_000, description = "Xavfsizlik xizmati deb SMS kod so'radi",
        evidence = listOf("call" to "+998 90 123 45 67", "sms_text" to "Kartangiz bloklandi"),
        findings = listOf("text.otp_request" to "SMS kodni so'rash"),
    )

    private fun make() = ReportCodec.create(input, edSeed, mlSeed, "00".repeat(16), 1_790_000_000, "test", 1)

    @Test fun seedDerivationMatchesPython() {
        // BouncyCastle urug'dan kalit hosil qilishi Python cryptography (FIPS 204 ξ) bilan bir xil.
        val (ed, ml) = Hybrid.publicKeys(edSeed, mlSeed)
        assertEquals(dbKat.getString("ed25519_pk"), ed.toHex())
        assertEquals(dbKat.getString("mldsa65_pk"), ml.toHex())
        assertEquals(kat.getString("device_id"), ReportCodec.deviceId(ed, ml))
    }

    @Test fun pythonReportVerifiesInKotlin() {
        val v = ReportCodec.verify(kat.getString("report"))
        assertTrue(v.error, v.ok)
        assertEquals(kat.getString("target_value_hash"), v.content!!.getString("target_value_hash"))
        assertEquals(kat.getString("target_value_hash"), ReportCodec.targetHash("phone", "+998901234567"))
    }

    @Test fun kotlinReportVerifiesAndIsReadable() {
        val f = make()
        val v = ReportCodec.verify(f.toString())
        assertTrue(v.error, v.ok)
        val c = v.content!!
        assertEquals("+998901234567", c.getString("target_value"))
        assertEquals(kat.getString("device_id"), c.getString("device_id"))
        val text = f.getString("readable")
        assertTrue(text, text.contains("+998 90 123 45 67"))
        assertTrue(text.contains("Uzcard"))
        assertTrue(text, text.contains("- SMS kodni so'rash"))
        assertFalse(text, text.contains("text.otp_request"))
        assertTrue(text, text.contains("1 500 000 so'm"))
        assertTrue(text.contains("\"Bank xavfsizlik xizmati\" qo'ng'irog'i"))
        // Python vositasi bilan qo'lda tekshirish uchun (tools/rostor_report verify).
        File(System.getProperty("java.io.tmpdir"), "rostor2-report-from-kotlin.json").writeText(f.toString(1))
    }

    @Test fun tamperingIsDetected() {
        val f = make()
        val c = JSONObject(String(Base64.getDecoder().decode(f.getString("content"))))
        c.put("target_value", "+998900000000")
        val t1 = JSONObject(f.toString()).put("content", Base64.getEncoder().encodeToString(c.toString().toByteArray()))
        assertFalse(ReportCodec.verify(t1.toString()).ok)
        // Boshqa qurilma kalitini qo'yish ham ishlamaydi.
        val other = ReportCodec.create(input, ByteArray(32) { 7 }, ByteArray(32) { 9 }, "11".repeat(16), 1, "t", 1)
        val t2 = JSONObject(f.toString()).put("ed25519_pk", other.getString("ed25519_pk")).put("mldsa65_pk", other.getString("mldsa65_pk"))
        assertFalse(ReportCodec.verify(t2.toString()).ok)
        // readable imzolanmaydi: uni o'zgartirish imzoni buzmaydi, lekin tekshiruv faqat content'ga tayanadi.
        val t3 = JSONObject(f.toString()).put("readable", "soxta matn")
        assertTrue(ReportCodec.verify(t3.toString()).ok)
        assertFalse(ReportCodec.verify("{}").ok)
    }

    @Test fun targetNormalization() {
        assertEquals("click-bonus.top", ReportCodec.normalizeTarget("link", "https://www.Click-Bonus.top/login?x=1"))
        assertEquals("click-bonus.top", ReportCodec.normalizeTarget("link", "click-bonus.top"))
        assertEquals("8600123456789012", ReportCodec.normalizeTarget("card", "8600 1234 5678 9012"))
        assertEquals("uzcard_help", ReportCodec.normalizeTarget("telegram", "@Uzcard_Help"))
        assertEquals("uzcard_help", ReportCodec.normalizeTarget("telegram", "https://t.me/uzcard_help"))
        for ((t, v) in listOf("phone" to "abc", "link" to "nodot", "card" to "1234", "apk" to "zz", "telegram" to "@a")) {
            try { ReportCodec.normalizeTarget(t, v); fail("$t:$v") } catch (e: ReportCodec.InvalidInput) {}
        }
        try { ReportCodec.create(input.copy(category = "T9"), edSeed, mlSeed, "00".repeat(16), 1, "t", 1); fail() } catch (e: ReportCodec.InvalidInput) {}
    }
}
