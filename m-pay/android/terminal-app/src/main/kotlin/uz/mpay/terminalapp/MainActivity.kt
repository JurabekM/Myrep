package uz.mpay.terminalapp

import android.content.Context
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.IsoDep
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import uz.mpay.core.AuthResult
import uz.mpay.core.MpayClient
import uz.mpay.core.TerminalData
import uz.mpay.core.TerminalException
import uz.mpay.core.TerminalKernel
import uz.mpay.core.ApduTransceiver
import uz.mpay.core.TapResult
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.File
import java.net.InetAddress
import java.net.Socket
import java.time.LocalDate

/**
 * M-Pay test terminali: NFC reader mode → `TerminalKernel.tap` (PPSE/AID/GPO) →
 * `POST /v1/authorizations` → server qarori ekranda. PAN emas, faqat maskalangan DPAN ko'rsatiladi.
 */
class MainActivity : ComponentActivity(), NfcAdapter.ReaderCallback {
    private sealed class Screen {
        data object Idle : Screen()
        data object Waiting : Screen()
        data object Processing : Screen()
        data class SeePhone(val masked: String?) : Screen()
        data class Result(val r: AuthResult) : Screen()
        data class Error(val msg: String) : Screen()
        data class Info(val title: String, val lines: List<String>) : Screen()
    }

    private val prefs by lazy { getSharedPreferences("terminal", Context.MODE_PRIVATE) }
    private var nfc: NfcAdapter? = null

    private var server by mutableStateOf("")
    private var terminalKey by mutableStateOf("")
    private var terminalId by mutableStateOf("TERMAND1")
    private var merchantId by mutableStateOf("SHOP0000000001")
    private var amount by mutableStateOf("25000")
    private var screen by mutableStateOf<Screen>(Screen.Idle)

    @Volatile private var armedAmountMinor: Long = 0

    private val vault by lazy { TerminalVault(this) }

    /** Import qilingan TLS + mTLS sozlamasi; `null` — qo'lda kiritilgan HTTP (faqat sandbox). */
    private var profile by mutableStateOf<TerminalVault.Profile?>(null)

    private val openBundle = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            importBundle { contentResolver.openInputStream(uri)!!.use { it.readBytes().toString(Charsets.UTF_8) } }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        nfc = NfcAdapter.getDefaultAdapter(this)
        server = prefs.getString("server", BuildConfig.DEFAULT_SERVER)!!
        // 0-fazadagi ochiq saqlangan kalit o'chiriladi: endi faqat Keystore bilan shifrlangan paket.
        prefs.edit().remove("terminal_key").apply()
        profile = runCatching { vault.load() }.getOrNull()
        terminalId = prefs.getString("terminal_id", terminalId)!!
        merchantId = prefs.getString("merchant_id", merchantId)!!
        setContent { App() }
    }

    override fun onPause() {
        disarm()
        super.onPause()
    }

    /** STAN: har avtorizatsiyada oshadi, qayta ishga tushganda ham saqlanadi (1..999999). */
    private fun nextStan(): Int = synchronized(this) {
        val s = prefs.getInt("stan", 0) % 999_999 + 1
        prefs.edit().putInt("stan", s).apply()
        s
    }

    private fun arm() {
        val som = amount.toLongOrNull()
        if (som == null || som <= 0) { screen = Screen.Error("Summa noto'g'ri"); return }
        if (key().isBlank()) { screen = Screen.Error("Terminal paketini import qiling yoki kalitni kiriting"); return }
        saveSettings()
        val adapter = nfc
        if (adapter == null || !adapter.isEnabled) { screen = Screen.Error("NFC yo'q yoki o'chirilgan"); return }
        armedAmountMinor = som * 100
        screen = Screen.Waiting
        adapter.enableReaderMode(
            this, this,
            NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK or NfcAdapter.FLAG_READER_NO_PLATFORM_SOUNDS,
            Bundle().apply { putInt(NfcAdapter.EXTRA_READER_PRESENCE_CHECK_DELAY, 250) },
        )
    }

    private fun saveSettings() {
        prefs.edit().putString("server", server.trim())
            .putString("terminal_id", terminalId.trim()).putString("merchant_id", merchantId.trim()).apply()
    }

    private fun client(): MpayClient = profile?.let { MpayClient(it.serverUrl, tls = it.tls) } ?: MpayClient(server.trim())

    private fun key(): String = profile?.terminalKey ?: terminalKey.trim()

    /**
     * Paket: avval ilova papkasidagi `terminal-bundle.json` (adb push), bo'lmasa fayl tanlash oynasi.
     * Import qilingach fayl o'chiriladi (ichida sirlar bor).
     */
    private fun importClicked() {
        val f = File(getExternalFilesDir(null), "terminal-bundle.json")
        if (f.exists()) {
            importBundle { f.readText().also { f.delete() } }
        } else {
            openBundle.launch(arrayOf("application/json", "*/*"))
        }
    }

    private fun importBundle(read: () -> String) {
        screen = Screen.Processing
        lifecycleScope.launch(Dispatchers.IO) {
            val next = runCatching { vault.import(read()) }.fold(
                onSuccess = { p ->
                    withContext(Dispatchers.Main) { profile = p }
                    Screen.Info("Paket import qilindi", listOf("Server: ${p.serverUrl}", "mTLS kaliti: ${p.keyId} (Android Keystore)", "Endi \"Ulanishni tekshirish\" ni bosing"))
                },
                onFailure = { Screen.Error("Paket: ${it.message}") },
            )
            withContext(Dispatchers.Main) { screen = next }
        }
    }

    /** `GET /v1/terminal/ping`: kalit, TLS pin va mTLS'ni tekshiradi. */
    private fun ping() {
        saveSettings()
        screen = Screen.Processing
        lifecycleScope.launch(Dispatchers.IO) {
            val next = runCatching { client().terminalPing(key()) }.fold(
                onSuccess = { (id, mtls) ->
                    Screen.Info("Ulanish ishlaydi", listOfNotNull(
                        "Kalit: $id",
                        if (mtls) "TLS: server pinlangan, mTLS sertifikati qabul qilindi" else "Oddiy HTTP (faqat sandbox)",
                    ))
                },
                onFailure = { Screen.Error("Ulanish: ${it.javaClass.simpleName}: ${it.message}") },
            )
            withContext(Dispatchers.Main) { screen = next }
        }
    }

    private fun forget() {
        vault.clear()
        profile = null
        screen = Screen.Info("Paket o'chirildi", listOf("Kalitlar Keystore'dan o'chirildi"))
    }

    private fun disarm() {
        runCatching { nfc?.disableReaderMode(this) }
    }

    /** NFC oqimida chaqiriladi (UI emas) — tarmoq so'rovi shu yerda bajarilishi mumkin. */
    override fun onTagDiscovered(tag: Tag) {
        val dep = IsoDep.get(tag) ?: return
        val amountMinor = armedAmountMinor
        if (amountMinor <= 0) return
        completeTap(amountMinor) {
            dep.use {
                it.connect()
                it.timeout = 3000
                kernelTap({ c -> it.transceive(c) }, amountMinor)
            }
        }
    }

    private fun kernelTap(t: ApduTransceiver, amountMinor: Long): TapResult {
        val d = LocalDate.now()
        return TerminalKernel.tap(t, amountMinor, TerminalData.dateBcd(d.year, d.monthValue, d.dayOfMonth))
    }

    /**
     * Faqat debug (emulyator): NFC o'rniga hamyon ilovasining virtual NFC ko'prigi (`127.0.0.1:47661`,
     * kadr `u16 uzunlik ‖ APDU`). Terminal yadrosi, avtorizatsiya va natija ekrani — haqiqiy tap bilan bir xil.
     */
    private fun virtualTap() {
        val som = amount.toLongOrNull()
        if (som == null || som <= 0) { screen = Screen.Error("Summa noto'g'ri"); return }
        if (key().isBlank()) { screen = Screen.Error("Terminal paketini import qiling yoki kalitni kiriting"); return }
        saveSettings()
        val amountMinor = som * 100
        Thread {
            completeTap(amountMinor) {
                Socket(InetAddress.getLoopbackAddress(), 47661).use { s ->
                    s.soTimeout = 5000
                    val input = DataInputStream(s.getInputStream())
                    val output = DataOutputStream(s.getOutputStream())
                    kernelTap({ c ->
                        output.writeShort(c.size)
                        output.write(c)
                        output.flush()
                        ByteArray(input.readUnsignedShort()).also(input::readFully)
                    }, amountMinor)
                }
            }
        }.start()
    }

    /** Tap → avtorizatsiya → natija (NFC va virtual yo'l uchun umumiy; UI oqimidan tashqarida). */
    private fun completeTap(amountMinor: Long, tapFn: () -> TapResult) {
        runOnUiThread { screen = Screen.Processing }
        val next: Screen = try {
            val tap = tapFn()
            Log.i(TAG, "tap: dpan=${tap.dpanMasked} atc=${tap.atc} summa=$amountMinor")
            val r = client().authorize(key(), terminalId.trim(), merchantId.trim(), nextStan(), tap.iccHex())
            Log.i(TAG, "auth: rc=${r.responseCode} rrn=${r.rrn} dpan=${r.dpanMasked}")
            armedAmountMinor = 0
            Screen.Result(r)
        } catch (e: TerminalException) {
            if (e.seePhone) Screen.SeePhone(null) else Screen.Error("Karta: ${e.message}")
        } catch (e: Exception) {
            Screen.Error("${e.javaClass.simpleName}: ${e.message}")
        }
        runOnUiThread {
            screen = next
            // To'lov yakunlangach o'quvchi o'chadi; "telefonda tasdiqlang" holatida kutishda qoladi.
            if (next !is Screen.SeePhone) disarm()
        }
    }

    @Composable
    private fun App() {
        val scheme = darkColorScheme(primary = Color(0xFF8AB4F8), surface = Color(0xFF161B26), background = Color(0xFF0D1117))
        MaterialTheme(colorScheme = scheme) {
            Column(
                Modifier.fillMaxSize().background(scheme.background).windowInsetsPadding(WindowInsets.safeDrawing).padding(16.dp).verticalScroll(rememberScrollState())
                    .semantics { testTagsAsResourceId = true },
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text("M-Pay Terminal", color = scheme.primary, fontSize = 24.sp, fontWeight = FontWeight.Bold)
                Text("Sandbox · M-Pay Test Scheme (fiktiv)", color = Color.Gray, fontSize = 12.sp)
                if (nfc == null) Text("Bu qurilmada NFC yo'q — tap qabul qilinmaydi", color = Color(0xFFFFB74D), fontSize = 12.sp)

                OutlinedTextField(amount, { amount = it.filter(Char::isDigit).take(9) }, label = { Text("Summa (so'm)") }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("amount"))
                if (BuildConfig.DEBUG) {
                    OutlinedButton({ virtualTap() }, enabled = screen !is Screen.Processing, modifier = Modifier.fillMaxWidth().testTag("virtual_tap")) {
                        Text("Virtual tap (emulyator, faqat debug)")
                    }
                }
                Button({ arm() }, enabled = screen !is Screen.Waiting && screen !is Screen.Processing, modifier = Modifier.fillMaxWidth().testTag("charge")) {
                    Text("To'lov qabul qilish")
                }
                if (screen is Screen.Waiting || screen is Screen.SeePhone) {
                    OutlinedButton({ disarm(); armedAmountMinor = 0; screen = Screen.Idle }, modifier = Modifier.fillMaxWidth().testTag("cancel")) { Text("Bekor qilish") }
                }

                StatusCard(screen)

                Spacer(Modifier.height(12.dp))
                Text("Sozlamalar", color = Color.Gray, fontSize = 14.sp)
                val p = profile
                if (p != null) {
                    Text("TLS + mTLS: ${p.serverUrl}", color = Color(0xFF7CE0B5), fontSize = 13.sp, modifier = Modifier.testTag("tls_profile"))
                    Text("Kalit ${p.keyId} · mijoz kaliti Android Keystore'da", color = Color.Gray, fontSize = 12.sp)
                } else {
                    Text("Qo'lda (oddiy HTTP, faqat sandbox). Ishlab chiqarishda — terminal paketi.", color = Color(0xFFFFB74D), fontSize = 12.sp)
                    OutlinedTextField(server, { server = it }, label = { Text("Server") }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("server"))
                    OutlinedTextField(terminalKey, { terminalKey = it }, label = { Text("Terminal kaliti (saqlanmaydi)") }, singleLine = true, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth().testTag("terminal_key"))
                }
                Button({ ping() }, enabled = screen !is Screen.Processing, modifier = Modifier.fillMaxWidth().testTag("ping")) { Text("Ulanishni tekshirish") }
                if (p == null) {
                    OutlinedButton({ importClicked() }, modifier = Modifier.fillMaxWidth().testTag("import")) { Text("Terminal paketini import qilish") }
                } else {
                    OutlinedButton({ forget() }, modifier = Modifier.fillMaxWidth().testTag("forget")) { Text("Paketni o'chirish") }
                }
                OutlinedTextField(terminalId, { terminalId = it.take(8) }, label = { Text("Terminal ID (8)") }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("terminal_id"))
                OutlinedTextField(merchantId, { merchantId = it.take(15) }, label = { Text("Merchant ID (≤15)") }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("merchant_id"))
            }
        }
    }

    @Composable
    private fun StatusCard(s: Screen) {
        val (bg, title, lines) = when (s) {
            Screen.Idle -> Triple(Color(0xFF1F2633), "Tayyor", listOf("Summani kiriting va \"To'lov qabul qilish\" ni bosing"))
            Screen.Waiting -> Triple(Color(0xFF1C3A5E), "Telefonni yaqinlashtiring", listOf("${amount} so'm"))
            Screen.Processing -> Triple(Color(0xFF1C3A5E), "Ishlanmoqda…", listOf("Server qarori kutilmoqda"))
            is Screen.SeePhone -> Triple(Color(0xFF5E4A1C), "Telefonda tasdiqlang", listOf("Summa CDCVM chegarasidan yuqori:", "biometriyadan so'ng qayta tekkizing"))
            is Screen.Result -> {
                val r = s.r
                Triple(
                    if (r.approved) Color(0xFF1B5E3A) else Color(0xFF6B1F24),
                    if (r.approved) "MA'QULLANDI" else "RAD ETILDI",
                    listOfNotNull(
                        "Kod ${r.responseCode} · ${r.reason}",
                        "${r.amountMinor / 100} so'm · ${r.dpanMasked}",
                        "RRN ${r.rrn}",
                        r.riskScore?.let { "Shield xavf bali: $it" },
                    ),
                )
            }
            is Screen.Error -> Triple(Color(0xFF6B1F24), "Xato", listOf(s.msg))
            is Screen.Info -> Triple(Color(0xFF1C3A5E), s.title, s.lines)
        }
        Card(
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = bg),
            modifier = Modifier.fillMaxWidth().testTag("result"),
        ) {
            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(title, color = Color.White, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                lines.forEach { Text(it, color = Color(0xFFE0E6F0), fontSize = 14.sp) }
            }
        }
    }

    private companion object {
        const val TAG = "MpayTerminal"
    }
}
