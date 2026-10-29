package uz.mpay.wallet.sdk

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import uz.mpay.core.CardBook
import java.io.File
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Hamyon kartalari ([CardBook]: token profillari, LUK'lar, serverdagi holat, asosiy karta) — AES-256-GCM
 * bilan shifrlangan fayl (`noBackupFilesDir`); kalit Android Keystore'da (chiqarib bo'lmaydi). LUK'lar
 * faqat shu faylda va xotirada; hech qachon logga yozilmaydi. Eski bitta kartali fayl o'qilganda
 * avtomatik ko'chadi ([CardBook.fromJson]).
 */
class WalletStore(context: Context) {
    private val file = File(context.noBackupFilesDir, "mpay-wallet.bin")
    private val alias = "mpay-wallet-store"
    private var cache: CardBook? = null

    private fun key(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (ks.getKey(alias, null) as? SecretKey)?.let { return it }
        val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .build()
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply { init(spec) }.generateKey()
    }

    private fun book(): CardBook {
        cache?.let { return it }
        val b = if (file.exists()) {
            val raw = file.readBytes()
            val ivLen = raw[0].toInt()
            val c = Cipher.getInstance("AES/GCM/NoPadding").apply {
                init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, raw.copyOfRange(1, 1 + ivLen)))
            }
            CardBook.fromJson(String(c.doFinal(raw.copyOfRange(1 + ivLen, raw.size)), Charsets.UTF_8))
        } else {
            CardBook()
        }
        cache = b
        return b
    }

    private fun persist(b: CardBook) {
        val c = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key()) }
        val ct = c.doFinal(b.toJson().toByteArray(Charsets.UTF_8))
        val tmp = File(file.parentFile, file.name + ".tmp")
        tmp.writeBytes(byteArrayOf(c.iv.size.toByte()) + c.iv + ct)
        tmp.renameTo(file)
    }

    /** O'qish (o'zgartirmaydi). */
    @Synchronized
    fun <T> read(f: (CardBook) -> T): T = f(book())

    /** O'zgartirish va darhol shifrlab saqlash (atomar fayl almashtirish). */
    @Synchronized
    fun <T> update(f: (CardBook) -> T): T {
        val b = book()
        val r = f(b)
        persist(b)
        return r
    }

    @Synchronized
    fun clear() {
        file.delete()
        cache = null
    }
}
