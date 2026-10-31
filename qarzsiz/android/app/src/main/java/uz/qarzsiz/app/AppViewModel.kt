package uz.qarzsiz.app

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import uz.qarzsiz.app.data.AppState
import uz.qarzsiz.app.data.LoadResult
import uz.qarzsiz.app.data.StateStore
import uz.qarzsiz.app.data.Payment
import uz.qarzsiz.app.data.ReminderSettings
import uz.qarzsiz.app.data.Store
import uz.qarzsiz.app.data.Stores
import uz.qarzsiz.app.reminders.ReminderScheduler
import uz.qarzsiz.core.Debt
import uz.qarzsiz.core.Habit
import uz.qarzsiz.core.Habits
import uz.qarzsiz.core.Ledger
import uz.qarzsiz.core.Overview
import uz.qarzsiz.core.OverviewCalc
import uz.qarzsiz.core.Pin
import uz.qarzsiz.core.PlanSettings
import uz.qarzsiz.core.Script
import uz.qarzsiz.core.TalkStatus
import java.time.LocalDate
import java.util.UUID

/** Ilova holati: yuklash, o'zgartirish va har o'zgarishdan keyin shifrlangan faylga saqlash. */
class AppViewModel(app: Application, private val store: StateStore) : AndroidViewModel(app) {
    /** `viewModels()` uchun: haqiqiy shifrlangan fayl. */
    constructor(app: Application) : this(app, Stores.factory(app))
    private val saveLock = Mutex()

    sealed interface Status {
        data object Loading : Status
        data object Ready : Status
        data class Broken(val reason: String) : Status
    }

    private val _status = MutableStateFlow<Status>(Status.Loading)
    val status: StateFlow<Status> = _status.asStateFlow()

    /** Oxirgi saqlash muvaffaqiyatsiz bo'ldi (xotira to'lgan, Keystore xatosi) — UI ogohlantiradi. */
    private val _saveFailed = MutableStateFlow(false)
    val saveFailed: StateFlow<Boolean> = _saveFailed.asStateFlow()

    private val _state = MutableStateFlow(AppState())
    val state: StateFlow<AppState> = _state.asStateFlow()

    /** PIN o'rnatilgan va hali kiritilmagan — UI faqat qulf ekranini ko'rsatadi. */
    private val _locked = MutableStateFlow(false)
    val locked: StateFlow<Boolean> = _locked.asStateFlow()

    /** Ilova fonga o'tgan payt (`SystemClock.elapsedRealtime`, monoton). */
    private var backgroundSince: Long? = null

    /** Pul hisoblari faqat yadroda (`OverviewCalc`); UI tayyor raqamni ko'rsatadi. */
    val overview: StateFlow<Overview> = _state
        .map { it.debts to it.settings }
        .distinctUntilChanged()
        .map { (debts, settings) -> OverviewCalc.compute(debts, settings) }
        // 4 strategiya × 600 oygacha simulyatsiya — UI oqimidan tashqarida.
        .flowOn(Dispatchers.Default)
        .stateIn(viewModelScope, SharingStarted.Eagerly, OverviewCalc.compute(emptyList(), PlanSettings()))

    init {
        viewModelScope.launch(Dispatchers.IO) {
            when (val r = store.load()) {
                is LoadResult.Ok -> {
                    _state.value = r.state
                    // Qulf «Ready»dan oldin qo'yiladi: ma'lumot bir lahza ham ko'rinmaydi.
                    _locked.value = r.state.pin != null
                    _status.value = Status.Ready
                }
                LoadResult.Empty -> _status.value = Status.Ready
                is LoadResult.Broken -> _status.value = Status.Broken(r.reason)
            }
        }
    }

    private fun mutate(block: (AppState) -> AppState) {
        _state.update(block)
        // Qulf ichida eng so'nggi holat yoziladi: ketma-ket o'zgarishlarda eski nusxa yangisini bosib ketmaydi.
        viewModelScope.launch(Dispatchers.IO) {
            saveLock.withLock {
                _saveFailed.value = runCatching { store.save(_state.value) }.isFailure
            }
        }
    }

    fun today(): LocalDate = LocalDate.now()

    // --- sozlamalar ---
    fun finishOnboarding() = mutate { it.copy(onboardingDone = true) }
    fun updateSettings(s: PlanSettings) = mutate { it.copy(settings = s) }
    fun setSecureScreen(on: Boolean) = mutate { it.copy(secureScreen = on) }
    fun setScript(script: Script) = mutate { it.copy(script = script) }

    /** Eslatma sozlamalari: saqlanadi va signal darhol qayta rejalashtiriladi (yoki bekor qilinadi). */
    fun setReminders(r: ReminderSettings) {
        mutate { it.copy(reminders = r) }
        ReminderScheduler.apply(getApplication(), r)
    }
    fun markAnalysisSeen() {
        if (!_state.value.analysisSeen) mutate { it.copy(analysisSeen = true) }
    }

    // --- qarzlar ---
    fun newId(): String = UUID.randomUUID().toString()

    fun upsertDebt(debt: Debt) = mutate { s ->
        val exists = s.debts.any { it.id == debt.id }
        s.copy(debts = if (exists) s.debts.map { if (it.id == debt.id) debt else it } else s.debts + debt)
    }

    fun deleteDebt(id: String) = mutate { s ->
        s.copy(debts = s.debts.filterNot { it.id == id }, payments = s.payments.filterNot { it.debtId == id })
    }

    fun setTalkStatus(id: String, status: TalkStatus, note: String) = mutate { s ->
        s.copy(debts = s.debts.map { if (it.id == id) it.copy(talkStatus = status, note = note) else it })
    }

    fun addPayment(debtId: String, amount: Long, date: LocalDate, note: String) = mutate { s ->
        val debt = s.debts.firstOrNull { it.id == debtId } ?: return@mutate s
        val applied = minOf(amount, debt.balance)
        if (applied <= 0) return@mutate s
        val updated = Ledger.applyPayment(debt, applied, date)
        s.copy(
            debts = s.debts.map { if (it.id == debtId) updated else it },
            payments = s.payments + Payment(newId(), debtId, applied, date.toString(), note.trim()),
        )
    }

    fun deletePayment(paymentId: String) = mutate { s ->
        val p = s.payments.firstOrNull { it.id == paymentId } ?: return@mutate s
        s.copy(
            debts = s.debts.map { if (it.id == p.debtId) Ledger.revertPayment(it, p.amount) else it },
            payments = s.payments.filterNot { it.id == paymentId },
        )
    }

    // --- odatlar ---
    fun toggleHabit(habitId: String, date: LocalDate) = mutate { s ->
        val key = Habits.key(date, habitId)
        s.copy(habitDone = if (key in s.habitDone) s.habitDone - key else s.habitDone + key)
    }

    fun addHabit(title: String) {
        val t = title.trim()
        if (t.isEmpty()) return
        mutate { it.copy(habits = it.habits + Habit("u-" + newId().take(8), t)) }
    }

    fun removeHabit(id: String) = mutate { s ->
        s.copy(habits = s.habits.filterNot { it.id == id }, habitDone = s.habitDone.filterNot { it.endsWith("|$id") }.toSet())
    }

    // --- PIN-kod ---
    sealed interface PinCheck {
        data object Ok : PinCheck
        /** Noto'g'ri; `attemptsLeft` — kutishsiz qolgan urinishlar. */
        data class Wrong(val attemptsLeft: Int) : PinCheck
        /** Juda ko'p xato: `ms` kutish kerak. */
        data class Wait(val ms: Long) : PinCheck
    }

    /** PIN'ni tekshiradi (og'ir PBKDF2 — fon oqimida); xatolar soni va kutish holatda saqlanadi. */
    suspend fun checkPin(pin: String, nowMs: Long = System.currentTimeMillis()): PinCheck {
        val lock = _state.value.pin ?: return PinCheck.Ok
        Pin.remainingLockMs(lock, nowMs).let { if (it > 0) return PinCheck.Wait(it) }
        val ok = withContext(Dispatchers.Default) { Pin.matches(lock, pin) }
        if (ok) {
            if (lock.failures != 0) mutate { s -> s.copy(pin = s.pin?.let(Pin::afterSuccess)) }
            return PinCheck.Ok
        }
        val updated = Pin.afterFailure(lock, nowMs)
        mutate { it.copy(pin = updated) }
        val wait = Pin.remainingLockMs(updated, nowMs)
        return if (wait > 0) PinCheck.Wait(wait) else PinCheck.Wrong(Pin.FREE_ATTEMPTS + 1 - updated.failures)
    }

    suspend fun unlock(pin: String): PinCheck = checkPin(pin).also { if (it == PinCheck.Ok) _locked.value = false }

    /** Yangi PIN (eskisini almashtiradi). Kutish sozlamasi saqlanib qoladi. */
    suspend fun setPin(pin: String) {
        val grace = _state.value.pin?.graceSeconds ?: Pin.DEFAULT_GRACE_SECONDS
        val lock = withContext(Dispatchers.Default) { Pin.create(pin, grace) }
        mutate { it.copy(pin = lock) }
    }

    fun removePin() = mutate { it.copy(pin = null) }

    fun setPinGrace(seconds: Int) = mutate { s -> s.copy(pin = s.pin?.copy(graceSeconds = seconds)) }

    /** Activity.onStop: fonga o'tish vaqti. */
    fun onBackground(elapsedMs: Long) {
        if (_state.value.pin != null && !_locked.value) backgroundSince = elapsedMs
    }

    /** Activity.onStart: fonda kutish muddatidan uzoq tursa — qulf. */
    fun onForeground(elapsedMs: Long) {
        val since = backgroundSince ?: return
        backgroundSince = null
        val lock = _state.value.pin ?: return
        if (elapsedMs - since >= lock.graceSeconds * 1000L) _locked.value = true
    }

    // --- zaxira ---
    /** Zaxirada PIN xeshi yo'q: tiklangan qurilmada eski (unutilgan bo'lishi mumkin) PIN qulf solmaydi. */
    fun exportText(): String = Store.exportText(_state.value.copy(pin = null))

    /** Import: tekshiradi va almashtiradi. Xato bo'lsa — sababini qaytaradi. */
    fun importText(text: String): String? {
        val imported = try {
            Store.importText(text)
        } catch (e: Exception) {
            return "Fayl o'qilmadi: bu Qarzsiz zaxira nusxasi emas."
        }
        if (imported.schemaVersion > AppState.SCHEMA_VERSION) return "Fayl ilovaning yangiroq versiyasidan. Ilovani yangilang."
        if (imported.debts.any { it.balance < 0 || it.monthlyPayment < 0 || it.annualRateBp < 0 }) {
            return "Faylda noto'g'ri summa bor."
        }
        if (imported.debts.map { it.id }.toSet().size != imported.debts.size) return "Faylda takroriy qarz bor."
        // Joriy qurilmaning PIN'i saqlanadi (fayldagi PIN e'tiborga olinmaydi).
        mutate { imported.copy(onboardingDone = true, pin = _state.value.pin) }
        ReminderScheduler.apply(getApplication(), imported.reminders)
        return null
    }

    /** Buzilgan fayl yoki foydalanuvchi so'rovi bo'yicha hammasini o'chirish. */
    fun wipeAll() {
        viewModelScope.launch(Dispatchers.IO) {
            // Holat qulf ichida tozalanadi: navbatdagi saqlash eski ma'lumotni qayta yozib qo'ymaydi.
            ReminderScheduler.cancel(getApplication())
            saveLock.withLock {
                runCatching { store.wipe() }
                _state.value = AppState()
            }
            _locked.value = false
            _status.value = Status.Ready
        }
    }
}
