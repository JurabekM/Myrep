package uz.barakadaftari.app.native

import java.io.File
import java.io.FileOutputStream

/**
 * Wrap qilingan kichik blob'lar ombori. Fayllar ilovaning private
 * `noBackupFilesDir` papkasida yotadi (backup'ga ham tushmaydi).
 */
class SecureBlobStore(
    private val dir: File,
    private val wrapper: KeyWrapper,
) {
    @Synchronized
    fun read(name: String): ByteArray? {
        val file = fileFor(name)
        if (!file.exists()) return null
        return wrapper.unwrap(file.readBytes(), aad(name))
    }

    /** Atomik yozuv: avval vaqtinchalik fayl, keyin rename. */
    @Synchronized
    fun write(name: String, data: ByteArray) {
        val target = fileFor(name)
        dir.mkdirs()
        val tmp = File(dir, "$name$TMP_SUFFIX")
        FileOutputStream(tmp).use { out ->
            out.write(wrapper.wrap(data, aad(name)))
            out.fd.sync()
        }
        if (!tmp.renameTo(target)) {
            target.delete()
            check(tmp.renameTo(target)) { "Blob yozilmadi" }
        }
    }

    @Synchronized
    fun delete(name: String) {
        fileFor(name).delete()
    }

    private fun fileFor(name: String): File {
        require(NAME.matches(name)) { "Noto'g'ri blob nomi" }
        return File(dir, "$name$SUFFIX")
    }

    private fun aad(name: String) = "baraka:$name".toByteArray(Charsets.UTF_8)

    companion object {
        val NAME = Regex("[a-z0-9_]{1,40}")
        const val SUFFIX = ".blob"
        const val TMP_SUFFIX = ".tmp"
    }
}
