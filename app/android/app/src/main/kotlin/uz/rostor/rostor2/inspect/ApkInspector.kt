package uz.rostor.rostor2.inspect

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.Drawable
import android.net.Uri
import android.os.Build
import android.provider.OpenableColumns
import com.android.apksig.ApkVerifier
import uz.rostor.rostor2.crypto.toHex
import java.io.ByteArrayOutputStream
import java.io.File
import java.security.MessageDigest

/**
 * APK Qalqon (T1) — faylni o'rnatmasdan, qurilmaning o'zida tahlil qiladi.
 * Faktlarni yig'adi; hukm chiqarish (qoidalar) Dart tomonida, bazadagi reestrlar bilan.
 */
class ApkInspector(private val ctx: Context) {
    private val pm: PackageManager = ctx.packageManager

    companion object {
        const val MAX_BYTES = 512L * 1024 * 1024
    }

    fun inspect(uri: Uri): Map<String, Any?> {
        val (displayName, declaredSize) = queryNameSize(uri)
        val dir = File(ctx.cacheDir, "inspect").apply { mkdirs() }
        val tmp = File(dir, "${System.nanoTime()}.apk")
        try {
            val md = MessageDigest.getInstance("SHA-256")
            var total = 0L
            val input = ctx.contentResolver.openInputStream(uri)
                ?: return error("Faylni ochib bo'lmadi", displayName)
            input.use { inp ->
                tmp.outputStream().use { out ->
                    val buf = ByteArray(64 * 1024)
                    while (true) {
                        val n = inp.read(buf)
                        if (n < 0) break
                        total += n
                        if (total > MAX_BYTES) return error("Fayl juda katta (512 MB dan ortiq)", displayName)
                        md.update(buf, 0, n)
                        out.write(buf, 0, n)
                    }
                }
            }
            val result = analyze(tmp).toMutableMap()
            result["fileName"] = displayName
            result["fileSize"] = if (total > 0) total else declaredSize
            result["fileSha256"] = md.digest().toHex()
            return result
        } catch (e: SecurityException) {
            return error("Faylga ruxsat berilmadi", displayName)
        } catch (e: Exception) {
            return error("Faylni o'qishda xato: ${e.javaClass.simpleName}", displayName)
        } finally {
            tmp.delete()
        }
    }

    private fun error(msg: String, name: String?) = mapOf("ok" to false, "error" to msg, "fileName" to name)

    private fun queryNameSize(uri: Uri): Pair<String?, Long> {
        if (uri.scheme == "file") {
            val f = File(uri.path ?: "")
            return f.name to f.length()
        }
        return try {
            ctx.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE), null, null, null)
                ?.use { c ->
                    if (c.moveToFirst()) {
                        val name = c.getColumnIndex(OpenableColumns.DISPLAY_NAME).let { if (it >= 0) c.getString(it) else null }
                        val size = c.getColumnIndex(OpenableColumns.SIZE).let { if (it >= 0 && !c.isNull(it)) c.getLong(it) else -1L }
                        name to size
                    } else null to -1L
                } ?: (null to -1L)
        } catch (e: Exception) {
            null to -1L
        }
    }

    fun analyze(file: File): Map<String, Any?> {
        val out = mutableMapOf<String, Any?>("ok" to true)

        // 1) Imzo: APK Signature Scheme v1–v4 (apksig).
        try {
            val res = ApkVerifier.Builder(file).build().verify()
            val certs = res.signerCertificates ?: emptyList()
            out["sigVerified"] = res.isVerified
            out["sigSchemes"] = listOfNotNull(
                "v1".takeIf { res.isVerifiedUsingV1Scheme },
                "v2".takeIf { res.isVerifiedUsingV2Scheme },
                "v3".takeIf { res.isVerifiedUsingV3Scheme },
                "v3.1".takeIf { res.isVerifiedUsingV31Scheme },
                "v4".takeIf { res.isVerifiedUsingV4Scheme },
            )
            out["signers"] = certs.map { Certs.describe(it) }
            out["lineage"] = try {
                res.signingCertificateLineage?.certificatesInLineage?.map { Certs.sha256Hex(it.encoded) } ?: emptyList()
            } catch (e: Exception) {
                emptyList<String>()
            }
            out["sigErrors"] = res.errors.take(5).map { it.toString() }
        } catch (e: Exception) {
            out["sigVerified"] = false
            out["sigSchemes"] = emptyList<String>()
            out["signers"] = emptyList<Any>()
            out["sigErrors"] = listOf("APK tuzilmasi o'qilmadi: ${e.javaClass.simpleName}")
        }

        // 2) Manifest: paket, nom, ruxsatlar, xavfli komponentlar.
        val flags = PackageManager.GET_PERMISSIONS or PackageManager.GET_SERVICES or
            PackageManager.GET_RECEIVERS or PackageManager.GET_ACTIVITIES
        val pi: PackageInfo? = try {
            if (Build.VERSION.SDK_INT >= 33) {
                pm.getPackageArchiveInfo(file.path, PackageManager.PackageInfoFlags.of(flags.toLong()))
            } else {
                @Suppress("DEPRECATION")
                pm.getPackageArchiveInfo(file.path, flags)
            }
        } catch (e: Exception) {
            null
        }
        if (pi == null) {
            out["parsed"] = false
            return out
        }
        out["parsed"] = true
        val ai = pi.applicationInfo
        if (ai != null) {
            ai.sourceDir = file.path
            ai.publicSourceDir = file.path
            out["label"] = try { ai.loadLabel(pm).toString() } catch (e: Exception) { null }
            out["icon"] = try { drawableToPng(ai.loadIcon(pm)) } catch (e: Exception) { null }
            out["targetSdk"] = ai.targetSdkVersion
            out["minSdk"] = if (Build.VERSION.SDK_INT >= 24) ai.minSdkVersion else null
        }
        out["packageName"] = pi.packageName
        out["versionName"] = pi.versionName
        out["versionCode"] = if (Build.VERSION.SDK_INT >= 28) pi.longVersionCode else @Suppress("DEPRECATION") pi.versionCode.toLong()
        out["permissions"] = pi.requestedPermissions?.toList() ?: emptyList<String>()
        val services = pi.services ?: emptyArray()
        out["accessibilityServices"] = services.filter { it.permission == Manifest.permission.BIND_ACCESSIBILITY_SERVICE }.map { it.name }
        out["notificationListeners"] = services.filter { it.permission == Manifest.permission.BIND_NOTIFICATION_LISTENER_SERVICE }.map { it.name }
        out["deviceAdmins"] = (pi.receivers ?: emptyArray()).filter { it.permission == Manifest.permission.BIND_DEVICE_ADMIN }.map { it.name }
        out["activityCount"] = pi.activities?.size ?: 0
        out["serviceCount"] = services.size
        out["receiverCount"] = pi.receivers?.size ?: 0

        // 3) Qurilmadagi o'rnatilgan nusxa bilan solishtirish (TOFU: Play'dan kelgan sertifikat).
        out["installed"] = installedCopy(pi.packageName)
        out["sameLabelInstalled"] = sameLabelInstalled(out["label"] as String?, pi.packageName)
        return out
    }

    private fun installedCopy(pkg: String): Map<String, Any?>? {
        val ipi = try { pm.getPackageInfo(pkg, Certs.signatureFlag()) } catch (e: PackageManager.NameNotFoundException) { return null }
        val (current, history) = Certs.ofInstalled(ipi)
        return mapOf(
            "versionName" to ipi.versionName,
            "certSha256" to current.map { Certs.sha256Hex(it) },
            "historySha256" to history.map { Certs.sha256Hex(it) },
            "installer" to Installers.of(pm, pkg),
        )
    }

    /** Fayl nomi bilan bir xil nomli, lekin boshqa paketdagi o'rnatilgan ilovalar (taqlid belgisi). */
    private fun sameLabelInstalled(label: String?, pkg: String): List<Map<String, Any?>> {
        if (label.isNullOrBlank()) return emptyList()
        val target = label.trim().lowercase()
        val launcher = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val found = mutableListOf<Map<String, Any?>>()
        val seen = HashSet<String>()
        for (ri in pm.queryIntentActivities(launcher, 0)) {
            val p = ri.activityInfo.packageName
            if (p == pkg || !seen.add(p)) continue
            val l = try { ri.loadLabel(pm).toString() } catch (e: Exception) { continue }
            if (l.trim().lowercase() == target) {
                val ipi = try { pm.getPackageInfo(p, Certs.signatureFlag()) } catch (e: Exception) { null }
                val certs: List<String> = ipi?.let { Certs.ofInstalled(it).first.map { c -> Certs.sha256Hex(c) } } ?: emptyList()
                found.add(
                    mapOf(
                        "packageName" to p,
                        "label" to l,
                        "installer" to Installers.of(pm, p),
                        "certSha256" to certs,
                    )
                )
            }
        }
        return found
    }

    private fun drawableToPng(d: Drawable, size: Int = 96): ByteArray {
        val bmp = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
        val c = Canvas(bmp)
        d.setBounds(0, 0, size, size)
        d.draw(c)
        return ByteArrayOutputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it); it.toByteArray() }
    }
}
