package uz.barakadaftari.app.native

import org.junit.Assert.assertEquals
import org.junit.Test

/** RFC 7914, 11-bo'lim: PBKDF2-HMAC-SHA256 test vektorlari (KAT). */
class PinKdfTest {
    @Test
    fun rfc7914VectorOneIteration() {
        val dk = PinKdf.derive("passwd".toCharArray(), "salt".toByteArray(), 1, 64)
        assertEquals(
            "55ac046e56e3089fec1691c22544b605f94185216dde0465e68b9d57c20dacbc" +
                "49ca9cccf179b645991664b39d77ef317c71b845b1e30bd509112041d3a19783",
            dk.hex(),
        )
    }

    @Test
    fun rfc7914Vector80000Iterations() {
        val dk = PinKdf.derive("Password".toCharArray(), "NaCl".toByteArray(), 80_000, 64)
        assertEquals(
            "4ddcd8f60b98be21830cee5ef22701f9641a4418d04c0414aeff08876b34ab56" +
                "a1d425a1225833549adb841b51c9b3176a272bdebba1d078478f62b397f33c8d",
            dk.hex(),
        )
    }

    @Test
    fun defaultLengthIs32Bytes() {
        assertEquals(32, PinKdf.derive("123456".toCharArray(), ByteArray(16), 1).size)
    }
}
