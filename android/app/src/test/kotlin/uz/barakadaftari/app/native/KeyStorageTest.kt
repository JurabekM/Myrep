package uz.barakadaftari.app.native

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.security.GeneralSecurityException

class KeyStorageTest {
    @get:Rule
    val tmp = TemporaryFolder()

    private val wrappingKey = softwareAesKey()
    private fun wrapper(key: javax.crypto.SecretKey = wrappingKey) = AesGcmKeyWrapper { key }
    private fun store(dir: File, key: javax.crypto.SecretKey = wrappingKey) = SecureBlobStore(dir, wrapper(key))

    @Test
    fun wrapUnwrapRoundTrip() {
        val plain = "maxfiy".toByteArray()
        val blob = wrapper().wrap(plain, "a".toByteArray())
        assertEquals(1 + 12 + plain.size + 16, blob.size)
        assertEquals(AesGcmKeyWrapper.FORMAT_VERSION, blob[0])
        assertArrayEquals(plain, wrapper().unwrap(blob, "a".toByteArray()))
    }

    @Test
    fun eachWrapUsesFreshIv() {
        val a = wrapper().wrap(ByteArray(32), byteArrayOf())
        val b = wrapper().wrap(ByteArray(32), byteArrayOf())
        assertFalse(a.copyOfRange(1, 13).contentEquals(b.copyOfRange(1, 13)))
    }

    @Test
    fun tamperedBlobIsRejected() {
        val blob = wrapper().wrap(ByteArray(32) { 7 }, byteArrayOf())
        blob[blob.size - 1] = (blob[blob.size - 1].toInt() xor 1).toByte()
        assertThrows(GeneralSecurityException::class.java) { wrapper().unwrap(blob, byteArrayOf()) }
    }

    @Test
    fun wrongAadIsRejected() {
        val blob = wrapper().wrap(ByteArray(8), "db_key".toByteArray())
        assertThrows(GeneralSecurityException::class.java) { wrapper().unwrap(blob, "pin".toByteArray()) }
    }

    @Test
    fun truncatedBlobIsRejected() {
        assertThrows(GeneralSecurityException::class.java) { wrapper().unwrap(byteArrayOf(1, 2, 3), byteArrayOf()) }
    }

    @Test
    fun databaseKeyIs256BitAndStableAcrossRestart() {
        val dir = tmp.newFolder("secure")
        val first = DatabaseKeyStore(store(dir)).getOrCreate()
        assertEquals(32, first.size)

        // «Qayta ishga tushirish»: yangi obyektlar, o'sha papka va o'sha Keystore kaliti.
        val second = DatabaseKeyStore(store(dir)).getOrCreate()
        assertArrayEquals(first, second)
    }

    @Test
    fun databaseKeyIsNotStoredInPlaintext() {
        val dir = tmp.newFolder("secure")
        val key = DatabaseKeyStore(store(dir)).getOrCreate()
        val onDisk = File(dir, "db_key.blob").readBytes()
        assertFalse(onDisk.hex().contains(key.hex()))
    }

    @Test
    fun differentInstallsGetDifferentKeys() {
        val a = DatabaseKeyStore(store(tmp.newFolder("a"))).getOrCreate()
        val b = DatabaseKeyStore(store(tmp.newFolder("b"))).getOrCreate()
        assertFalse(a.contentEquals(b))
    }

    @Test
    fun foreignWrappingKeyFailsInsteadOfSilentlyRegenerating() {
        val dir = tmp.newFolder("secure")
        DatabaseKeyStore(store(dir)).getOrCreate()
        val other = DatabaseKeyStore(store(dir, softwareAesKey()))
        // Jimgina yangi kalit yaratilsa, shifrlangan baza abadiy yo'qoladi.
        assertThrows(GeneralSecurityException::class.java) { other.getOrCreate() }
    }

    @Test
    fun blobsCannotBeSwapped() {
        val dir = tmp.newFolder("secure")
        val s = store(dir)
        s.write("pin_record", "A".toByteArray())
        s.write("lockout", "B".toByteArray())
        File(dir, "pin_record.blob").copyTo(File(dir, "lockout.blob"), overwrite = true)
        assertThrows(GeneralSecurityException::class.java) { s.read("lockout") }
    }

    @Test
    fun blobLifecycle() {
        val s = store(tmp.newFolder("secure"))
        assertNull(s.read("security_settings"))
        s.write("security_settings", byteArrayOf(1, 2))
        assertArrayEquals(byteArrayOf(1, 2), s.read("security_settings"))
        s.delete("security_settings")
        assertNull(s.read("security_settings"))
    }

    @Test
    fun invalidBlobNamesAreRejected() {
        val s = store(tmp.newFolder("secure"))
        for (bad in listOf("", "../x", "A", "with space", "a".repeat(41))) {
            assertThrows(IllegalArgumentException::class.java) { s.write(bad, byteArrayOf()) }
        }
        assertTrue(SecureBlobStore.NAME.matches("db_key"))
    }
}
