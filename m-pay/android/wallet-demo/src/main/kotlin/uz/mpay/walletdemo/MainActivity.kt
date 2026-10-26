package uz.mpay.walletdemo

import android.content.ComponentName
import android.content.Intent
import android.nfc.NfcAdapter
import android.nfc.cardemulation.CardEmulation
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import uz.mpay.core.Hex
import uz.mpay.core.ProvisionResult
import uz.mpay.core.ServerPinPolicy
import uz.mpay.core.maskPan
import uz.mpay.wallet.sdk.BiometricGate
import uz.mpay.wallet.sdk.IntegrityTokenProvider
import uz.mpay.wallet.sdk.MpayHceService
import uz.mpay.wallet.sdk.MpayWallet
import uz.mpay.wallet.sdk.WalletConfig
import java.io.File

/** Wallet SDK namoyish ilovasi (sandbox). */
class MainActivity : FragmentActivity() {
    private lateinit var wallet: MpayWallet

    private var server by mutableStateOf(BuildConfig.DEFAULT_SERVER)
    private var pan by mutableStateOf("")
    private var expiry by mutableStateOf("3112")
    private var status by mutableStateOf("Serverga ulaning")
    private var busy by mutableStateOf(false)
    private var pending by mutableStateOf<ProvisionResult.PendingIdv?>(null)
    private var otp by mutableStateOf("")
    private var operatorKey by mutableStateOf("")
    /** Sandbox Play Integrity stsenariysi (server mock'i; real ilovada — Play Integrity API). */
    private var integrityPreset by mutableStateOf("strong")
    private var refresh by mutableIntStateOf(0)
    private val events = mutableStateOf(listOf<String>())

    private val listener: (String) -> Unit = { e ->
        runOnUiThread {
            events.value = (listOf(e) + events.value).take(6)
            refresh++
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        wallet = MpayWallet.get(this)
        // Server ishonchi build vaqtida (P1.5); pin berilmagan sandbox build'ida — TOFU.
        val pins = ServerPinPolicy.parseList(BuildConfig.SERVER_FINGERPRINTS)
        wallet.config = WalletConfig(
            pinnedFingerprints = pins,
            tlsCertSha256 = BuildConfig.TLS_PIN.takeIf { it.isNotEmpty() }?.let(Hex::decode),
            allowTofu = pins.isEmpty(),
            rootFingerprint = BuildConfig.ROOT_FINGERPRINT.takeIf { it.isNotEmpty() },
        )
        wallet.addListener(listener)
        // P2.6: sandbox'da yaxlitlik tokeni server mock'idan (operator kaliti bilan).
        wallet.integrityProvider = IntegrityTokenProvider { hash ->
            operatorKey.trim().takeIf { it.isNotEmpty() }?.let { wallet.sandboxIntegrityToken(hash, it, integrityPreset) }
        }
        setContent { App() }
    }

    override fun onDestroy() {
        wallet.removeListener(listener)
        super.onDestroy()
    }

    /** Tarmoq/Keystore ishi fon oqimida, holat — Main'da. */
    private fun work(label: String, block: suspend () -> String) {
        busy = true
        status = "$label…"
        lifecycleScope.launch(Dispatchers.IO) {
            val msg = runCatching { block() }.getOrElse { "Xato: ${it.message}" }
            withContext(Dispatchers.Main) {
                status = msg
                busy = false
                refresh++
            }
        }
    }

    private fun connect() = work("Ulanmoqda") { "Ulandi. Server: ${wallet.connect(server).take(16)}…" }

    private fun provision() = work("Tokenlashtirilmoqda") {
        val r = wallet.provision(pan.trim(), expiry.trim())
        // FPAN ekranda qolmasin: server javob bergach maydon tozalanadi.
        withContext(Dispatchers.Main) { if (r !is ProvisionResult.Declined) pan = "" }
        when (r) {
            is ProvisionResult.Active -> "Token faol (${r.idv.decision}): ${maskPan(r.profile.dpan)}"
            is ProvisionResult.PendingIdv -> {
                withContext(Dispatchers.Main) { pending = r }
                val sms = r.otpSentTo?.let { "kod SMS bilan $it raqamiga yuborildi" } ?: "OTP kiriting"
                "Qo'shimcha tasdiq kerak (${r.idv.decision}): $sms"
            }
            is ProvisionResult.Declined -> "Rad etildi: ${r.idv.decision} ${r.idv.reasons}"
        }
    }

    private fun verify() {
        val p = pending ?: return
        work("OTP tekshirilmoqda") {
            val prof = wallet.verifyOtp(p.tokenId, p.challengeId, otp.trim())
            withContext(Dispatchers.Main) { pending = null; otp = "" }
            "Token faol: ${maskPan(prof.dpan)}"
        }
    }

    private fun resendOtp() {
        val p = pending ?: return
        work("SMS qayta yuborilmoqda") { "Kod qayta yuborildi: ${wallet.resendOtp(p.tokenId, p.challengeId)}" }
    }

    private fun fetchOtp() {
        val p = pending ?: return
        work("Sandbox OTP") {
            val v = wallet.sandboxOtp(p.challengeId, operatorKey.trim())
            withContext(Dispatchers.Main) { otp = v }
            "OTP olindi (sandbox)"
        }
    }

    private fun prepareToPay() {
        BiometricGate.authenticate(this, wallet.cdcvm) { ok, err ->
            status = if (ok) "To'lovga tayyor: telefonni terminalga yaqinlashtiring" else "Biometriya: ${err ?: "bekor qilindi"}"
            refresh++
        }
    }

    /**
     * Faqat debug: emulyatorda NFC yo'q — terminal ilovasi APDU'larni loopback ko'prik orqali yuboradi
     * (`src/debug/.../VirtualNfcService`; release'da sinf yo'q, tugma ko'rinmaydi).
     */
    private fun startVirtualNfc() {
        val i = Intent().setClassName(packageName, "uz.mpay.walletdemo.VirtualNfcService")
        runCatching { startForegroundService(i) }
            .onSuccess { status = "Virtual NFC yoqildi: 127.0.0.1:47661 (faqat emulyator sinovi)" }
            .onFailure { status = "Virtual NFC: ${it.message}" }
    }

    private fun makeDefault() {
        val i = Intent(CardEmulation.ACTION_CHANGE_DEFAULT)
            .putExtra(CardEmulation.EXTRA_CATEGORY, CardEmulation.CATEGORY_PAYMENT)
            .putExtra(CardEmulation.EXTRA_SERVICE_COMPONENT, ComponentName(this, MpayHceService::class.java))
        runCatching { startActivity(i) }.onFailure { status = "NFC to'lov sozlamasi mavjud emas" }
    }

    private fun exportChain() = work("Attestatsiya zanjiri") {
        val f = File(getExternalFilesDir(null), "attestation-chain.pem")
        f.writeText(wallet.deviceKey().chainPem())
        "Saqlandi: ${f.absolutePath} (StrongBox: ${wallet.deviceKey().strongBox})"
    }

    @Composable
    private fun App() {
        val scheme = darkColorScheme(primary = Color(0xFF7CE0B5), surface = Color(0xFF14201B), background = Color(0xFF0B1410))
        MaterialTheme(colorScheme = scheme) {
            var seconds by remember { mutableIntStateOf(0) }
            LaunchedEffect(Unit) {
                while (true) { seconds = wallet.cdcvm.secondsLeft(); delay(500) }
            }
            Column(
                Modifier.fillMaxSize().background(scheme.background).windowInsetsPadding(WindowInsets.safeDrawing).padding(16.dp).verticalScroll(rememberScrollState())
                    .semantics { testTagsAsResourceId = true },
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text("M-Pay Hamyon", color = scheme.primary, fontSize = 24.sp, fontWeight = FontWeight.Bold)
                Text("Sandbox · PQ Link (X25519+ML-KEM-768)", color = Color.Gray, fontSize = 12.sp)
                val pinCount = wallet.config.pinnedFingerprints.size
                if (pinCount > 0) {
                    Text("Server pinlangan: $pinCount ta barmoq izi (build)", color = Color(0xFF7CE0B5), fontSize = 12.sp, modifier = Modifier.testTag("pin_mode"))
                } else {
                    Text("Server pinlanmagan — TOFU (faqat sandbox)", color = Color(0xFFFFB74D), fontSize = 12.sp, modifier = Modifier.testTag("pin_mode"))
                }
                val nfc = NfcAdapter.getDefaultAdapter(this@MainActivity)
                if (nfc == null) Text("Bu qurilmada NFC yo'q — tap ishlamaydi (provisioning ishlaydi)", color = Color(0xFFFFB74D), fontSize = 12.sp)

                OutlinedTextField(server, { server = it }, label = { Text("Server") }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("server"))
                Button({ connect() }, enabled = !busy, modifier = Modifier.fillMaxWidth().testTag("connect")) { Text("Ulanish") }

                CardView(seconds)

                OutlinedTextField(pan, { pan = it.filter(Char::isDigit) }, label = { Text("Karta raqami (test FPAN)") }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("pan"))
                OutlinedTextField(expiry, { expiry = it.filter(Char::isDigit).take(4) }, label = { Text("Amal qilish (YYMM)") }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("expiry"))
                OutlinedTextField(operatorKey, { operatorKey = it.trim() }, label = { Text("Operator kaliti (sandbox: OTP va yaxlitlik mock'i)") }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("operator"))
                Text("Ilova yaxlitligi (sandbox mock):", color = Color.Gray, fontSize = 12.sp)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    listOf("strong", "basic", "no_integrity", "remote_control").forEach { p ->
                        if (p == integrityPreset) {
                            Button({ integrityPreset = p }, modifier = Modifier.testTag("pi_$p")) { Text(p, fontSize = 12.sp) }
                        } else {
                            OutlinedButton({ integrityPreset = p }, modifier = Modifier.testTag("pi_$p")) { Text(p, fontSize = 12.sp) }
                        }
                    }
                }
                Button({ provision() }, enabled = !busy && pan.length == 16, modifier = Modifier.fillMaxWidth().testTag("provision")) { Text("Kartani qo'shish") }

                pending?.let { p ->
                    OutlinedTextField(otp, { otp = it.filter(Char::isDigit).take(6) }, label = { Text("OTP") }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("otp"))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        if (p.otpSentTo == null) {
                            OutlinedButton({ fetchOtp() }, enabled = !busy && operatorKey.isNotEmpty(), modifier = Modifier.testTag("fetch_otp")) { Text("OTP olish") }
                        }
                        OutlinedButton({ resendOtp() }, enabled = !busy, modifier = Modifier.testTag("resend_otp")) { Text("Qayta yuborish") }
                        Button({ verify() }, enabled = !busy && otp.length == 6, modifier = Modifier.testTag("verify")) { Text("Tasdiqlash") }
                    }
                }

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button({ prepareToPay() }, enabled = wallet.profile() != null && BiometricGate.available(this@MainActivity), modifier = Modifier.testTag("pay")) { Text("To'lovga tayyorlash") }
                    OutlinedButton({ work("LUK") { "Yangi LUK: ${wallet.replenish()}" } }, enabled = !busy && wallet.profile() != null, modifier = Modifier.testTag("replenish")) { Text("LUK to'ldirish") }
                }
                // Tugmalar sig'masa keyingi qatorga o'tadi (tor ekranda matn harflab uzilmasin).
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton({ makeDefault() }, modifier = Modifier.testTag("default")) { Text("Standart to'lov ilovasi") }
                    if (BuildConfig.DEBUG) {
                        OutlinedButton({ startVirtualNfc() }, modifier = Modifier.testTag("virtual_nfc")) { Text("Virtual NFC") }
                    }
                    OutlinedButton({ exportChain() }, modifier = Modifier.testTag("export")) { Text("Attestatsiya") }
                }
                Text(status, color = Color.White, modifier = Modifier.testTag("status"))
                events.value.forEach { Text("• $it", color = Color.Gray, fontSize = 12.sp) }
                Spacer(Modifier.height(24.dp))
            }
        }
    }

    @Composable
    private fun CardView(seconds: Int) {
        @Suppress("UNUSED_EXPRESSION") refresh
        val p = wallet.profile()
        Card(
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF11624A)),
            modifier = Modifier.fillMaxWidth().heightIn(min = 150.dp).testTag("card"),
        ) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("M-PAY TEST", color = Color(0xFFB9F0D6), fontWeight = FontWeight.Bold)
                if (p == null) {
                    Text("Karta qo'shilmagan", color = Color.White)
                } else {
                    val now = System.currentTimeMillis() / 1000
                    Text(maskPan(p.dpan), color = Color.White, fontSize = 20.sp, fontWeight = FontWeight.Medium)
                    Text("Muddat ${p.expiryYymm.take(2)}/${p.expiryYymm.drop(2)}  ·  ATC ${p.atc}", color = Color(0xFFDDEFE6), fontSize = 12.sp)
                    Text("LUK: ${p.luks.count { it.usesLeft > 0 && it.expiresAt > now }} yaroqli", color = Color(0xFFDDEFE6), fontSize = 12.sp)
                    Text(if (seconds > 0) "To'lovga tayyor: $seconds s" else "Biometriya kutilmoqda", color = if (seconds > 0) Color(0xFF7CE0B5) else Color(0xFFDDEFE6), fontSize = 12.sp)
                }
            }
        }
    }
}
