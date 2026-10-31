package uz.epiradar.app

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings as AndroidSettings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Flutter UI ↔ Kotlin yadro ko'prigi. Barcha ma'lumot JSON matn sifatida uzatiladi
 * (format: engine/json/Codec.kt; Dart tomoni: lib/data/models.dart).
 */
class MainActivity : FlutterActivity() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val repo by lazy { (application as EpiRadarApp).repository }
    private var pendingPermission: MethodChannel.Result? = null
    private var launchEventId: String? = null
    private var channel: MethodChannel? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        // "So'nggi ilovalar"dan qayta ochilganda eski bildirishnoma intent'i qayta keladi — uni e'tiborsiz qoldiramiz.
        val fromHistory = ((intent?.flags ?: 0) and Intent.FLAG_ACTIVITY_LAUNCHED_FROM_HISTORY) != 0
        launchEventId = if (fromHistory) null else intent?.getStringExtra(Notifier.EXTRA_EVENT_ID)
        channel =
            MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).also {
                it.setMethodCallHandler(::handle)
            }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        intent.getStringExtra(Notifier.EXTRA_EVENT_ID)?.let { id ->
            // Dart hali tayyor bo'lmasa ham yo'qolmasin: consumeLaunchEventId orqali ham olinadi.
            launchEventId = id
            channel?.invokeMethod(
                "openEvent",
                id,
                object : MethodChannel.Result {
                    override fun success(result: Any?) {
                        // Dart `true` qaytarsa — hodisa ochildi; aks holda ishga tushishda consumeLaunchEventId oladi.
                        if (result == true && launchEventId == id) launchEventId = null
                    }

                    override fun error(
                        code: String,
                        message: String?,
                        details: Any?,
                    ) = Unit

                    override fun notImplemented() = Unit
                },
            )
        }
    }

    private fun handle(
        call: MethodCall,
        result: MethodChannel.Result,
    ) {
        when (call.method) {
            "getSnapshot" -> async(result) { repo.current()?.let(repo::encode) }
            "refresh" ->
                async(result) {
                    val r = repo.sync()
                    r.notifications.forEach { Notifier.show(this, it) }
                    RiskWidgetProvider.update(this, r.snapshot)
                    repo.encode(r.snapshot)
                }
            "getSettings" -> result.success(repo.engine.codec.encodeSettings(repo.settings()).toString())
            "saveSettings" ->
                async(result) {
                    val saved = repo.saveSettings(call.arguments as String)
                    repo.current()?.let { RiskWidgetProvider.update(this, it) }
                    repo.engine.codec.encodeSettings(saved).toString()
                }
            "getCatalog" -> async(result) { repo.catalogJson() }
            "lastSync" -> result.success(repo.lastSync())
            "consumeLaunchEventId" -> {
                result.success(launchEventId)
                launchEventId = null
            }
            "notificationStatus" -> result.success(notificationStatus())
            "requestNotificationPermission" -> requestNotificationPermission(result)
            "openNotificationSettings" -> {
                startSafely(Intent(AndroidSettings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(AndroidSettings.EXTRA_APP_PACKAGE, packageName))
                result.success(true)
            }
            "openUrl" -> {
                val url = call.arguments as? String
                // Faqat HTTPS havolalar (manba sahifalari, tarjima) ochiladi.
                result.success(url != null && url.startsWith("https://") && startSafely(Intent(Intent.ACTION_VIEW, Uri.parse(url))))
            }
            "share" -> {
                val text = call.arguments as? String ?: ""
                val send = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text)
                result.success(startSafely(Intent.createChooser(send, null)))
            }
            "dial" -> {
                val number = (call.arguments as? String).orEmpty().filter { it.isDigit() || it == '+' }
                result.success(number.isNotEmpty() && startSafely(Intent(Intent.ACTION_DIAL, Uri.parse("tel:$number"))))
            }
            else -> result.notImplemented()
        }
    }

    private fun async(
        result: MethodChannel.Result,
        block: suspend () -> Any?,
    ) {
        scope.launch {
            try {
                result.success(block())
            } catch (e: Exception) {
                result.error("ENGINE", e.message ?: e::class.java.simpleName, null)
            }
        }
    }

    private fun notificationStatus(): String =
        when {
            Notifier.canNotify(this) -> "granted"
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED -> "denied"
            else -> "disabled"
        }

    private fun requestNotificationPermission(result: MethodChannel.Result) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        ) {
            result.success(notificationStatus())
            return
        }
        pendingPermission?.success(notificationStatus())
        pendingPermission = result
        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQ_NOTIFICATIONS)
    }

    @Deprecated("FlutterActivity hali Activity Result API'ga o'tmagan")
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        @Suppress("DEPRECATION")
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQ_NOTIFICATIONS) {
            pendingPermission?.success(notificationStatus())
            pendingPermission = null
        }
    }

    private fun startSafely(intent: Intent): Boolean =
        try {
            startActivity(intent)
            true
        } catch (_: ActivityNotFoundException) {
            false
        }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        const val CHANNEL = "uz.epiradar/engine"
        private const val REQ_NOTIFICATIONS = 41
    }
}
