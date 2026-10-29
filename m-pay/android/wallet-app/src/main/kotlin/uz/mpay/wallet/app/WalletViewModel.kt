package uz.mpay.wallet.app

import android.app.Application
import android.util.Log
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import uz.mpay.core.ApiException
import uz.mpay.core.ProvisionResult
import uz.mpay.core.Txn
import uz.mpay.core.WalletCard
import java.io.IOException

/** Ekranlar (oddiy stek — tashqi navigatsiya kutubxonasisiz). */
sealed interface Screen {
    data object Home : Screen
    data object AddCard : Screen
    data class Otp(val tokenId: String, val challengeId: String, val sentTo: String?) : Screen
    data class Card(val tokenId: String) : Screen
    data object Pay : Screen
    data class History(val tokenId: String?) : Screen
    data object Settings : Screen
    data object ChangePin : Screen
}

/** Karta bo'yicha tarix holati. */
data class HistoryState(
    val items: List<Txn> = emptyList(),
    val cursor: String? = null,
    val loading: Boolean = false,
    val end: Boolean = false,
    val error: Int? = null,
)

/**
 * Ilova holati va SDK chaqiruvlari. Tarmoq/Keystore — `Dispatchers.IO`; Compose holati **faqat Main'da**
 * yoziladi (IO'dan yozilgan holat qayta chizishni ishga tushirmasligi mumkin).
 */
class WalletViewModel(app: Application) : AndroidViewModel(app) {
    private val ctx get() = getApplication<Application>()
    val prefs = AppPrefs(app)

    var stack by mutableStateOf(listOf<Screen>(Screen.Home))
        private set
    val screen: Screen get() = stack.last()

    var cards by mutableStateOf(listOf<WalletCard>())
        private set
    var busy by mutableStateOf(false)
        private set
    var syncing by mutableStateOf(false)
        private set
    /** Bir martalik xabar (snackbar): matn resursi va argumenti. */
    var message by mutableStateOf<Pair<Int, String?>?>(null)
    /** Server bilan aloqa yo'q (oxirgi urinish). */
    var offline by mutableStateOf(false)
        private set
    /** Tap'dan keyin oxirgi tranzaksiya (to'lov ekranida natija). */
    var lastPayment by mutableStateOf<Txn?>(null)
        private set

    val history = mutableStateMapOf<String, HistoryState>()

    init {
        reloadLocal()
    }

    fun go(s: Screen) {
        stack = stack + s
    }

    /** `false` — stek bo'sh (Activity yopilsin). */
    fun back(): Boolean {
        if (stack.size <= 1) return false
        stack = stack.dropLast(1)
        return true
    }

    fun home() {
        stack = listOf(Screen.Home)
    }

    private fun replaceTop(s: Screen) {
        stack = stack.dropLast(1) + s
    }

    /** Lokal kartalar (tarmoqsiz) — Keystore o'qishi ham fonda. */
    fun reloadLocal() {
        viewModelScope.launch {
            val list = withContext(Dispatchers.IO) { runCatching { WalletSetup.wallet(ctx).cards() }.getOrDefault(emptyList()) }
            cards = list
        }
    }

    /** Fon ishi + xatoni foydalanuvchi matniga aylantirish. */
    private fun work(
        busyFlag: Boolean = true,
        onError: (Int) -> Unit = { message = it to null },
        block: suspend () -> Unit,
    ) {
        viewModelScope.launch {
            if (busyFlag) busy = true
            try {
                withContext(Dispatchers.IO) { block() }
                offline = false
            } catch (e: Exception) {
                Log.w(TAG, "amal: ${e.javaClass.simpleName} ${(e as? ApiException)?.code ?: ""}")
                if (e is IOException) offline = true
                onError(errorText(e))
            } finally {
                if (busyFlag) busy = false
                cards = withContext(Dispatchers.IO) { runCatching { WalletSetup.wallet(ctx).cards() }.getOrDefault(cards) }
            }
        }
    }

    /** Server bilan moslash (kartalar holati, kam LUK'lar, so'nggi tarix). */
    fun refresh() {
        if (syncing) return
        syncing = true
        work(busyFlag = false) {
            try {
                val (changes, _) = Sync.run(ctx)
                withContext(Dispatchers.Main) {
                    if (changes.isNotEmpty()) message = R.string.msg_cards_updated to null
                    history.clear()
                }
            } finally {
                withContext(Dispatchers.Main) { syncing = false }
            }
        }
    }

    // ------------------------------------------------------------ karta qo'shish

    fun addCard(pan: String, mmyy: String, onDone: () -> Unit) {
        val yymm = Format.mmyyToYymm(mmyy) ?: run { message = R.string.err_expiry to null; return }
        work {
            val r = WalletSetup.call(ctx) { it.provision(pan, yymm) }
            withContext(Dispatchers.Main) {
                when (r) {
                    is ProvisionResult.Active -> {
                        onDone()
                        replaceTop(Screen.Card(r.profile.tokenId))
                        message = R.string.msg_card_added to null
                    }
                    is ProvisionResult.PendingIdv -> {
                        onDone()
                        replaceTop(Screen.Otp(r.tokenId, r.challengeId, r.otpSentTo))
                    }
                    is ProvisionResult.Declined -> message = R.string.err_declined to null
                }
            }
        }
    }

    fun verifyOtp(s: Screen.Otp, code: String) = work {
        val p = WalletSetup.call(ctx) { it.verifyOtp(s.tokenId, s.challengeId, code) }
        withContext(Dispatchers.Main) {
            replaceTop(Screen.Card(p.tokenId))
            message = R.string.msg_card_added to null
        }
    }

    fun resendOtp(s: Screen.Otp) = work {
        val to = WalletSetup.call(ctx) { it.resendOtp(s.tokenId, s.challengeId) }
        withContext(Dispatchers.Main) { message = R.string.msg_otp_resent to to }
    }

    // ------------------------------------------------------------ karta boshqaruvi

    fun setDefault(tokenId: String) = work(busyFlag = false) {
        WalletSetup.wallet(ctx).setDefaultCard(tokenId)
        withContext(Dispatchers.Main) { message = R.string.msg_default_set to null }
    }

    fun suspend(tokenId: String) = work {
        WalletSetup.call(ctx) { it.suspendCard(tokenId) }
        withContext(Dispatchers.Main) { message = R.string.msg_suspended to null }
    }

    fun resume(tokenId: String) = work {
        WalletSetup.call(ctx) { it.resumeCard(tokenId) }
        withContext(Dispatchers.Main) { message = R.string.msg_resumed to null }
    }

    fun delete(tokenId: String) = work {
        WalletSetup.call(ctx) { it.deleteCard(tokenId) }
        prefs.setTxnMarker(tokenId, null)
        withContext(Dispatchers.Main) {
            history.remove(tokenId)
            home()
            message = R.string.msg_deleted to null
        }
    }

    fun replenish(tokenId: String) = work {
        val n = WalletSetup.call(ctx) { it.replenish(tokenId) }
        withContext(Dispatchers.Main) { message = R.string.msg_keys_added to n.toString() }
    }

    // ------------------------------------------------------------ tarix

    fun loadHistory(tokenId: String, reset: Boolean = false) {
        val cur = history[tokenId] ?: HistoryState()
        if (cur.loading || (cur.end && !reset)) return
        history[tokenId] = cur.copy(loading = true, error = null)
        val cursor = if (reset) null else cur.cursor
        work(busyFlag = false, onError = { e -> history[tokenId] = (history[tokenId] ?: cur).copy(loading = false, error = e) }) {
            val page = WalletSetup.call(ctx) { it.transactions(tokenId, cursor, PAGE) }
            withContext(Dispatchers.Main) {
                val prev = if (reset) emptyList() else (history[tokenId]?.items ?: emptyList())
                history[tokenId] = HistoryState(prev + page.transactions, page.nextCursor, false, page.nextCursor == null)
            }
        }
    }

    // ------------------------------------------------------------ to'lov

    /** Tap bo'ldi (SDK hodisasi): bir necha soniyadan keyin tarixdan natijani oladi. */
    fun onTapped(tokenId: String) {
        lastPayment = null
        viewModelScope.launch {
            repeat(5) {
                delay(2_000)
                val t = withContext(Dispatchers.IO) {
                    runCatching { WalletSetup.call(ctx) { it.transactions(tokenId, null, 1) }.transactions.firstOrNull() }.getOrNull()
                }
                if (t != null && System.currentTimeMillis() / 1000 - t.at < 120) {
                    lastPayment = t
                    history.remove(tokenId)
                    return@launch
                }
            }
        }
    }

    fun clearPayment() {
        lastPayment = null
    }

    /** Hamyonni butunlay tozalash (qurilmadagi kartalar, kalit, PIN). Serverdagi tokenlar — bank. */
    fun resetWallet(onDone: () -> Unit) = work {
        Sync.cancel(ctx)
        WalletSetup.wallet(ctx).reset()
        prefs.reset()
        withContext(Dispatchers.Main) {
            history.clear()
            home()
            onDone()
        }
    }

    companion object {
        private const val TAG = "MpayApp"
        const val PAGE = 20

        /** Server xato kodi → foydalanuvchi matni. */
        fun errorText(e: Throwable): Int = when (e) {
            is javax.net.ssl.SSLException -> R.string.err_server_untrusted
            is IOException -> R.string.err_network
            is ApiException -> when (e.code) {
                "SUSPENDED_BY_BANK" -> R.string.err_suspended_by_bank
                "OTP_INVALID" -> R.string.err_otp_invalid
                "OTP_EXPIRED", "CHALLENGE_NOT_FOUND" -> R.string.err_otp_expired
                "OTP_LOCKED" -> R.string.err_otp_locked
                "OTP_RESEND_LIMIT" -> R.string.err_otp_resend_limit
                "TOO_MANY_TOKENS", "TOO_MANY_DEVICES" -> R.string.err_too_many
                "CARD_ALREADY_ON_DEVICE" -> R.string.err_already_added
                "BAD_REQUEST" -> R.string.err_card_invalid
                "INTEGRITY_REQUIRED", "INTEGRITY_INVALID", "PQLINK_ATTESTATION" -> R.string.err_device_untrusted
                "RATE_LIMITED", "BUSY" -> R.string.err_busy
                "DEVICE_MISMATCH" -> R.string.err_device_mismatch
                "TOKEN_NOT_FOUND" -> R.string.err_card_not_found
                "INVALID_STATE" -> R.string.err_invalid_state
                else -> R.string.err_generic
            }
            is IllegalStateException -> if (e.message?.contains("pin") == true || e.message?.contains("TLS") == true) R.string.err_server_untrusted else R.string.err_generic
            is SecurityException -> R.string.err_server_untrusted
            else -> R.string.err_generic
        }
    }
}
