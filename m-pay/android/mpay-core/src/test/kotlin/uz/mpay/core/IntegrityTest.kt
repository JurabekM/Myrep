package uz.mpay.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

/** P2.6: `requestHash` Rust `mpay_integrity::request_hash` bilan bir xil (umumiy vektor). */
class IntegrityTest {
    @Test
    fun requestHashVector() {
        val sid = ByteArray(16) { 0x11 }
        assertEquals("ibPmhjjxqmxmm7yGEh3rp1XGVsQiEPYcFNkCMz56DDw", Integrity.requestHash(Integrity.PURPOSE_PROVISION, sid))
        assertNotEquals(
            Integrity.requestHash(Integrity.PURPOSE_PROVISION, sid),
            Integrity.requestHash(Integrity.PURPOSE_PROVISION, ByteArray(16) { 0x12 }),
        )
    }
}
