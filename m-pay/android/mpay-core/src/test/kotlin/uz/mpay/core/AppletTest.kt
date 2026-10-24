package uz.mpay.core

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Kotlin HCE applet ↔ Kotlin terminal yadrosi (loopback) va ARQC qayta hisoblash. */
class AppletTest {
    private class Gate(var ok: Boolean = false) : CdcvmGate {
        override fun isVerified() = ok
        override fun consume() { ok = false }
    }

    private val luk = ByteArray(16) { 7 }

    private fun profile() = CardProfile(
        "tok_00000000000000000000000000000001", "9900770000001230", "2912", 0,
        mutableListOf(CardLuk(3, luk, Long.MAX_VALUE, 2)), 0,
    )

    @Test
    fun tapProducesVerifiableArqc() {
        val p = profile()
        val gate = Gate()
        val applet = CardApplet({ p }, gate)
        val tap = TerminalKernel.tap({ applet.process(it) }, 1_250_000, TerminalData.dateBcd(2026, 10, 24))
        assertEquals(1, tap.atc)
        assertEquals("990077******1230", tap.dpanMasked)
        // Emitent tomonidagi qayta hisoblash (LUK → SK → CDOL → ARQC).
        val icc = tap.icc
        val pdol = java.io.ByteArrayOutputStream().also { o -> Emv.PDOL.forEach { (t, _) -> o.write(Tlv.require(icc, t)) } }.toByteArray()
        val iad = Iad.parse(Tlv.require(icc, Emv.Tag.IAD))
        assertEquals(3L, iad.lukSeq)
        val sk = MpayScheme.sessionKey(luk, 1)
        assertArrayEquals(MpayScheme.arqc(sk, Cdol.data(pdol, Emv.AIP, 1, iad)), Tlv.require(icc, Emv.Tag.ARQC))
        // ARPC tekshiruvi.
        val arc = "00".toByteArray()
        val arpc = MpayScheme.arpc(sk, Tlv.require(icc, Emv.Tag.ARQC), arc)
        assertTrue(applet.verifyIssuerAuth(arpc + arc))
        assertTrue(!applet.verifyIssuerAuth(byteArrayOf(0, 0, 0, 0) + arc))
    }

    @Test
    fun cdcvmLimitsAndStatusWords() {
        val p = profile()
        val gate = Gate()
        val applet = CardApplet({ p }, gate)
        val date = TerminalData.dateBcd(2026, 10, 24)
        try {
            TerminalKernel.tap({ applet.process(it) }, 200_000_000, date)
            throw AssertionError("6986 kutilgan")
        } catch (e: TerminalException) {
            assertTrue(e.seePhone)
        }
        gate.ok = true
        TerminalKernel.tap({ applet.process(it) }, 200_000_000, date)
        assertTrue("CDCVM bir martalik", !gate.ok)
        // LUK 2 marta ishlatildi (1 tasi oldingi 6986 da sarflanmagan): ikkinchi kichik tap ham o'tadi, uchinchisi — 6985.
        TerminalKernel.tap({ applet.process(it) }, 100, date)
        try {
            TerminalKernel.tap({ applet.process(it) }, 100, date)
            throw AssertionError("6985 kutilgan")
        } catch (e: TerminalException) {
            assertEquals(CardApplet.SW_CONDITIONS, e.sw)
        }
        // Holat so'zlari.
        assertArrayEquals(CardApplet.sw(CardApplet.SW_WRONG_LENGTH), applet.process(byteArrayOf(0)))
        assertArrayEquals(CardApplet.sw(CardApplet.SW_CLA_NOT_SUPPORTED), applet.process(byteArrayOf(0x90.toByte(), 0xB2.toByte(), 0, 0, 0)))
        val noProfile = CardApplet({ null }, gate)
        assertArrayEquals(CardApplet.sw(CardApplet.SW_FILE_NOT_FOUND), noProfile.process(byteArrayOf(0, 0xA4.toByte(), 4, 0, 6) + Emv.AID + byteArrayOf(0)))
    }
}
