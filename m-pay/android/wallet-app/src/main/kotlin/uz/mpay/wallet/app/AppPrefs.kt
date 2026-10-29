package uz.mpay.wallet.app

import android.content.Context
import android.content.res.Configuration
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import java.security.SecureRandom
import javax.crypto.KeyGenerator
import javax.crypto.Mac
import javax.crypto.SecretKey

/**
 * Ilova sozlamalari (sirsiz): til, biometriya, bildirishnomalar, PIN tekshirgichi (Keystore HMAC),
 * tranzaksiya belgilari. Kartalar va LUK'lar — SDK'ning shifrlangan omborida (`WalletStore`).
 */
class AppPrefs(context: Context) {
    private val p = context.applicationContext.getSharedPreferences("mpay_app", Context.MODE_PRIVATE)

    var lang: Lang
        get() = Lang.of(p.getString("lang", null))
        set(v) = p.edit().putString("lang", v.tag).apply()

    val langChosen: Boolean get() = p.contains("lang")

    var onboarded: Boolean
        get() = p.getBoolean("onboarded", false)
        set(v) = p.edit().putBoolean("onboarded", v).apply()

    var biometricUnlock: Boolean
        get() = p.getBoolean("bio_unlock", false)
        set(v) = p.edit().putBoolean("bio_unlock", v).apply()

    var notifications: Boolean
        get() = p.getBoolean("notify", true)
        set(v) = p.edit().putBoolean("notify", v).apply()

    // ------------------------------------------------------------ PIN

    val pin = PinPolicy(::hmac)

    var pinState: PinPolicy.State?
        get() {
            val salt = p.getString("pin_salt", null) ?: return null
            val ver = p.getString("pin_ver", null) ?: return null
            return PinPolicy.State(b64(salt), b64(ver), p.getInt("pin_fail", 0), p.getLong("pin_until", 0))
        }
        set(s) {
            val e = p.edit()
            if (s == null) {
                e.remove("pin_salt").remove("pin_ver").remove("pin_fail").remove("pin_until")
            } else {
                e.putString("pin_salt", b64(s.salt)).putString("pin_ver", b64(s.verifier))
                    .putInt("pin_fail", s.failures).putLong("pin_until", s.lockedUntil)
            }
            e.commit() // xatolar hisoblagichi jarayon o'ldirilsa ham saqlansin
        }

    fun newSalt(): ByteArray = ByteArray(16).also(SecureRandom()::nextBytes)

    private fun hmacKey(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (ks.getKey(PIN_KEY, null) as? SecretKey)?.let { return it }
        val spec = KeyGenParameterSpec.Builder(PIN_KEY, KeyProperties.PURPOSE_SIGN).build()
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_HMAC_SHA256, "AndroidKeyStore").apply { init(spec) }.generateKey()
    }

    private fun hmac(data: ByteArray): ByteArray = Mac.getInstance("HmacSHA256").run {
        init(hmacKey())
        doFinal(data)
    }

    // ------------------------------------------------------------ fon sinxronlash belgilari

    fun txnMarker(tokenId: String): String? = p.getString("txn_$tokenId", null)
    fun setTxnMarker(tokenId: String, id: String?) = p.edit().putString("txn_$tokenId", id).apply()

    /** Hamyonni tozalash: PIN, belgilar, sozlamalar (til qoladi). */
    fun reset() {
        val l = p.getString("lang", null)
        p.edit().clear().apply { if (l != null) putString("lang", l) }.commit()
        runCatching { KeyStore.getInstance("AndroidKeyStore").apply { load(null) }.deleteEntry(PIN_KEY) }
    }

    private fun b64(b: ByteArray) = Base64.encodeToString(b, Base64.NO_WRAP)
    private fun b64(s: String) = Base64.decode(s, Base64.NO_WRAP)

    companion object {
        private const val PIN_KEY = "mpay-app-pin"

        /** Tanlangan til bilan kontekst (Activity `attachBaseContext` va bildirishnomalar uchun). */
        fun localized(base: Context): Context {
            val lang = AppPrefs(base).lang
            val conf = Configuration(base.resources.configuration)
            conf.setLocale(lang.locale)
            return base.createConfigurationContext(conf)
        }
    }
}
