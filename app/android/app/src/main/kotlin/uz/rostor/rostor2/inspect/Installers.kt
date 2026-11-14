package uz.rostor.rostor2.inspect

import android.content.pm.PackageManager
import android.os.Build

/** Ilovani kim o'rnatgani: do'kon yoki APK faylini ochgan ilova (masalan Telegram). */
object Installers {
    fun of(pm: PackageManager, pkg: String): Map<String, String?> {
        return try {
            if (Build.VERSION.SDK_INT >= 30) {
                val s = pm.getInstallSourceInfo(pkg)
                mapOf(
                    "installing" to s.installingPackageName,
                    "initiating" to s.initiatingPackageName,
                )
            } else {
                @Suppress("DEPRECATION")
                mapOf("installing" to pm.getInstallerPackageName(pkg), "initiating" to null)
            }
        } catch (e: Exception) {
            mapOf("installing" to null, "initiating" to null)
        }
    }
}
