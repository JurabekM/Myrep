package uz.distribos.crypto

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Base64

/**
 * ML-DSA-65 moslik testi.
 *
 * Python OpenSSL orqali imzolaydi, Kotlin BouncyCastle orqali tekshiradi.
 * Ikkalasi ham FIPS 204, lekin bu **avtomatik** moslikni anglatmaydi —
 * kodlash tafsilotlari farq qilishi mumkin. Shuning uchun bu test
 * Python yaratgan HAQIQIY imzolar ustida ishlaydi.
 *
 * Bu yiqilsa: telefon desktop yuborgan hodisani rad etadi, ya'ni
 * sinxronizatsiya umuman ishlamaydi.
 */
class MlDsaInteropTest {

    private val vectors: JSONObject by lazy {
        val stream = requireNotNull(
            javaClass.classLoader?.getResourceAsStream("des1_kat.json")
        ) { "des1_kat.json topilmadi" }
        JSONObject(stream.bufferedReader().use { it.readText() })
    }

    private fun decode(value: String): ByteArray = Base64.getDecoder().decode(value)

    private fun JSONArray.objects(): List<JSONObject> =
        (0 until length()).map { getJSONObject(it) }

    @Test
    fun `python signatures verify in kotlin`() {
        var positive = 0
        var negative = 0

        for (case in vectors.getJSONArray("signatures").objects()) {
            val expectValid = if (case.has("expect_valid")) case.getBoolean("expect_valid") else true
            val valid = MlDsa65.verify(
                decode(case.getString("public_key")),
                decode(case.getString("signature")),
                decode(case.getString("message")),
            )
            assertEquals(
                "imzo tekshiruvi kutilganidan farq qildi: ${case.getString("name")}",
                expectValid, valid,
            )
            if (expectValid) positive++ else negative++
        }

        assertTrue("ijobiy holatlar yo'q", positive >= 4)
        assertTrue("salbiy holatlar yo'q", negative >= 2)
    }

    @Test
    fun `public key size matches spec`() {
        for (case in vectors.getJSONArray("signatures").objects()) {
            assertEquals(
                "ML-DSA-65 ochiq kaliti 1952 bayt bo'lishi kerak",
                MlDsa65.PUBLIC_KEY_SIZE, decode(case.getString("public_key")).size,
            )
            assertEquals(
                "ML-DSA-65 imzosi 3309 bayt bo'lishi kerak",
                MlDsa65.SIGNATURE_SIZE, decode(case.getString("signature")).size,
            )
        }
    }

    @Test
    fun `kotlin can sign and verify its own`() {
        val keys = MlDsa65.generate()
        val message = "DistribOS hodisasi".toByteArray()
        val signature = MlDsa65.sign(keys.privateKey, message)

        assertEquals(MlDsa65.SIGNATURE_SIZE, signature.size)
        assertTrue("o'z imzosi tekshirilmadi", MlDsa65.verify(keys.publicKey, signature, message))
    }

    @Test
    fun `tampered message is rejected`() {
        val keys = MlDsa65.generate()
        val signature = MlDsa65.sign(keys.privateKey, "asl xabar".toByteArray())

        assertFalse(
            "o'zgartirilgan xabar qabul qilindi",
            MlDsa65.verify(keys.publicKey, signature, "asl xabar!".toByteArray()),
        )
    }

    @Test
    fun `foreign key is rejected`() {
        val ours = MlDsa65.generate()
        val theirs = MlDsa65.generate()
        val message = "hodisa".toByteArray()
        val signature = MlDsa65.sign(ours.privateKey, message)

        assertFalse(
            "begona kalit bilan tekshirish o'tdi",
            MlDsa65.verify(theirs.publicKey, signature, message),
        )
    }

    @Test
    fun `malformed input does not crash`() {
        // Buzuq kalit yoki imzo tushsa ilova YIQILMASLIGI kerak —
        // tarmoqdan istalgan axlat kelishi mumkin.
        assertFalse(MlDsa65.verify(ByteArray(10), ByteArray(10), "x".toByteArray()))
        assertFalse(MlDsa65.verify(ByteArray(1952), ByteArray(3309), "x".toByteArray()))
    }

    @Test
    fun `private key is not exposed in toString`() {
        val keys = MlDsa65.generate()
        assertTrue(keys.toString().contains("<secrets hidden>"))
        assertFalse(keys.toString().contains(keys.privateKey.toHex().take(16)))
    }
}
