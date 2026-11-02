package uz.rostor.rostor2

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import uz.rostor.rostor2.call.CallShield
import uz.rostor.rostor2.db.DbBundle
import uz.rostor.rostor2.db.DbKeys
import uz.rostor.rostor2.db.DbLoader
import uz.rostor.rostor2.inspect.ApkInspector
import uz.rostor.rostor2.inspect.Certs
import uz.rostor.rostor2.inspect.DeviceAuditor
import uz.rostor.rostor2.inspect.Installers
import uz.rostor.rostor2.report.ReportCodec
import uz.rostor.rostor2.report.ReportFileProvider
import uz.rostor.rostor2.report.ReporterKeys
import java.util.concurrent.Executors

/**
 * Flutter UI va Android API orasidagi yagona ko'prik. Og'ir ishlar (APK tahlili, audit)
 * fon oqimida bajariladi, natija asosiy oqimda qaytariladi.
 */
class MainActivity : FlutterActivity() {
    private lateinit var channel: MethodChannel
    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private var pendingPick: MethodChannel.Result? = null
    private var pendingRole: MethodChannel.Result? = null
    private var pendingNotif: MethodChannel.Result? = null
    private var pendingIncoming: Map<String, Any?>? = null

    // Qo'ng'iroq Qalqoni xizmati tarixga yozganda ochiq ekran darhol yangilanadi.
    // SharedPreferences tinglovchini zaif havola bilan saqlaydi, shuning uchun maydonda turadi.
    private val prefsListener = android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
        if (key == "call_history") main.post { if (::channel.isInitialized) channel.invokeMethod("callsChanged", null) }
    }

    companion object {
        const val CHANNEL = "uz.rostor.rostor2/native"
        const val REQ_PICK_APK = 4101
        const val REQ_CALL_ROLE = 4102
        const val REQ_NOTIFICATIONS = 4103
        const val PREFS = DbLoader.PREFS
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
        channel.setMethodCallHandler(::onCall)
        prefs().registerOnSharedPreferenceChangeListener(prefsListener)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (savedInstanceState == null) pendingIncoming = parseIncoming(intent)
    }

    override fun onDestroy() {
        prefs().unregisterOnSharedPreferenceChangeListener(prefsListener)
        super.onDestroy()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        val incoming = parseIncoming(intent) ?: return
        channel.invokeMethod("incoming", incoming)
    }

    private fun prefs() = getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    private fun onCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "takeIncoming" -> { result.success(pendingIncoming); pendingIncoming = null }
            "selfInfo" -> result.success(selfInfo())
            "loadDb" -> background(result) { loadDb() }
            "pickApk" -> pickApk(result)
            "inspectUri" -> {
                val uri = Uri.parse(call.argument<String>("uri"))
                background(result) { ApkInspector(this).inspect(uri) }
            }
            "audit" -> background(result) { DeviceAuditor(this).audit() }
            "changedSinceLast" -> background(result) { changedSinceLast() }
            "markAudited" -> {
                prefs().edit().putInt("changed_seq", call.argument<Int>("sequence") ?: 0).apply()
                result.success(null)
            }
            "appIcon" -> background(result) { appIcon(call.argument<String>("package")!!) }
            "openAppDetails" -> result.success(open(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + call.argument<String>("package")))))
            "openUnknownSources" -> result.success(open(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + call.argument<String>("package")))))
            "openAccessibility" -> result.success(open(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)))
            "openNotificationAccess" -> result.success(open(Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS")))
            "openSecurity" -> result.success(open(Intent(Settings.ACTION_SECURITY_SETTINGS)))
            "openDefaultApps" -> result.success(open(Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS)))
            "openDeveloperOptions" -> result.success(open(Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)))
            "callStatus" -> result.success(callStatus())
            "requestCallRole" -> requestCallRole(result)
            "requestNotifications" -> requestNotifications(result)
            "openNotificationSettings" -> result.success(open(
                Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName)))
            "openCallScreeningRole" -> result.success(open(Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS)))
            "checkPhone" -> {
                val n = call.argument<String>("number") ?: ""
                background(result) { CallShield.check(this, n) }
            }
            "testCallNotification" -> background(result) { CallShield.notifyTest(this) }
            "reportIdentity" -> background(result) { reportIdentity() }
            "createReport" -> background(result) { createReport(call.arguments as Map<*, *>) }
            "listReports" -> background(result) { listReports() }
            "readReport" -> background(result) { readReport(call.argument<String>("name")!!) }
            "shareReport" -> result.success(shareReport(call.argument<String>("name")!!))
            "deleteReport" -> background(result) { deleteReport(call.argument<String>("name")!!) }
            "kvGet" -> result.success(prefs().getString(call.argument<String>("key"), null))
            "kvSet" -> { prefs().edit().putString(call.argument<String>("key"), call.argument<String>("value")).apply(); result.success(null) }
            else -> result.notImplemented()
        }
    }

    private fun background(result: MethodChannel.Result, work: () -> Any?) {
        io.execute {
            try {
                val value = work()
                main.post { result.success(value) }
            } catch (e: Throwable) {
                main.post { result.error("native", e.javaClass.simpleName + ": " + (e.message ?: ""), null) }
            }
        }
    }

    private fun open(intent: Intent): Boolean = try {
        startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        true
    } catch (e: ActivityNotFoundException) {
        try { startActivity(Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); true } catch (e2: Exception) { false }
    }

    // --- Kirib kelgan APK yoki matn -------------------------------------------------------

    private fun parseIncoming(i: Intent?): Map<String, Any?>? {
        if (i == null) return null
        return when (i.action) {
            CallShield.ACTION_OPEN -> mapOf("type" to "calls")
            Intent.ACTION_VIEW -> i.data?.let { mapOf("type" to "apk", "uri" to it.toString()) }
            Intent.ACTION_SEND -> {
                val stream: Uri? = if (Build.VERSION.SDK_INT >= 33) i.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
                else @Suppress("DEPRECATION") i.getParcelableExtra(Intent.EXTRA_STREAM)
                when {
                    stream != null -> mapOf("type" to "apk", "uri" to stream.toString())
                    i.getStringExtra(Intent.EXTRA_TEXT) != null -> mapOf("type" to "text", "text" to i.getStringExtra(Intent.EXTRA_TEXT))
                    else -> null
                }
            }
            Intent.ACTION_PROCESS_TEXT -> i.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT)?.let { mapOf("type" to "text", "text" to it.toString()) }
            else -> null
        }
    }

    private fun pickApk(result: MethodChannel.Result) {
        if (pendingPick != null) { result.error("busy", "Fayl tanlash oynasi allaqachon ochiq", null); return }
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("application/vnd.android.package-archive", "application/octet-stream", "application/zip"))
        }
        pendingPick = result
        try {
            startActivityForResult(intent, REQ_PICK_APK)
        } catch (e: ActivityNotFoundException) {
            pendingPick = null
            result.error("no_picker", "Fayl tanlash oynasi topilmadi", null)
        }
    }

    @Deprecated("FlutterActivity ComponentActivity emas, shuning uchun klassik API")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_CALL_ROLE) {
            pendingRole?.success(callStatus())
            pendingRole = null
            return
        }
        if (requestCode != REQ_PICK_APK) return
        val r = pendingPick ?: return
        pendingPick = null
        val uri = data?.data
        if (resultCode != Activity.RESULT_OK || uri == null) { r.success(null); return }
        background(r) { ApkInspector(this).inspect(uri) }
    }

    // --- Qo'ng'iroq Qalqoni (F2) ---------------------------------------------------------

    private fun roleManager(): android.app.role.RoleManager? =
        if (Build.VERSION.SDK_INT >= 29) getSystemService(android.app.role.RoleManager::class.java) else null

    private fun callStatus(): Map<String, Any?> {
        val rm = roleManager()
        val available = rm?.isRoleAvailable(android.app.role.RoleManager.ROLE_CALL_SCREENING) == true
        return mapOf(
            "supported" to (Build.VERSION.SDK_INT >= 29 && available),
            "sdkInt" to Build.VERSION.SDK_INT,
            "roleHeld" to (available && rm!!.isRoleHeld(android.app.role.RoleManager.ROLE_CALL_SCREENING)),
            "notifications" to CallShield.notificationsEnabled(this),
            "notificationsAskable" to (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED),
        )
    }

    private fun requestCallRole(result: MethodChannel.Result) {
        val rm = roleManager()
        if (rm == null || !rm.isRoleAvailable(android.app.role.RoleManager.ROLE_CALL_SCREENING)) { result.success(callStatus()); return }
        if (rm.isRoleHeld(android.app.role.RoleManager.ROLE_CALL_SCREENING)) { result.success(callStatus()); return }
        if (pendingRole != null) { result.error("busy", "Ruxsat oynasi allaqachon ochiq", null); return }
        pendingRole = result
        try {
            @Suppress("DEPRECATION")
            startActivityForResult(rm.createRequestRoleIntent(android.app.role.RoleManager.ROLE_CALL_SCREENING), REQ_CALL_ROLE)
        } catch (e: ActivityNotFoundException) {
            pendingRole = null
            result.success(callStatus())
        }
    }

    private fun requestNotifications(result: MethodChannel.Result) {
        CallShield.ensureChannel(this)
        if (Build.VERSION.SDK_INT < 33 ||
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) == android.content.pm.PackageManager.PERMISSION_GRANTED) {
            result.success(callStatus()); return
        }
        if (pendingNotif != null) { result.error("busy", "Ruxsat oynasi allaqachon ochiq", null); return }
        pendingNotif = result
        requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), REQ_NOTIFICATIONS)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQ_NOTIFICATIONS) {
            pendingNotif?.success(callStatus())
            pendingNotif = null
        }
    }

    // --- Firibgarlik hisoboti (F3) -------------------------------------------------------

    private fun reportsDir() = java.io.File(filesDir, "reports").apply { mkdirs() }
    private val reportName = Regex("R2-[0-9A-F]{12}")

    private fun reportIdentity(): Map<String, Any?> {
        val keys = ReporterKeys(this)
        if (!keys.exists()) return mapOf("exists" to false)
        val (ed, ml) = keys.seeds()
        val (edPk, mlPk) = uz.rostor.rostor2.crypto.Hybrid.publicKeys(ed, ml)
        return mapOf("exists" to true, "deviceId" to ReportCodec.deviceId(edPk, mlPk))
    }

    private fun createReport(a: Map<*, *>): Map<String, Any?> {
        @Suppress("UNCHECKED_CAST")
        val evidence = (a["evidence"] as? List<Map<String, Any?>>).orEmpty()
            .map { (it["kind"] as String) to ((it["value"] as? String) ?: "") }
        val inp = ReportCodec.Input(
            category = a["category"] as String,
            targetType = a["targetType"] as String,
            targetValue = a["targetValue"] as String,
            claimedOrg = a["claimedOrg"] as String?,
            incidentAt = (a["incidentAt"] as Number?)?.toLong(),
            amountUzs = (a["amountUzs"] as Number?)?.toLong(),
            description = (a["description"] as String?) ?: "",
            evidence = evidence,
            findings = (a["findings"] as? List<*>).orEmpty().mapNotNull { f ->
                (f as? Map<*, *>)?.let { (it["code"] as? String ?: "") to (it["title"] as? String ?: "") }
            },
            reporterContact = a["reporterContact"] as String?,
        )
        val id = ByteArray(16).also { java.security.SecureRandom().nextBytes(it) }.joinToString("") { "%02x".format(it) }
        val (ed, ml) = ReporterKeys(this).seeds()
        val pi = packageManager.getPackageInfo(packageName, 0)
        val file = try {
            ReportCodec.create(inp, ed, ml, id, System.currentTimeMillis() / 1000, pi.versionName ?: "",
                prefs().getLong("db_max_version", 0))
        } catch (e: ReportCodec.InvalidInput) {
            return mapOf("error" to e.message)
        }
        val name = "R2-" + id.substring(0, 12).uppercase()
        java.io.File(reportsDir(), "$name.json").writeText(file.toString(1) + "\n")
        java.io.File(reportsDir(), "$name.txt").writeText(file.getString("readable") + "\n")
        return mapOf("name" to name, "readable" to file.getString("readable"), "deviceId" to file.getString("device_id"))
    }

    private fun listReports(): List<Map<String, Any?>> =
        reportsDir().listFiles { f -> f.name.endsWith(".json") }.orEmpty().mapNotNull { f ->
            val v = ReportCodec.verify(f.readText())
            val c = v.content ?: return@mapNotNull mapOf("name" to f.nameWithoutExtension, "ok" to false, "error" to v.error)
            mapOf(
                "name" to f.nameWithoutExtension, "ok" to true, "createdAt" to c.getLong("created_at"),
                "category" to c.getString("category"), "targetType" to c.getString("target_type"),
                "targetValue" to c.getString("target_value"),
            )
        }.sortedByDescending { (it["createdAt"] as? Long) ?: 0L }

    private fun readReport(name: String): Map<String, Any?> {
        require(reportName.matches(name))
        val f = java.io.File(reportsDir(), "$name.json")
        val v = ReportCodec.verify(f.readText())
        return mapOf("ok" to v.ok, "error" to v.error, "readable" to v.content?.let { ReportCodec.readable(it) })
    }

    private fun deleteReport(name: String): Boolean {
        require(reportName.matches(name))
        return java.io.File(reportsDir(), "$name.json").delete() and java.io.File(reportsDir(), "$name.txt").delete()
    }

    /** Foydalanuvchi o'zi tanlagan ilovaga (Telegram, pochta) yuboradi — ROSTOR-2 hech narsa jo'natmaydi. */
    private fun shareReport(name: String): Boolean {
        require(reportName.matches(name))
        val txt = java.io.File(reportsDir(), "$name.txt")
        val uris = arrayListOf(ReportFileProvider.uriFor("$name.txt"), ReportFileProvider.uriFor("$name.json"))
        val send = Intent(Intent.ACTION_SEND_MULTIPLE).apply {
            type = "*/*"
            putParcelableArrayListExtra(Intent.EXTRA_STREAM, uris)
            putExtra(Intent.EXTRA_SUBJECT, "Firibgarlik haqida hisobot $name")
            putExtra(Intent.EXTRA_TEXT, txt.readText())
            clipData = android.content.ClipData.newRawUri(name, uris[0]).apply { addItem(android.content.ClipData.Item(uris[1])) }
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        // open() emas: u xato bo'lsa Sozlamalarni ochadi, bu yerda esa shunchaki false qaytishi kerak.
        return try { startActivity(Intent.createChooser(send, "Hisobotni yuborish")); true } catch (e: ActivityNotFoundException) { false }
    }

    // --- Baza, o'z-o'zini isbotlash, o'zgarishlar -----------------------------------------

    private fun loadDb(): Map<String, Any?> {
        val r = DbLoader.load(this)
        return mapOf(
            "ok" to r.ok, "error" to r.error, "version" to r.dbVersion, "issuedAt" to r.issuedAt,
            "keyId" to r.keyId, "payload" to r.payloadJson,
        )
    }

    private fun selfInfo(): Map<String, Any?> {
        val pi = packageManager.getPackageInfo(packageName, Certs.signatureFlag() or android.content.pm.PackageManager.GET_PERMISSIONS)
        val perms = pi.requestedPermissions?.toList() ?: emptyList()
        return mapOf(
            "packageName" to packageName,
            "versionName" to pi.versionName,
            "versionCode" to if (Build.VERSION.SDK_INT >= 28) pi.longVersionCode else @Suppress("DEPRECATION") pi.versionCode.toLong(),
            "certSha256" to Certs.ofInstalled(pi).first.map { Certs.sha256Hex(it) },
            "permissions" to perms,
            "hasInternet" to ("android.permission.INTERNET" in perms),
            "installer" to Installers.of(packageManager, packageName),
            "dbKeyId" to DbBundle.keyId(DbKeys.ED25519_PK, DbKeys.MLDSA65_PK),
            "debuggable" to ((applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0),
            // F4: yig'ishda berilgan rasmiy imzo xeshi (bo'sh bo'lishi mumkin).
            "expectedCert" to BuildConfig.EXPECTED_SIGNATURE_SHA256.lowercase(),
        )
    }

    private fun changedSinceLast(): Map<String, Any?> {
        val seq = prefs().getInt("changed_seq", -1)
        if (seq < 0) {
            // Birinchi ishga tushish: joriy ketma-ketlik raqamini olamiz, o'zgarishlar ro'yxati bo'sh.
            val current = packageManager.getChangedPackages(0)?.sequenceNumber ?: 0
            return mapOf("first" to true, "sequence" to current, "packages" to emptyList<String>())
        }
        return DeviceAuditor(this).changedSince(seq) + ("first" to false)
    }

    private fun appIcon(pkg: String): ByteArray? = try {
        val d = packageManager.getApplicationIcon(pkg)
        val bmp = android.graphics.Bitmap.createBitmap(96, 96, android.graphics.Bitmap.Config.ARGB_8888)
        val c = android.graphics.Canvas(bmp)
        d.setBounds(0, 0, 96, 96)
        d.draw(c)
        java.io.ByteArrayOutputStream().use { bmp.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, it); it.toByteArray() }
    } catch (e: Exception) {
        null
    }
}
