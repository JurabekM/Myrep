package uz.distribos.crypto

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Base64

/**
 * Kotlin implementatsiyasi Python bilan BAYTMA-BAYT mos ekanini qulflaydi.
 *
 * Vektorlar `tools/gen_des1_kat.py` tomonidan generatsiya qilinadi va
 * ikkala tomon SHU faylni o'qiydi — nusxa emas, bitta manba.
 *
 * Bu test yiqilsa: Kotlin va Python turli baytlar ishlab chiqarmoqda,
 * ya'ni telefon desktop yuborgan xabarni ocholmaydi. Bu «keyinroq
 * tuzatamiz» toifasidagi xato emas.
 */
class Des1KatTest {

    private val vectors: JSONObject by lazy {
        val stream = requireNotNull(
            javaClass.classLoader?.getResourceAsStream("des1_kat.json")
        ) { "des1_kat.json topilmadi — `python tools/gen_des1_kat.py` ni ishga tushiring" }
        JSONObject(stream.bufferedReader().use { it.readText() })
    }

    private fun decode(value: String): ByteArray = Base64.getDecoder().decode(value)

    private fun JSONArray.objects(): List<JSONObject> =
        (0 until length()).map { getJSONObject(it) }

    // --- primitivlar ------------------------------------------------------

    @Test
    fun `sha3-256 matches python`() {
        for (case in vectors.getJSONObject("kdf").getJSONArray("sha3").objects()) {
            val input = decode(case.getString("input"))
            assertArrayEquals(
                "SHA3-256 farq qildi: ${case.getString("name")}",
                decode(case.getString("sha3_256")),
                Kdf.sha3_256(input),
            )
        }
    }

    @Test
    fun `hkdf-sha3 matches python`() {
        for (case in vectors.getJSONObject("kdf").getJSONArray("hkdf").objects()) {
            val prk = Kdf.hkdfExtract(
                decode(case.getString("salt")), decode(case.getString("ikm"))
            )
            assertArrayEquals("PRK farq qildi", decode(case.getString("prk")), prk)

            val okm = Kdf.hkdfExpand(
                prk, decode(case.getString("info")), case.getInt("length")
            )
            assertArrayEquals("OKM farq qildi", decode(case.getString("okm")), okm)
        }
    }

    @Test
    fun `kmac256 matches python`() {
        for (case in vectors.getJSONObject("kdf").getJSONArray("kmac256").objects()) {
            val actual = Kdf.kmac256(
                decode(case.getString("key")),
                decode(case.getString("data")),
                case.getInt("length"),
                decode(case.getString("custom")),
            )
            assertArrayEquals("KMAC256 farq qildi", decode(case.getString("out")), actual)
        }
    }

    @Test
    fun `cshake256 matches python`() {
        for (case in vectors.getJSONObject("kdf").getJSONArray("cshake256").objects()) {
            val actual = Kdf.cshake256(
                decode(case.getString("data")),
                case.getInt("length"),
                decode(case.getString("name")),
                decode(case.getString("custom")),
            )
            assertArrayEquals("cSHAKE256 farq qildi", decode(case.getString("out")), actual)
        }
    }

    // --- DES-1 ------------------------------------------------------------

    @Test
    fun `epoch key derivation matches python`() {
        for (case in vectors.getJSONArray("epoch_keys").objects()) {
            val keys = Des1Codec.deriveEpochKeys(
                decode(case.getString("epoch_root_secret")),
                decode(case.getString("tenant_id")),
                case.getInt("epoch"),
                case.getLong("key_id"),
                case.getInt("profile_id"),
            )
            val label = "epoch=${case.getInt("epoch")} profil=${case.getInt("profile_id")}"
            assertArrayEquals("$label: aead_key", decode(case.getString("aead_key")), keys.aeadKey)
            assertArrayEquals("$label: aead_iv", decode(case.getString("aead_iv")), keys.aeadIv)
            assertArrayEquals(
                "$label: tenant_tag", decode(case.getString("tenant_tag")), keys.tenantTag
            )
        }
    }

    @Test
    fun `nonce derivation matches python`() {
        for (case in vectors.getJSONArray("nonce").objects()) {
            val actual = Des1Codec.nonce(
                case.getLong("sequence"), decode(case.getString("iv"))
            )
            assertArrayEquals(
                "nonce farq qildi: seq=${case.getLong("sequence")}",
                decode(case.getString("nonce")), actual,
            )
        }
    }

    @Test
    fun `header packing matches python`() {
        for (case in vectors.getJSONArray("header").objects()) {
            val header = Des1Header(
                version = case.getInt("version"),
                profileId = case.getInt("profile_id"),
                contentType = case.getInt("content_type"),
                epoch = case.getInt("epoch"),
                keyId = case.getLong("key_id"),
                tenantTag = decode(case.getString("tenant_tag")),
                senderDeviceId = decode(case.getString("sender_device_id")),
                sequence = case.getLong("sequence"),
                rand = decode(case.getString("rand")),
            )
            assertArrayEquals(
                "header baytlari farq qildi", decode(case.getString("packed")), header.pack()
            )
            assertEquals("header qayta o'qilmadi", header, Des1Header.unpack(header.pack()))
        }
    }

    @Test
    fun `python ciphertext opens in kotlin`() {
        for (case in vectors.getJSONArray("aead").objects()) {
            val keys = Des1Codec.deriveEpochKeys(
                decode(case.getString("epoch_root_secret")),
                decode(case.getString("tenant_id")),
                case.getInt("epoch"),
                case.getLong("key_id"),
                case.getInt("profile_id"),
            )
            val header = Des1Header.unpack(decode(case.getString("packed_header")))
            val plaintext = Des1Codec.openAead(
                header, decode(case.getString("ciphertext")), keys
            )
            assertArrayEquals(
                "Python shifrlagan matn Kotlin'da ochilmadi",
                decode(case.getString("plaintext")), plaintext,
            )
        }
    }

    @Test
    fun `kotlin ciphertext matches python byte for byte`() {
        for (case in vectors.getJSONArray("aead").objects()) {
            val keys = Des1Codec.deriveEpochKeys(
                decode(case.getString("epoch_root_secret")),
                decode(case.getString("tenant_id")),
                case.getInt("epoch"),
                case.getLong("key_id"),
                case.getInt("profile_id"),
            )
            val header = Des1Header.unpack(decode(case.getString("packed_header")))
            // ChaCha20-Poly1305 deterministik: bir xil kalit+nonce+AAD ->
            // bir xil ciphertext. Shuning uchun baytma-bayt solishtiramiz.
            val sealed = Des1Codec.seal(
                decode(case.getString("plaintext")), header, keys,
            ) { ByteArray(Des1.SIGNATURE_SIZE) }
            val parts = Des1Codec.split(sealed)
            assertArrayEquals(
                "Kotlin ciphertext Python'nikidan farq qildi",
                decode(case.getString("ciphertext")), parts.ciphertext,
            )
        }
    }

    @Test
    fun `signed bytes match python`() {
        for (case in vectors.getJSONArray("aead").objects()) {
            val actual = Des1Codec.signedBytes(
                decode(case.getString("packed_header")),
                decode(case.getString("ciphertext")),
            )
            assertArrayEquals(
                "imzo ostidagi baytlar farq qildi",
                decode(case.getString("signed_bytes")), actual,
            )
        }
    }

    // --- salbiy holatlar --------------------------------------------------

    @Test
    fun `tampered ciphertext is rejected`() {
        val case = vectors.getJSONArray("aead").getJSONObject(1)
        val keys = Des1Codec.deriveEpochKeys(
            decode(case.getString("epoch_root_secret")),
            decode(case.getString("tenant_id")),
            case.getInt("epoch"), case.getLong("key_id"), case.getInt("profile_id"),
        )
        val header = Des1Header.unpack(decode(case.getString("packed_header")))
        val ciphertext = decode(case.getString("ciphertext"))
        ciphertext[0] = (ciphertext[0].toInt() xor 0x01).toByte()

        try {
            Des1Codec.openAead(header, ciphertext, keys)
            throw AssertionError("buzilgan ciphertext ochildi")
        } catch (_: Des1FormatException) {
            // kutilgan
        }
    }

    @Test
    fun `profile downgrade changes keys`() {
        val root = ByteArray(32) { it.toByte() }
        val tenant = "tenant-demo-0001".toByteArray()
        val hybrid = Des1Codec.deriveEpochKeys(root, tenant, 7, 3, Des1.PROFILE_HYBRID)
        val minimal = Des1Codec.deriveEpochKeys(root, tenant, 7, 3, Des1.PROFILE_MINIMAL)

        assertFalse("0x01 va 0x03 bir xil kalit berdi", hybrid.aeadKey.contentEquals(minimal.aeadKey))
        assertFalse(hybrid.tenantTag.contentEquals(minimal.tenantTag))
    }

    @Test
    fun `foreign tenant tag does not match`() {
        val root = ByteArray(32) { it.toByte() }
        val ours = Des1Codec.deriveEpochKeys(root, "tenant-demo-0001".toByteArray(), 7, 3, 1)
        val theirs = Des1Codec.deriveEpochKeys(root, "tenant-other-002".toByteArray(), 7, 3, 1)

        val header = Des1Header(
            Des1.VERSION, 1, 1, 7, 3, ours.tenantTag,
            ByteArray(16), 1L, ByteArray(6),
        )
        assertTrue(Des1Codec.tenantTagMatches(header, ours))
        assertFalse("begona tenant qabul qilindi", Des1Codec.tenantTagMatches(header, theirs))
    }

    @Test
    fun `truncated envelope is rejected`() {
        try {
            Des1Codec.split(ByteArray(Des1.MIN_ENVELOPE_SIZE - 1))
            throw AssertionError("qisqa envelope qabul qilindi")
        } catch (_: Des1FormatException) {
            // kutilgan
        }
    }

    @Test
    fun `epoch keys do not leak secrets in toString`() {
        val keys = Des1Codec.deriveEpochKeys(
            ByteArray(32) { it.toByte() }, "tenant-demo-0001".toByteArray(), 7, 3, 1
        )
        val text = keys.toString()
        assertTrue(text.contains("<secrets hidden>"))
        assertFalse(text.contains(keys.aeadKey.toHex()))
    }
}
