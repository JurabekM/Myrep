package uz.distribos.crypto

import co.nstant.`in`.cbor.CborDecoder
import co.nstant.`in`.cbor.model.ByteString
import co.nstant.`in`.cbor.model.Map as CborMap
import co.nstant.`in`.cbor.model.Number as CborNumber
import co.nstant.`in`.cbor.model.UnicodeString
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Base64

/**
 * BOOT-1 moslik testi.
 *
 * Bu yiqilsa — telefon desktopga ULANA OLMAYDI. Ulash oqimi butun
 * mahsulotning kirish nuqtasi, shuning uchun bu kritik.
 */
class Boot1KatTest {

    private val boot1: JSONObject by lazy {
        val stream = requireNotNull(
            javaClass.classLoader?.getResourceAsStream("des1_kat.json")
        ) { "des1_kat.json topilmadi" }
        JSONObject(stream.bufferedReader().use { it.readText() }).getJSONObject("boot1")
    }

    private fun decode(value: String): ByteArray = Base64.getDecoder().decode(value)

    private fun JSONArray.objects(): List<JSONObject> =
        (0 until length()).map { getJSONObject(it) }

    @Test
    fun `key derivation matches python`() {
        for (case in boot1.getJSONArray("keys").objects()) {
            val keys = Boot1Codec.deriveKeys(decode(case.getString("invitation_secret")))
            assertArrayEquals("request_key", decode(case.getString("request_key")), keys.requestKey)
            assertArrayEquals("request_iv", decode(case.getString("request_iv")), keys.requestIv)
            assertArrayEquals(
                "response_key", decode(case.getString("response_key")), keys.responseKey
            )
            assertArrayEquals("response_iv", decode(case.getString("response_iv")), keys.responseIv)
        }
    }

    @Test
    fun `join proof matches python`() {
        for (case in boot1.getJSONArray("proof").objects()) {
            val keys = Boot1Codec.deriveKeys(decode(case.getString("invitation_secret")))
            val proof = Boot1Codec.joinProof(
                keys, decode(case.getString("device_id")),
                decode(case.getString("sign_public_key")),
            )
            assertArrayEquals("isbot farq qildi", decode(case.getString("proof")), proof)
        }
    }

    @Test
    fun `python join request opens in kotlin`() {
        val case = boot1.getJSONArray("envelopes").objects().first { it.getString("name") == "join-request" }
        val keys = Boot1Codec.deriveKeys(decode(case.getString("invitation_secret")))
        val wire = decode(case.getString("wire"))

        assertArrayEquals(
            decode(case.getString("invitation_id")), Boot1Codec.peekInvitationId(wire)
        )
        assertEquals(Boot1Kind.JOIN_REQUEST, Boot1Codec.peekKind(wire))

        val payload = Boot1Codec.open(wire, keys, Boot1Kind.JOIN_REQUEST).asCborMap()
        assertArrayEquals(
            "device_id farq qildi",
            decode(case.getString("expect_device_id")), payload.bytes("device_id"),
        )
        assertEquals(case.getString("expect_platform"), payload.text("platform"))

        // Isbot ham to'g'ri bo'lishi kerak.
        assertTrue(
            "join isboti tasdiqlanmadi",
            Boot1Codec.verifyJoinProof(
                keys, payload.bytes("device_id"),
                payload.bytes("sign_public_key"), payload.bytes("proof"),
            ),
        )
    }

    @Test
    fun `python join response opens in kotlin`() {
        val case = boot1.getJSONArray("envelopes").objects().first { it.getString("name") == "join-response" }
        val keys = Boot1Codec.deriveKeys(decode(case.getString("invitation_secret")))

        val payload = Boot1Codec.open(
            decode(case.getString("wire")), keys, Boot1Kind.JOIN_RESPONSE
        ).asCborMap()

        assertEquals(case.getInt("expect_epoch").toLong(), payload.number("epoch"))
        assertEquals(case.getString("expect_role"), payload.text("role"))
        assertArrayEquals(
            "epoch root secret farq qildi",
            decode(case.getString("expect_epoch_root_secret")),
            payload.bytes("epoch_root_secret"),
        )
    }

    @Test
    fun `kotlin envelope round trips`() {
        val secret = ByteArray(32) { (it + 7).toByte() }
        val keys = Boot1Codec.deriveKeys(secret)
        val invitationId = ByteArray(8) { it.toByte() }
        val plaintext = "salom".toByteArray()

        val wire = Boot1Codec.seal(plaintext, Boot1Kind.JOIN_REQUEST, invitationId, keys)
        assertArrayEquals(plaintext, Boot1Codec.open(wire, keys, Boot1Kind.JOIN_REQUEST))
    }

    @Test
    fun `request cannot be replayed as response`() {
        // Yo'nalishli kalitlar: ushlab olingan so'rovni javob sifatida
        // ochib bo'lmaydi (AETHER-Q N3).
        val keys = Boot1Codec.deriveKeys(ByteArray(32) { it.toByte() })
        val wire = Boot1Codec.seal(
            "x".toByteArray(), Boot1Kind.JOIN_REQUEST, ByteArray(8), keys
        )
        try {
            Boot1Codec.open(wire, keys, Boot1Kind.JOIN_RESPONSE)
            throw AssertionError("so'rov javob sifatida ochildi")
        } catch (_: Boot1Exception) {
            // kutilgan
        }
    }

    @Test
    fun `wrong secret is rejected`() {
        val real = Boot1Codec.deriveKeys(ByteArray(32) { it.toByte() })
        val guessed = Boot1Codec.deriveKeys(ByteArray(32) { (it + 1).toByte() })
        val wire = Boot1Codec.seal("x".toByteArray(), Boot1Kind.JOIN_REQUEST, ByteArray(8), real)

        try {
            Boot1Codec.open(wire, guessed, Boot1Kind.JOIN_REQUEST)
            throw AssertionError("noto'g'ri sir bilan ochildi")
        } catch (_: Boot1Exception) {
            // kutilgan
        }
    }

    @Test
    fun `proof is bound to device identity`() {
        val keys = Boot1Codec.deriveKeys(ByteArray(32) { it.toByte() })
        val proof = Boot1Codec.joinProof(keys, ByteArray(16) { 1 }, ByteArray(1952))

        assertFalse(
            "boshqa qurilma isbotni ishlatdi",
            Boot1Codec.verifyJoinProof(keys, ByteArray(16) { 2 }, ByteArray(1952), proof),
        )
    }

    @Test
    fun `truncated envelope is rejected`() {
        val keys = Boot1Codec.deriveKeys(ByteArray(32))
        try {
            Boot1Codec.open(ByteArray(Boot1.MIN_ENVELOPE_SIZE - 1), keys)
            throw AssertionError("qisqa envelope qabul qilindi")
        } catch (_: Boot1Exception) {
            // kutilgan
        }
    }

    @Test
    fun `keys do not leak in toString`() {
        val keys = Boot1Codec.deriveKeys(ByteArray(32) { it.toByte() })
        assertTrue(keys.toString().contains("<secrets hidden>"))
        assertFalse(keys.toString().contains(keys.requestKey.toHex()))
    }

    // --- CBOR yordamchilari ------------------------------------------------

    private fun ByteArray.asCborMap(): CborMap =
        CborDecoder.decode(this).first() as CborMap

    private fun CborMap.bytes(key: String): ByteArray =
        (get(UnicodeString(key)) as ByteString).bytes

    private fun CborMap.text(key: String): String =
        (get(UnicodeString(key)) as UnicodeString).string

    private fun CborMap.number(key: String): Long =
        (get(UnicodeString(key)) as CborNumber).value.toLong()
}
