package uz.baraka.oilasi

import android.os.Bundle
import android.view.WindowManager
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine

/**
 * Yagona oyna. `FLAG_SECURE` standart holda yoqiq (7.4): ilovaning hamma ekrani moliyaviy —
 * skrinshot va «so'nggi ilovalar» ko'rinishi qora.
 */
class MainActivity : FlutterFragmentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
        super.onCreate(savedInstanceState)
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val messenger = flutterEngine.dartExecutor.binaryMessenger
        PlatformSecretApi.setUp(messenger, PlatformSecretStore(applicationContext))
        SecureWindowApi.setUp(messenger, object : SecureWindowApi {
            override fun setSecure(secure: Boolean) {
                runOnUiThread {
                    if (secure) {
                        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
                    } else {
                        window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
                    }
                }
            }
        })
    }
}
