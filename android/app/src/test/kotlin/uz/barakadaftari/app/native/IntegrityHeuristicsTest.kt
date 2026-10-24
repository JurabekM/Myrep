package uz.barakadaftari.app.native

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class IntegrityHeuristicsTest {
    private val pixel = DeviceFingerprint(
        fingerprint = "google/husky/husky:15/AP4A.250105.002/12701944:user/release-keys",
        model = "Pixel 8 Pro",
        manufacturer = "Google",
        brand = "google",
        device = "husky",
        product = "husky",
        hardware = "husky",
        tags = "release-keys",
    )
    private val avd = DeviceFingerprint(
        fingerprint = "google/sdk_gphone64_x86_64/emu64xa:16/BP22.250325.006/13344233:user/release-keys",
        model = "sdk_gphone64_x86_64",
        manufacturer = "Google",
        brand = "google",
        device = "emu64xa",
        product = "sdk_gphone64_x86_64",
        hardware = "ranchu",
        tags = "release-keys",
    )

    @Test
    fun emulatorDetection() {
        assertTrue(IntegrityHeuristics.isEmulator(avd))
        assertFalse(IntegrityHeuristics.isEmulator(pixel))
    }

    @Test
    fun rootDetection() {
        assertFalse(IntegrityHeuristics.isRooted(pixel) { false })
        assertTrue(IntegrityHeuristics.isRooted(pixel) { it == "/system/xbin/su" })
        assertTrue(IntegrityHeuristics.isRooted(pixel.copy(tags = "test-keys")) { false })
    }

    @Test
    fun signatureComparison() {
        val actual = IntegrityHeuristics.sha256Hex("cert".toByteArray())
        assertEquals(64, actual.length)
        assertNull(IntegrityHeuristics.signatureMatches(actual, ""))
        assertEquals(true, IntegrityHeuristics.signatureMatches(actual, actual.lowercase().chunked(2).joinToString(":")))
        assertEquals(false, IntegrityHeuristics.signatureMatches(actual, "00".repeat(32)))
        assertEquals(false, IntegrityHeuristics.signatureMatches("", "AB"))
    }
}
