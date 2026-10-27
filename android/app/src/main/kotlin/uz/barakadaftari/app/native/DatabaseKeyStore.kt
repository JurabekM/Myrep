package uz.barakadaftari.app.native

import java.security.SecureRandom

/** SQLCipher uchun 256-bit DB kaliti (SPEC 4.5). */
class DatabaseKeyStore(
    private val blobs: SecureBlobStore,
    private val random: SecureRandom = SecureRandom(),
) {
    @Synchronized
    fun getOrCreate(): ByteArray {
        blobs.read(BLOB_NAME)?.let { existing ->
            check(existing.size == KEY_LENGTH) { "DB kaliti uzunligi noto'g'ri" }
            return existing
        }
        val key = ByteArray(KEY_LENGTH).also(random::nextBytes)
        blobs.write(BLOB_NAME, key)
        return key
    }

    companion object {
        const val BLOB_NAME = "db_key"
        const val KEY_LENGTH = 32
    }
}
