package uz.qarzsiz.app.data

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import kotlinx.serialization.json.Json
import java.io.File
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Holatni saqlash joyi. Ilovada — [Store] (shifrlangan fayl), testlarda — xotiradagi nusxa. */
interface StateStore {
    fun load(): LoadResult
    fun save(state: AppState)
    fun wipe()
}

sealed interface LoadResult {
    data class Ok(val state: AppState) : LoadResult
    data object Empty : LoadResult
    data class Broken(val reason: String) : LoadResult
}

/**
 * Holat qurilmada AES-256-GCM bilan shifrlanadi; kalit Android Keystore'da (ilovadan chiqarib bo'lmaydi).
 * Fayl: [12 bayt IV][shifrlangan JSON + 16 bayt teg]. Yozish atomar (AtomicFile).
 */
class Store(context: Context) : StateStore {
    private val file = AtomicFile(File(context.filesDir, FILE_NAME))

    override fun load(): LoadResult {
        if (!file.baseFile.exists()) return LoadResult.Empty
        return try {
            val bytes = file.readFully()
            val plain = decrypt(bytes)
            LoadResult.Ok(json.decodeFromString(AppState.serializer(), plain.decodeToString()))
        } catch (e: Exception) {
            LoadResult.Broken(e.javaClass.simpleName)
        }
    }

    override fun save(state: AppState) {
        val data = encrypt(json.encodeToString(AppState.serializer(), state).encodeToByteArray())
        val out = file.startWrite()
        try {
            out.write(data)
            file.finishWrite(out)
        } catch (e: Exception) {
            file.failWrite(out)
            throw e
        }
    }

    /** Hamma ma'lumotni o'chirish (kalit ham yangilanadi). */
    override fun wipe() {
        file.delete()
        runCatching { keyStore().deleteEntry(KEY_ALIAS) }
    }

    private fun keyStore(): KeyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    private fun key(): SecretKey {
        (keyStore().getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        gen.init(
            KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return gen.generateKey()
    }

    private fun encrypt(plain: ByteArray): ByteArray {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val iv = cipher.iv
        check(iv.size == IV_SIZE)
        return iv + cipher.doFinal(plain)
    }

    private fun decrypt(data: ByteArray): ByteArray {
        require(data.size > IV_SIZE) { "fayl juda qisqa" }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, data, 0, IV_SIZE))
        return cipher.doFinal(data, IV_SIZE, data.size - IV_SIZE)
    }

    companion object {
        private const val FILE_NAME = "qarzsiz.state"
        private const val KEY_ALIAS = "qarzsiz_state_v1"
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val IV_SIZE = 12

        val json = Json {
            ignoreUnknownKeys = true
            encodeDefaults = true
            prettyPrint = false
        }

        /** Zaxira nusxa (shifrlanmagan JSON) — foydalanuvchi o'zi tanlagan faylga. */
        private val exportJson = Json(json) { prettyPrint = true }

        fun exportText(state: AppState): String = exportJson.encodeToString(AppState.serializer(), state)

        fun importText(text: String): AppState = json.decodeFromString(AppState.serializer(), text)
    }
}
