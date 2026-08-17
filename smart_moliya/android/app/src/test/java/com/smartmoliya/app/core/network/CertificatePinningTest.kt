package com.smartmoliya.app.core.network

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class CertificatePinningTest {

    private val validPin = "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="

    @Test
    fun `blank host disables pinning`() {
        assertNull(buildCertificatePinner("", validPin))
    }

    @Test
    fun `blank pin disables pinning`() {
        assertNull(buildCertificatePinner("api.smartmoliya.uz", ""))
    }

    @Test
    fun `configured host and pin produce a pinner with one entry`() {
        val pinner = buildCertificatePinner("api.smartmoliya.uz", validPin)
        assertNotNull(pinner)
        assertEquals(1, pinner!!.pins.size)
    }

    @Test
    fun `pin without sha256 prefix is normalized`() {
        val pinner = buildCertificatePinner("api.smartmoliya.uz", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
        assertNotNull(pinner)
        val pin = pinner!!.pins.first()
        assertEquals("sha256", pin.hashAlgorithm.removeSuffix("/"))
    }

    @Test
    fun `pins only apply to the configured host`() {
        val pinner = buildCertificatePinner("api.smartmoliya.uz", validPin)!!
        // Boshqa hostga (masalan dev'dagi 10.0.2.2) hech qanday pin qo'llanmaydi
        assertEquals(0, pinner.findMatchingPins("10.0.2.2").size)
        assertEquals(1, pinner.findMatchingPins("api.smartmoliya.uz").size)
    }
}
