package uz.barakadaftari.app.native

import android.os.Build
import android.os.Handler
import android.os.Looper
import android.view.WindowManager
import androidx.fragment.app.FragmentActivity
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * [SecurityApi] ning Kotlin tomondagi implementatsiyasi (Vazifa 2).
 *
 * Qoida: maxfiy qiymatlar (kalit, PIN, hosila) hech qachon loglanmaydi va
 * xato xabarlariga qo'shilmaydi.
 */
class SecurityApiImpl(
    private val databaseKeys: DatabaseKeyStore,
    private val blobs: SecureBlobStore,
    private val biometrics: BiometricAuthenticator,
    private val integrity: () -> IntegritySignals,
    private val activityProvider: () -> FragmentActivity?,
    private val documentPicker: DocumentPicker? = null,
    private val sdkInt: Int = Build.VERSION.SDK_INT,
    private val background: ExecutorService = Executors.newSingleThreadExecutor(),
    private val deliver: (Runnable) -> Unit = { Handler(Looper.getMainLooper()).post(it) },
) : SecurityApi {

    override fun ping(): NativeInfo =
        NativeInfo(apiVersion = API_VERSION, androidSdkInt = sdkInt.toLong())

    override fun getOrCreateDatabaseKey(callback: (Result<ByteArray>) -> Unit) =
        runInBackground(callback, "DB_KEY") { databaseKeys.getOrCreate() }

    override fun derivePinKey(
        pin: String,
        salt: ByteArray,
        iterations: Long,
        callback: (Result<ByteArray>) -> Unit,
    ) {
        if (iterations < PinKdf.MIN_ITERATIONS || iterations > Int.MAX_VALUE || salt.size < MIN_SALT) {
            callback(Result.failure(FlutterError(CODE_INVALID_ARGUMENT, "KDF parametrlari noto'g'ri", null)))
            return
        }
        val chars = pin.toCharArray()
        runInBackground(callback, "KDF") {
            try {
                PinKdf.derive(chars, salt, iterations.toInt())
            } finally {
                chars.fill('\u0000')
            }
        }
    }

    override fun encryptBackup(
        password: String,
        plain: ByteArray,
        callback: (Result<ByteArray>) -> Unit,
    ) {
        if (password.length < MIN_BACKUP_PASSWORD) {
            callback(Result.failure(FlutterError(CODE_INVALID_ARGUMENT, "Parol juda qisqa", null)))
            return
        }
        val chars = password.toCharArray()
        runInBackground(callback, "BACKUP") {
            try {
                BackupCipher.encrypt(chars, plain)
            } finally {
                chars.fill('\u0000')
            }
        }
    }

    override fun decryptBackup(
        password: String,
        data: ByteArray,
        callback: (Result<ByteArray>) -> Unit,
    ) {
        val chars = password.toCharArray()
        runInBackground(callback, "BACKUP") {
            try {
                BackupCipher.decrypt(chars, data)
            } catch (e: BackupCipher.BadPasswordException) {
                throw FlutterError(CODE_BACKUP_BAD_PASSWORD, null, null)
            } catch (e: BackupCipher.FormatException) {
                throw FlutterError(CODE_BACKUP_FORMAT, null, null)
            } finally {
                chars.fill('\u0000')
            }
        }
    }

    override fun pickBackupFile(callback: (Result<ByteArray?>) -> Unit) {
        val picker = documentPicker
            ?: return callback(Result.failure(FlutterError("PICK_UNAVAILABLE", null, null)))
        picker.pick { reader ->
            if (reader == null) {
                deliver { callback(Result.success(null)) }
            } else {
                runInBackground<ByteArray?>(callback, "PICK") { reader() }
            }
        }
    }

    override fun readSecureBlob(name: String): ByteArray? = guarded("BLOB") { blobs.read(name) }

    override fun writeSecureBlob(name: String, data: ByteArray) = guarded("BLOB") { blobs.write(name, data) }

    override fun deleteSecureBlob(name: String) = guarded("BLOB") { blobs.delete(name) }

    override fun getBiometricAvailability(): BiometricAvailability = biometrics.availability()

    override fun authenticate(
        title: String,
        subtitle: String,
        cancelLabel: String,
        callback: (Result<BiometricOutcome>) -> Unit,
    ) = biometrics.authenticate(title, subtitle, cancelLabel, callback)

    override fun setSecureFlag(enabled: Boolean) {
        val activity = activityProvider() ?: return
        activity.runOnUiThread {
            if (enabled) {
                activity.window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
            } else {
                activity.window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
            }
        }
    }

    override fun getIntegritySignals(): IntegritySignals = integrity()

    private fun <T> runInBackground(callback: (Result<T>) -> Unit, code: String, work: () -> T) {
        background.execute {
            val result = try {
                Result.success(work())
            } catch (e: FlutterError) {
                Result.failure(e)
            } catch (e: Exception) {
                // Xabarga faqat istisno turi qo'shiladi — ichida maxfiy ma'lumot bo'lmasin.
                Result.failure(FlutterError("${code}_FAILED", e.javaClass.simpleName, null))
            }
            deliver { callback(result) }
        }
    }

    private inline fun <T> guarded(code: String, work: () -> T): T = try {
        work()
    } catch (e: IllegalArgumentException) {
        throw FlutterError(CODE_INVALID_ARGUMENT, e.message, null)
    } catch (e: Exception) {
        throw FlutterError("${code}_FAILED", e.javaClass.simpleName, null)
    }

    companion object {
        /** Pigeon kontrakti versiyasi; `pigeons/security_api.dart` o'zgarsa oshiriladi. */
        const val API_VERSION = 4L
        const val MIN_SALT = 16
        const val CODE_INVALID_ARGUMENT = "INVALID_ARGUMENT"
        const val CODE_BACKUP_BAD_PASSWORD = "BACKUP_BAD_PASSWORD"
        const val CODE_BACKUP_FORMAT = "BACKUP_FORMAT"
        const val MIN_BACKUP_PASSWORD = 8
    }
}

/**
 * Hujjat tanlash (MainActivity: `ActivityResultContracts.OpenDocument`).
 * Natija — fon oqimida chaqiriladigan o'qish funksiyasi yoki `null` (bekor).
 */
fun interface DocumentPicker {
    fun pick(onPicked: ((() -> ByteArray)?) -> Unit)
}
