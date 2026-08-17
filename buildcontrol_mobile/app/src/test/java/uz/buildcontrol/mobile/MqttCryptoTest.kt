package uz.buildcontrol.mobile

import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import uz.buildcontrol.mobile.data.sync.Crypto
import uz.buildcontrol.mobile.data.sync.MqttTransport

/** Payload sealing must stay byte-compatible with `app/sync/crypto.py`. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], manifest = Config.NONE)
class MqttCryptoTest {

    private val body = buildJsonObject {
        put("entity", JsonPrimitive("Project"))
        put("uid", JsonPrimitive("u1"))
        put("name", JsonPrimitive("Uy ta'miri"))
    }

    @Test
    fun `sealed payload round-trips`() {
        val key = Crypto.deriveKey("maxfiy-parol", "firma-kaliti")
        val sealed = Crypto.encrypt(body, key)
        assertFalse("content must not be readable", sealed.decodeToString().contains("Uy ta'miri"))
        assertTrue(sealed.decodeToString().contains(Crypto.MARKER))
        assertEquals(body, Crypto.decrypt(sealed, key))
    }

    @Test(expected = Crypto.DecryptionException::class)
    fun `wrong passphrase is rejected`() {
        val sealed = Crypto.encrypt(body, Crypto.deriveKey("to'g'ri", "firma"))
        Crypto.decrypt(sealed, Crypto.deriveKey("noto'g'ri", "firma"))
    }

    @Test(expected = Crypto.DecryptionException::class)
    fun `sealed payload without a passphrase is reported`() {
        Crypto.decrypt(Crypto.encrypt(body, Crypto.deriveKey("p", "firma")), null)
    }

    @Test
    fun `plain payload passes through`() {
        val raw = """{"entity":"Project"}""".toByteArray()
        assertEquals("Project", Crypto.decrypt(raw, null)["entity"]!!.jsonPrimitive.content)
    }

    @Test
    fun `key derivation is deterministic and workspace scoped`() {
        assertArrayEquals(Crypto.deriveKey("p", "firma"), Crypto.deriveKey("p", "firma"))
        assertFalse(Crypto.deriveKey("p", "firma").contentEquals(Crypto.deriveKey("p", "boshqa")))
    }

    @Test
    fun `public brokers default to tls ports`() {
        assertTrue(MqttTransport.PUBLIC_BROKERS.isNotEmpty())
        MqttTransport.PUBLIC_BROKERS.forEach { (host, port, label) ->
            assertTrue(host.isNotBlank() && label.isNotBlank())
            assertTrue("$host uses $port", port == 8883 || port == 8886)
        }
    }

    @Test
    fun `describe reveals whether payloads are sealed`() {
        val plain = MqttTransport(tenant = "firma")
        val sealed = MqttTransport(tenant = "firma", passphrase = "parol")
        assertFalse(plain.describe().contains("shifrlangan"))
        assertTrue(sealed.describe().contains("shifrlangan"))
    }
}
