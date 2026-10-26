package uz.mpay.wallet.sdk

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import org.json.JSONArray
import org.json.JSONObject
import uz.mpay.core.CardLuk
import uz.mpay.core.CardProfile
import uz.mpay.core.DEFAULT_CVM_LIMIT_MINOR
import uz.mpay.core.Hex
import java.io.File
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Token profili va LUK'lar — AES-256-GCM bilan shifrlangan fayl (`noBackupFilesDir`); kalit Android
 * Keystore'da (chiqarib bo'lmaydi). LUK'lar faqat shu faylda va xotirada; hech qachon logga yozilmaydi.
 */
class WalletStore(context: Context) {
    private val file = File(context.noBackupFilesDir, "mpay-wallet.bin")
    private val alias = "mpay-wallet-store"
    @Volatile private var cache: CardProfile? = null

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

    @Synchronized
    fun save(p: CardProfile) {
        val j = JSONObject()
            .put("token_id", p.tokenId).put("dpan", p.dpan).put("expiry", p.expiryYymm).put("psn", p.psn).put("atc", p.atc)
            .put("cvm", p.cvmLimitMinor)
            .put("renew_after", p.renewAfter ?: JSONObject.NULL)
            .put("luks", JSONArray().apply {
                p.luks.forEach { put(JSONObject().put("seq", it.seq).put("key", Hex.encode(it.key)).put("exp", it.expiresAt).put("uses", it.usesLeft)) }
            })
        val c = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key()) }
        val ct = c.doFinal(j.toString().toByteArray(Charsets.UTF_8))
        val tmp = File(file.parentFile, file.name + ".tmp")
        tmp.writeBytes(byteArrayOf(c.iv.size.toByte()) + c.iv + ct)
        tmp.renameTo(file)
        cache = p
    }

    @Synchronized
    fun load(): CardProfile? {
        cache?.let { return it }
        if (!file.exists()) return null
        val b = file.readBytes()
        val ivLen = b[0].toInt()
        val c = Cipher.getInstance("AES/GCM/NoPadding").apply {
            init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, b.copyOfRange(1, 1 + ivLen)))
        }
        val j = JSONObject(String(c.doFinal(b.copyOfRange(1 + ivLen, b.size)), Charsets.UTF_8))
        val a = j.getJSONArray("luks")
        val p = CardProfile(
            j.getString("token_id"), j.getString("dpan"), j.getString("expiry"), j.getInt("psn"),
            MutableList(a.length()) { i ->
                val l = a.getJSONObject(i)
                CardLuk(l.getLong("seq"), Hex.decode(l.getString("key")), l.getLong("exp"), l.getInt("uses"))
            },
            j.getInt("atc"),
            j.optLong("cvm", DEFAULT_CVM_LIMIT_MINOR),
            if (j.isNull("renew_after")) null else j.getLong("renew_after"),
        )
        cache = p
        return p
    }

    @Synchronized
    fun clear() {
        file.delete()
        cache = null
    }
}
