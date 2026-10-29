package uz.mpay.wallet.app

import android.Manifest
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.nfc.cardemulation.CardEmulation
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.view.WindowManager
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricPrompt
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import uz.mpay.core.ServerPinPolicy
import uz.mpay.wallet.app.ui.AddCardScreen
import uz.mpay.wallet.app.ui.CardScreen
import uz.mpay.wallet.app.ui.HistoryScreen
import uz.mpay.wallet.app.ui.HomeScreen
import uz.mpay.wallet.app.ui.MpayColors
import uz.mpay.wallet.app.ui.MpayIcons
import uz.mpay.wallet.app.ui.MpayTheme
import uz.mpay.wallet.app.ui.Onboarding
import uz.mpay.wallet.app.ui.OtpScreen
import uz.mpay.wallet.app.ui.PayScreen
import uz.mpay.wallet.app.ui.PinEntry
import uz.mpay.wallet.app.ui.SettingsModel
import uz.mpay.wallet.app.ui.SettingsScreen
import uz.mpay.wallet.sdk.BiometricGate
import uz.mpay.wallet.sdk.MpayHceService

/**
 * Yagona Activity: onboarding → qulf (PIN / biometriya) → ekranlar stegi ([WalletViewModel]).
 * `FLAG_SECURE` — skrinshot va "so'nggi ilovalar" ko'rinishida kartalar ko'rinmaydi.
 */
class MainActivity : FragmentActivity() {
    private val vm: WalletViewModel by viewModels()
    private lateinit var prefs: AppPrefs

    private var onboarded by mutableStateOf(false)
    private var locked by mutableStateOf(true)
    private var pinError by mutableStateOf<String?>(null)
    private var stoppedAt = 0L
    /** To'lov ekranida tanlangan karta va tap bo'lgan token. */
    private var payCard by mutableStateOf<String?>(null)
    private var tapped by mutableStateOf<String?>(null)

    private val listener: (String) -> Unit = { e ->
        // SDK hodisasi: "Tap: 990077******1111, ATC=…" (faqat maskalangan) — qaysi karta ekanini topamiz.
        if (e.startsWith("Tap: ")) {
            val masked = e.removePrefix("Tap: ").substringBefore(',')
            runOnUiThread {
                val card = vm.cards.firstOrNull { it.dpanMasked == masked }
                if (card != null && vm.screen == Screen.Pay) {
                    tapped = card.tokenId
                    // SDK bir martalik tanlovni tapdan keyin tozalaydi — ekran ham asosiy kartaga qaytsin.
                    payCard = null
                    vm.onTapped(card.tokenId)
                }
                vm.reloadLocal()
            }
        }
    }

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(AppPrefs.localized(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
        prefs = vm.prefs
        onboarded = prefs.onboarded && prefs.pinState != null
        // Til almashganda Activity qayta yaratiladi — qulf qayta so'ralmaydi.
        locked = onboarded && savedInstanceState?.getBoolean("unlocked") != true
        WalletSetup.wallet(this).addListener(listener)
        setContent { Root() }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putBoolean("unlocked", !locked)
    }

    override fun onDestroy() {
        WalletSetup.wallet(this).removeListener(listener)
        super.onDestroy()
    }

    override fun onStop() {
        super.onStop()
        stoppedAt = SystemClock.elapsedRealtime()
    }

    override fun onStart() {
        super.onStart()
        if (onboarded && !locked && stoppedAt > 0 && SystemClock.elapsedRealtime() - stoppedAt > LOCK_AFTER_MS) locked = true
    }

    private val biometricAvailable get() = BiometricGate.available(this)

    private fun unlockWithBiometric() {
        val prompt = BiometricPrompt(this, ContextCompat.getMainExecutor(this), object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                unlocked()
            }
        })
        prompt.authenticate(
            BiometricPrompt.PromptInfo.Builder()
                .setTitle(getString(R.string.unlock_title))
                .setNegativeButtonText(getString(R.string.use_pin))
                .setAllowedAuthenticators(BIOMETRIC_STRONG)
                .build(),
        )
    }

    private fun unlocked() {
        locked = false
        pinError = null
        vm.refresh()
    }

    private fun checkPin(pin: String): Int? {
        val s = prefs.pinState ?: return null
        val (r, next) = prefs.pin.check(s, pin, System.currentTimeMillis())
        prefs.pinState = next
        return when (r) {
            PinPolicy.Check.Ok -> { unlocked(); null }
            is PinPolicy.Check.Wrong -> {
                pinError = if (r.lockedUntil > 0) getString(R.string.pin_locked, ((r.lockedUntil - System.currentTimeMillis()) / 1000).coerceAtLeast(1))
                else getString(R.string.pin_wrong, MAX_SOFT - r.failures.coerceAtMost(MAX_SOFT - 1))
                R.string.pin_wrong_short
            }
            is PinPolicy.Check.Locked -> {
                pinError = getString(R.string.pin_locked, ((r.until - System.currentTimeMillis()) / 1000).coerceAtLeast(1))
                R.string.pin_wrong_short
            }
        }
    }

    private fun setLang(l: Lang) {
        prefs.lang = l
        Notifier.channels(this)
        recreate()
    }

    private fun makeDefaultPaymentApp() {
        val i = Intent(CardEmulation.ACTION_CHANGE_DEFAULT)
            .putExtra(CardEmulation.EXTRA_CATEGORY, CardEmulation.CATEGORY_PAYMENT)
            .putExtra(CardEmulation.EXTRA_SERVICE_COMPONENT, ComponentName(this, MpayHceService::class.java))
        runCatching { startActivity(i) }.onFailure { vm.message = R.string.err_no_nfc to null }
    }

    /** Faqat debug: emulyator uchun virtual NFC ko'prigi (`src/debug`; release'da sinf yo'q). */
    private fun startVirtualNfc() {
        vm.message = (if (DebugTools.startVirtualNfc(this)) R.string.msg_virtual_nfc else R.string.err_generic) to null
    }

    @Composable
    private fun Root() {
        MpayTheme {
            val notifyLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
                prefs.notifications = ok
                pendingNotify?.invoke()
                pendingNotify = null
            }
            val askNotifications: (() -> Unit) -> Unit = { after ->
                if (Build.VERSION.SDK_INT >= 33) {
                    pendingNotify = after
                    notifyLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                } else {
                    prefs.notifications = true
                    after()
                }
            }
            // Surface — rang berilmagan matnlar uchun to'g'ri kontent rangi (aks holda qora).
            Surface(
                Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing).semantics { testTagsAsResourceId = true },
                color = MpayColors.Background,
                contentColor = MpayColors.TextPrimary,
            ) {
                when {
                    !onboarded -> Onboarding(
                        langChosen = prefs.langChosen,
                        currentLang = prefs.lang,
                        biometricAvailable = biometricAvailable,
                        pinPolicy = prefs.pin,
                        onLang = ::setLang,
                        onPin = { prefs.pinState = prefs.pin.create(it, prefs.newSalt()) },
                        onBiometric = { prefs.biometricUnlock = it },
                        onNotifications = askNotifications,
                        onFinish = {
                            prefs.onboarded = true
                            Sync.schedule(this@MainActivity)
                            onboarded = true
                            locked = false
                            vm.refresh()
                        },
                    )
                    locked -> LockScreen()
                    else -> Main(askNotifications)
                }
            }
        }
    }

    private var pendingNotify: (() -> Unit)? = null

    @Composable
    private fun LockScreen() {
        LaunchedEffect(Unit) { if (prefs.biometricUnlock && biometricAvailable) unlockWithBiometric() }
        Box(Modifier.fillMaxSize().padding(24.dp)) {
            PinEntry(
                title = stringResource(R.string.unlock_title),
                subtitle = stringResource(R.string.unlock_sub),
                validate = ::checkPin,
                error = pinError,
                extra = if (prefs.biometricUnlock && biometricAvailable) {
                    {
                        IconButton(::unlockWithBiometric, Modifier.size(72.dp).testTag("bio_unlock")) {
                            Icon(MpayIcons.Fingerprint, stringResource(R.string.unlock_bio), tint = MpayColors.Mint, modifier = Modifier.size(36.dp))
                        }
                    }
                } else null,
            ) {}
        }
    }

    @Composable
    private fun Main(askNotifications: (() -> Unit) -> Unit) {
        val snack = remember { SnackbarHostState() }
        val msg = vm.message
        val text = msg?.let { (id, arg) -> if (arg != null) stringResource(id, arg) else stringResource(id) }
        LaunchedEffect(msg) {
            if (text != null) {
                snack.showSnackbar(text)
                vm.message = null
            }
        }
        BackHandler { if (vm.screen == Screen.Pay) leavePay(); if (!vm.back()) finish() }
        // To'lov ekraniga har kirish — toza holat (oldingi tap natijasi qolmasin).
        val onPay = vm.screen == Screen.Pay
        LaunchedEffect(onPay) { if (onPay) leavePay() }
        val lang = prefs.lang
        Scaffold(snackbarHost = { SnackbarHost(snack, Modifier.testTag("snackbar")) }, containerColor = MpayColors.Background) { pad ->
            Box(Modifier.padding(pad)) {
                when (val s = vm.screen) {
                    Screen.Home -> HomeScreen(vm, lang)
                    Screen.AddCard -> AddCardScreen(vm)
                    is Screen.Otp -> OtpScreen(vm, s)
                    is Screen.Card -> CardScreen(vm, s.tokenId)
                    Screen.Pay -> PayScreen(
                        vm, lang, biometricAvailable,
                        secondsLeft = { WalletSetup.wallet(this@MainActivity).cdcvm.secondsLeft() },
                        selected = payCard,
                        onSelect = { id ->
                            payCard = id
                            // Tanlov darhol: CDCVM chegarasidan kichik summa biometriyasiz ham o'tadi.
                            WalletSetup.wallet(this@MainActivity).nextTapCard = id
                        },
                        onAuthenticate = ::authenticatePayment,
                        tappedToken = tapped,
                        onLeave = { leavePay(); vm.back() },
                        onDone = { leavePay() },
                        onShown = { WalletSetup.wallet(this@MainActivity).nextTapCard = it },
                    )
                    is Screen.History -> HistoryScreen(vm, lang, s.tokenId)
                    Screen.Settings -> {
                        var bio by remember { mutableStateOf(prefs.biometricUnlock) }
                        var notify by remember { mutableStateOf(prefs.notifications && Notifier.allowed(this@MainActivity)) }
                        val pins = ServerPinPolicy.parseList(BuildConfig.SERVER_FINGERPRINTS)
                        SettingsScreen(
                            SettingsModel(
                                lang = lang,
                                biometricAvailable = biometricAvailable,
                                biometricUnlock = bio,
                                notifications = notify,
                                server = BuildConfig.SERVER,
                                serverPinned = pins.isNotEmpty(),
                                version = BuildConfig.VERSION_NAME + if (BuildConfig.SANDBOX) " · sandbox" else "",
                                debugTools = DebugTools.ENABLED,
                                onLang = ::setLang,
                                onBiometric = { bio = it; prefs.biometricUnlock = it },
                                onNotifications = { on ->
                                    if (on) askNotifications { notify = prefs.notifications } else { prefs.notifications = false; notify = false }
                                },
                                onChangePin = { vm.go(Screen.ChangePin) },
                                onDefaultPayment = ::makeDefaultPaymentApp,
                                onVirtualNfc = ::startVirtualNfc,
                                // Faqat debug: fon sinxronlashi darhol (bildirishnomalar bilan), 15 daqiqa kutmasdan.
                                onSyncNow = { Sync.now(this@MainActivity); vm.message = R.string.msg_sync_queued to null },
                                onReset = {
                                    vm.resetWallet {
                                        onboarded = false
                                        locked = false
                                    }
                                },
                                onBack = { vm.back() },
                            ),
                        )
                    }
                    Screen.ChangePin -> ChangePin()
                }
            }
        }
    }

    private fun leavePay() {
        payCard = null
        tapped = null
        WalletSetup.wallet(this).nextTapCard = null
        vm.clearPayment()
    }

    private fun authenticatePayment() {
        val w = WalletSetup.wallet(this)
        // Asosiy kartadan boshqasi tanlangan bo'lsa — faqat shu bitta tap uchun.
        w.nextTapCard = payCard
        tapped = null
        vm.clearPayment()
        BiometricGate.authenticate(this, w.cdcvm) { ok, _ ->
            if (!ok) vm.message = R.string.err_biometric to null
        }
    }

    @Composable
    private fun ChangePin() {
        var step by remember { mutableStateOf(0) }
        var first by remember { mutableStateOf("") }
        var err by remember { mutableStateOf<String?>(null) }
        Box(Modifier.fillMaxSize().padding(24.dp)) {
            when (step) {
                0 -> PinEntry(stringResource(R.string.pin_current_title), stringResource(R.string.unlock_sub), validate = { pin ->
                    val s = prefs.pinState ?: return@PinEntry null
                    val (r, next) = prefs.pin.check(s, pin, System.currentTimeMillis())
                    prefs.pinState = next
                    if (r == PinPolicy.Check.Ok) null else R.string.pin_wrong_short
                }, error = err) { step = 1 }
                1 -> PinEntry(stringResource(R.string.pin_new_title), stringResource(R.string.pin_create_sub), validate = { if (prefs.pin.valid(it)) null else R.string.pin_too_simple }) {
                    first = it
                    step = 2
                }
                else -> PinEntry(stringResource(R.string.pin_confirm_title), stringResource(R.string.pin_confirm_sub), validate = { if (it == first) null else R.string.pin_mismatch }, onMismatchReset = { step = 1 }) {
                    prefs.pinState = prefs.pin.create(it, prefs.newSalt())
                    vm.message = R.string.msg_pin_changed to null
                    vm.back()
                }
            }
        }
    }

    companion object {
        /** Fonda shu vaqtdan ko'p turgan ilova qayta qulflanadi. */
        const val LOCK_AFTER_MS = 30_000L
        /** Kutishsiz urinishlar (5-dan keyin kutish boshlanadi). */
        private const val MAX_SOFT = 5
    }
}
