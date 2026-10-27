package uz.barakadaftari.app.native

import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import android.os.Debug
import java.io.File
import java.security.MessageDigest

/** Build va muhit belgilari — testda soxta qiymat berish uchun alohida. */
data class DeviceFingerprint(
    val fingerprint: String,
    val model: String,
    val manufacturer: String,
    val brand: String,
    val device: String,
    val product: String,
    val hardware: String,
    val tags: String,
) {
    companion object {
        fun current() = DeviceFingerprint(
            fingerprint = Build.FINGERPRINT.orEmpty(),
            model = Build.MODEL.orEmpty(),
            manufacturer = Build.MANUFACTURER.orEmpty(),
            brand = Build.BRAND.orEmpty(),
            device = Build.DEVICE.orEmpty(),
            product = Build.PRODUCT.orEmpty(),
            hardware = Build.HARDWARE.orEmpty(),
            tags = Build.TAGS.orEmpty(),
        )
    }
}

/**
 * Root/emulyator evristikalari. Bular aniq dalil emas — faqat ogohlantirish
 * uchun signal (MVP'da ilova bloklanmaydi).
 */
object IntegrityHeuristics {
    val SU_PATHS = listOf(
        "/system/bin/su", "/system/xbin/su", "/sbin/su", "/system/su",
        "/system/bin/.ext/su", "/system/usr/we-need-root/su", "/data/local/su",
        "/data/local/bin/su", "/data/local/xbin/su", "/su/bin/su",
        "/system/app/Superuser.apk", "/system/xbin/daemonsu",
        "/data/adb/magisk", "/sbin/.magisk", "/cache/.disable_magisk",
    )

    fun isRooted(device: DeviceFingerprint, exists: (String) -> Boolean): Boolean =
        device.tags.contains("test-keys") || SU_PATHS.any(exists)

    fun isEmulator(d: DeviceFingerprint): Boolean =
        d.fingerprint.startsWith("generic") ||
            d.fingerprint.startsWith("unknown") ||
            d.fingerprint.contains("emulator") ||
            d.model.contains("google_sdk") ||
            d.model.contains("Emulator") ||
            d.model.contains("Android SDK built for") ||
            d.model.startsWith("sdk_gphone") ||
            d.manufacturer.contains("Genymotion") ||
            (d.brand.startsWith("generic") && d.device.startsWith("generic")) ||
            d.product.startsWith("sdk") ||
            d.product.contains("emulator") ||
            d.product.contains("simulator") ||
            d.hardware == "goldfish" ||
            d.hardware == "ranchu"

    /** Hex (katta harf), ajratgichsiz. */
    fun sha256Hex(bytes: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02X".format(it) }

    /** Kutilgan xesh bo'sh bo'lsa `null` — tekshiruv sozlanmagan. */
    fun signatureMatches(actualHex: String, expectedHex: String): Boolean? {
        val expected = expectedHex.replace(":", "").trim().uppercase()
        if (expected.isEmpty()) return null
        return actualHex.isNotEmpty() && MessageDigest.isEqual(
            actualHex.toByteArray(),
            expected.toByteArray(),
        )
    }
}

class IntegrityChecker(
    private val context: Context,
    private val expectedSignatureSha256: String,
) {
    fun collect(): IntegritySignals {
        val device = DeviceFingerprint.current()
        val signature = signingCertificateSha256()
        return IntegritySignals(
            isRooted = IntegrityHeuristics.isRooted(device) { File(it).exists() },
            isEmulator = IntegrityHeuristics.isEmulator(device),
            isDebuggerAttached = Debug.isDebuggerConnected() || Debug.waitingForDebugger(),
            isDebuggableBuild =
                (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0,
            signatureSha256 = signature,
            isSignatureValid = IntegrityHeuristics.signatureMatches(signature, expectedSignatureSha256),
        )
    }

    @SuppressLint("PackageManagerGetSignatures")
    @Suppress("DEPRECATION")
    private fun signingCertificateSha256(): String {
        val pm = context.packageManager
        val name = context.packageName
        val certs = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            val info = pm.getPackageInfo(name, PackageManager.GET_SIGNING_CERTIFICATES).signingInfo
                ?: return ""
            if (info.hasMultipleSigners()) info.apkContentsSigners else info.signingCertificateHistory
        } else {
            pm.getPackageInfo(name, PackageManager.GET_SIGNATURES).signatures
        }
        val first = certs?.firstOrNull() ?: return ""
        return IntegrityHeuristics.sha256Hex(first.toByteArray())
    }
}
