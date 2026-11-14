package uz.rostor.rostor2.inspect

import android.accessibilityservice.AccessibilityServiceInfo
import android.app.AppOpsManager
import android.app.KeyguardManager
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import android.provider.Telephony
import android.view.accessibility.AccessibilityManager
import java.io.File

/**
 * Qurilma auditi (T1 o'rnatilgandan keyin, T7): bank troyanlari foydalanadigan kuchli
 * imkoniyatlarga kim ega ekanini aniqlaydi. Faqat o'qiydi, hech narsani o'zgartirmaydi.
 */
class DeviceAuditor(private val ctx: Context) {
    private val pm = ctx.packageManager

    fun audit(): Map<String, Any?> {
        val a11y = enabledAccessibility()
        val listeners = enabledNotificationListeners()
        val admins = activeAdmins()
        val defaultSms = try { Telephony.Sms.getDefaultSmsPackage(ctx) } catch (e: Exception) { null }
        val launcherPkgs = pm.queryIntentActivities(
            Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER), 0
        ).map { it.activityInfo.packageName }.toHashSet()

        val flags = PackageManager.GET_PERMISSIONS or Certs.signatureFlag()
        val pkgs: List<PackageInfo> = if (Build.VERSION.SDK_INT >= 33) {
            pm.getInstalledPackages(PackageManager.PackageInfoFlags.of(flags.toLong()))
        } else {
            @Suppress("DEPRECATION") pm.getInstalledPackages(flags)
        }

        val apps = pkgs.mapNotNull { pi ->
            val ai = pi.applicationInfo ?: return@mapNotNull null
            if (pi.packageName == ctx.packageName) return@mapNotNull null
            val system = (ai.flags and ApplicationInfo.FLAG_SYSTEM) != 0
            val requested = pi.requestedPermissions?.toList() ?: emptyList()
            val granted = requested.filterIndexed { i, _ ->
                val f = pi.requestedPermissionsFlags?.getOrNull(i) ?: 0
                (f and PackageInfo.REQUESTED_PERMISSION_GRANTED) != 0
            }
            val pkg = pi.packageName
            // Tizim ilovalaridan faqat kuchli imkoniyat olganlari ro'yxatga kiradi.
            val holdsPower = pkg in a11y || pkg in listeners || pkg in admins || pkg == defaultSms
            if (system && !holdsPower) return@mapNotNull null
            mapOf(
                "packageName" to pkg,
                "label" to (try { ai.loadLabel(pm).toString() } catch (e: Exception) { pkg }),
                "versionName" to pi.versionName,
                "system" to system,
                "updatedSystem" to ((ai.flags and ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0),
                "targetSdk" to ai.targetSdkVersion,
                "firstInstall" to pi.firstInstallTime,
                "lastUpdate" to pi.lastUpdateTime,
                "installer" to Installers.of(pm, pkg),
                "hasLauncher" to (pkg in launcherPkgs),
                "requested" to requested,
                "granted" to granted,
                "certSha256" to Certs.ofInstalled(pi).first.map { Certs.sha256Hex(it) },
                "certDebug" to Certs.ofInstalled(pi).first.any {
                    Certs.parse(it)?.subjectX500Principal?.name?.contains("CN=Android Debug") == true
                },
                "accessibilityOn" to (pkg in a11y),
                "notificationListenerOn" to (pkg in listeners),
                "deviceAdminOn" to (pkg in admins),
                "defaultSms" to (pkg == defaultSms),
                "overlayAllowed" to if ("android.permission.SYSTEM_ALERT_WINDOW" in requested)
                    opAllowed("android:system_alert_window", ai.uid, pkg, "android.permission.SYSTEM_ALERT_WINDOW") else false,
                "installUnknownAllowed" to if ("android.permission.REQUEST_INSTALL_PACKAGES" in requested)
                    opAllowed("android:request_install_packages", ai.uid, pkg, "android.permission.REQUEST_INSTALL_PACKAGES") else false,
            )
        }
        return mapOf("apps" to apps, "device" to posture(), "scannedAt" to System.currentTimeMillis())
    }

    private fun enabledAccessibility(): Set<String> {
        val out = HashSet<String>()
        try {
            val am = ctx.getSystemService(Context.ACCESSIBILITY_SERVICE) as AccessibilityManager
            am.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)
                .forEach { out += it.resolveInfo.serviceInfo.packageName }
        } catch (e: Exception) { }
        secureList(Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES).forEach { out += it }
        return out
    }

    private fun enabledNotificationListeners(): Set<String> = secureList("enabled_notification_listeners").toSet()

    private fun secureList(key: String): List<String> = try {
        Settings.Secure.getString(ctx.contentResolver, key)
            ?.split(':')
            ?.mapNotNull { ComponentName.unflattenFromString(it)?.packageName }
            ?: emptyList()
    } catch (e: Exception) {
        emptyList()
    }

    private fun activeAdmins(): Set<String> = try {
        val dpm = ctx.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        dpm.activeAdmins?.map { it.packageName }?.toSet() ?: emptySet()
    } catch (e: Exception) {
        emptySet()
    }

    /** AppOps holati; MODE_DEFAULT bo'lsa ruxsatning o'zi hal qiladi. Aniqlab bo'lmasa null. */
    private fun opAllowed(op: String, uid: Int, pkg: String, perm: String): Boolean? = try {
        val aom = ctx.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = if (Build.VERSION.SDK_INT >= 29) aom.unsafeCheckOpNoThrow(op, uid, pkg)
        else @Suppress("DEPRECATION") aom.checkOpNoThrow(op, uid, pkg)
        when (mode) {
            AppOpsManager.MODE_ALLOWED -> true
            AppOpsManager.MODE_DEFAULT -> pm.checkPermission(perm, pkg) == PackageManager.PERMISSION_GRANTED
            else -> false
        }
    } catch (e: Exception) {
        null
    }

    private fun posture(): Map<String, Any?> {
        val km = ctx.getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager
        val suPaths = listOf("/system/xbin/su", "/system/bin/su", "/sbin/su", "/su/bin/su", "/data/local/xbin/su", "/data/local/bin/su")
        return mapOf(
            "sdkInt" to Build.VERSION.SDK_INT,
            "release" to Build.VERSION.RELEASE,
            "securityPatch" to Build.VERSION.SECURITY_PATCH,
            "manufacturer" to Build.MANUFACTURER,
            "model" to Build.MODEL,
            "screenLock" to km.isDeviceSecure,
            "developerOptions" to (Settings.Global.getInt(ctx.contentResolver, Settings.Global.DEVELOPMENT_SETTINGS_ENABLED, 0) == 1),
            "adbEnabled" to (Settings.Global.getInt(ctx.contentResolver, Settings.Global.ADB_ENABLED, 0) == 1),
            "rootIndicators" to (suPaths.filter { File(it).exists() } + listOfNotNull("test-keys".takeIf { Build.TAGS?.contains("test-keys") == true })),
        )
    }

    /**
     * Q4: doimiy fon xizmatisiz "oxirgi tekshiruvdan beri nima o'zgardi". Ketma-ketlik raqami
     * qurilma qayta yuklanganda nolga tushadi — u holda null qaytadi va to'liq audit tavsiya etiladi.
     */
    fun changedSince(seq: Int): Map<String, Any?> {
        val ch = pm.getChangedPackages(seq)
        return mapOf(
            "sequence" to (ch?.sequenceNumber ?: seq),
            "packages" to (ch?.packageNames?.filter { it != ctx.packageName } ?: emptyList()),
        )
    }
}
