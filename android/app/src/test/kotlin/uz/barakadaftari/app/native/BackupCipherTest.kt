package uz.barakadaftari.app.native

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class BackupCipherTest {
    private val plain = "Baraka Dastur — zaxira nusxa".toByteArray()

    @Test
    fun roundTripWithRightPassword() {
        val data = BackupCipher.encrypt("toʻgʻri-parol".toCharArray(), plain)
        assertArrayEquals(plain, BackupCipher.decrypt("toʻgʻri-parol".toCharArray(), data))
        // Sarlavha: BRKD + versiya 1 + iteratsiya 310 000.
        assertEquals("BRKD", String(data.copyOfRange(0, 4)))
        assertEquals(1, data[4].toInt())
        assertFalse("ochiq matn ko'rinmasin", String(data).contains("zaxira"))
    }

    @Test
    fun sameInputGivesDifferentCiphertext() {
        val a = BackupCipher.encrypt("parol-1234".toCharArray(), plain)
        val b = BackupCipher.encrypt("parol-1234".toCharArray(), plain)
        assertFalse(a.contentEquals(b))
    }

    @Test(expected = BackupCipher.BadPasswordException::class)
    fun wrongPasswordRejected() {
        val data = BackupCipher.encrypt("parol-1234".toCharArray(), plain)
        BackupCipher.decrypt("parol-4321".toCharArray(), data)
    }

    @Test(expected = BackupCipher.BadPasswordException::class)
    fun tamperedCiphertextRejected() {
        val data = BackupCipher.encrypt("parol-1234".toCharArray(), plain)
        data[data.size - 1] = (data[data.size - 1].toInt() xor 1).toByte()
        BackupCipher.decrypt("parol-1234".toCharArray(), data)
    }

    @Test(expected = BackupCipher.BadPasswordException::class)
    fun tamperedHeaderRejected() {
        val data = BackupCipher.encrypt("parol-1234".toCharArray(), plain)
        data[20] = (data[20].toInt() xor 1).toByte() // tuz
        BackupCipher.decrypt("parol-1234".toCharArray(), data)
    }

    @Test(expected = BackupCipher.FormatException::class)
    fun notABackupRejected() {
        BackupCipher.decrypt("parol-1234".toCharArray(), ByteArray(64) { 7 })
    }
}
