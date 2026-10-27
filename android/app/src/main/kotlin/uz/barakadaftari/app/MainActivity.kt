package uz.barakadaftari.app

import android.net.Uri
import androidx.activity.result.contract.ActivityResultContracts
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import uz.barakadaftari.app.native.AesGcmKeyWrapper
import uz.barakadaftari.app.native.BiometricAuthenticator
import uz.barakadaftari.app.native.DatabaseKeyStore
import uz.barakadaftari.app.native.DocumentPicker
import uz.barakadaftari.app.native.FlutterError
import uz.barakadaftari.app.native.IntegrityChecker
import uz.barakadaftari.app.native.KeystoreKeys
import uz.barakadaftari.app.native.ReminderApi
import uz.barakadaftari.app.native.ReminderApiImpl
import uz.barakadaftari.app.native.SecureBlobStore
import uz.barakadaftari.app.native.SecurityApi
import uz.barakadaftari.app.native.SecurityApiImpl
import uz.barakadaftari.app.native.WidgetApi
import uz.barakadaftari.app.native.WidgetApiImpl
import java.io.File

/** BiometricPrompt FragmentActivity talab qiladi, shu sabab FlutterFragmentActivity. */
class MainActivity : FlutterFragmentActivity() {
    // Zaxira faylini tanlash (Vazifa 15): file_selector plagini R8 release'da
    // ishga tushishni buzgani uchun o'zimizning ACTION_OPEN_DOCUMENT.
    private var onDocument: ((Uri?) -> Unit)? = null
    private val openDocument = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        val handler = onDocument
        onDocument = null
        handler?.invoke(uri)
    }

    private val documentPicker = DocumentPicker { onPicked ->
        runOnUiThread {
            // Oldingi tugallanmagan so'rov bekor qilingan deb yopiladi.
            onDocument?.invoke(null)
            onDocument = { uri -> onPicked(uri?.let { u -> { readLimited(u) } }) }
            openDocument.launch(arrayOf("*/*"))
        }
    }

    private fun readLimited(uri: Uri): ByteArray {
        val input = contentResolver.openInputStream(uri) ?: throw IllegalStateException("stream")
        return input.use {
            val out = java.io.ByteArrayOutputStream()
            val buf = ByteArray(64 * 1024)
            while (true) {
                val n = it.read(buf)
                if (n < 0) break
                out.write(buf, 0, n)
                if (out.size() > MAX_BACKUP_BYTES) {
                    throw FlutterError("PICK_TOO_LARGE", null, null)
                }
            }
            out.toByteArray()
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val keys = KeystoreKeys(applicationContext)
        val blobs = SecureBlobStore(
            dir = File(applicationContext.noBackupFilesDir, "secure"),
            wrapper = AesGcmKeyWrapper(keys::getOrCreateWrappingKey),
        )
        val integrity = IntegrityChecker(applicationContext, BuildConfig.EXPECTED_SIGNATURE_SHA256)
        SecurityApi.setUp(
            flutterEngine.dartExecutor.binaryMessenger,
            SecurityApiImpl(
                databaseKeys = DatabaseKeyStore(blobs),
                blobs = blobs,
                biometrics = BiometricAuthenticator { this },
                integrity = integrity::collect,
                activityProvider = { this },
                documentPicker = documentPicker,
            ),
        )
        ReminderApi.setUp(
            flutterEngine.dartExecutor.binaryMessenger,
            ReminderApiImpl(applicationContext) { this },
        )
        // Ilova qulfli holda ishga tushadi — vidjet summalari darhol yashiriladi.
        WidgetApiImpl.applyVisibleUntil(applicationContext, 0L)
        WidgetApi.setUp(flutterEngine.dartExecutor.binaryMessenger, WidgetApiImpl(applicationContext))
    }

    override fun cleanUpFlutterEngine(flutterEngine: FlutterEngine) {
        SecurityApi.setUp(flutterEngine.dartExecutor.binaryMessenger, null)
        ReminderApi.setUp(flutterEngine.dartExecutor.binaryMessenger, null)
        WidgetApi.setUp(flutterEngine.dartExecutor.binaryMessenger, null)
        super.cleanUpFlutterEngine(flutterEngine)
    }

    companion object {
        private const val MAX_BACKUP_BYTES = 64 * 1024 * 1024
    }
}
