package com.smartmoliya.app.feature.gamification.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smartmoliya.app.BuildConfig
import com.smartmoliya.app.core.network.ApiService
import com.smartmoliya.app.core.network.dto.BadgeDto
import com.smartmoliya.app.core.network.dto.ChallengeDto
import com.smartmoliya.app.core.network.dto.LeaderboardEntryDto
import com.smartmoliya.app.core.network.dto.ProgressDto
import com.smartmoliya.app.core.network.dto.UserChallengeDto
import com.smartmoliya.app.feature.expense.domain.Transaction
import com.smartmoliya.app.feature.expense.domain.TransactionRepository
import com.smartmoliya.app.feature.expense.domain.TransactionType
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.launch
import java.util.Calendar
import java.util.concurrent.TimeUnit
import javax.inject.Inject

/** Offline rejimdagi lokal challenge - progress tranzaksiyalardan real vaqtda hisoblanadi. */
data class LocalChallenge(
    val title: String,
    val description: String,
    val targetValue: Double,
    val progressValue: Double,
    val xpReward: Int
) {
    val completed: Boolean get() = progressValue >= targetValue
}

/** Offline'da nishon: earned bayrog'i bilan. */
data class LocalBadge(val badge: BadgeDto, val earned: Boolean)

data class GamificationUiState(
    val progress: ProgressDto? = null,
    val badges: List<BadgeDto> = emptyList(),
    val leaderboard: List<LeaderboardEntryDto> = emptyList(),
    val activeChallenges: List<ChallengeDto> = emptyList(),
    val myChallenges: List<UserChallengeDto> = emptyList(),
    val localChallenges: List<LocalChallenge> = emptyList(),
    val localBadges: List<LocalBadge> = emptyList(),
    val isLoading: Boolean = false,
    val message: String? = null
)

@HiltViewModel
class GamificationViewModel @Inject constructor(
    private val api: ApiService,
    transactionRepository: TransactionRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(GamificationUiState())
    val uiState: StateFlow<GamificationUiState> = _uiState.asStateFlow()

    init {
        if (BuildConfig.OFFLINE_MODE) {
            transactionRepository.observeTransactions()
                .map { computeLocalState(it) }
                .onEach { _uiState.value = it }
                .launchIn(viewModelScope)
        } else {
            refresh()
        }
    }

    fun refresh() {
        if (BuildConfig.OFFLINE_MODE) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, message = null)
            runCatching {
                val progress = api.getMyProgress()
                val badges = api.listBadges()
                val leaderboard = api.getLeaderboard()
                val challenges = api.listChallenges()
                val mine = api.listMyChallenges()
                _uiState.value = GamificationUiState(
                    progress = progress,
                    badges = badges,
                    leaderboard = leaderboard,
                    activeChallenges = challenges,
                    myChallenges = mine,
                    isLoading = false
                )
            }.onFailure {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    message = "Ma'lumotlarni yuklab bo'lmadi (offline yoki server xatosi)"
                )
            }
        }
    }

    fun joinChallenge(challengeId: String) {
        if (BuildConfig.OFFLINE_MODE) return
        viewModelScope.launch {
            runCatching { api.joinChallenge(challengeId) }
                .onSuccess {
                    _uiState.value = _uiState.value.copy(message = "Challenge'ga qo'shildingiz!")
                    refresh()
                }
                .onFailure { _uiState.value = _uiState.value.copy(message = "Qo'shilib bo'lmadi (allaqachon a'zo bo'lishingiz mumkin)") }
        }
    }

    fun refreshChallengeProgress(challengeId: String) {
        if (BuildConfig.OFFLINE_MODE) return
        viewModelScope.launch {
            runCatching { api.refreshChallenge(challengeId) }
                .onSuccess { refresh() }
        }
    }
}

/** Offline gamification: barcha ko'rsatkichlar qurilmadagi tranzaksiyalardan hisoblanadi. */
private fun computeLocalState(transactions: List<Transaction>): GamificationUiState {
    val (currentStreak, longestStreak) = computeStreaks(transactions)

    val badgeStates = listOf(
        LocalBadge(
            BadgeDto("first_transaction", "Birinchi qadam", "Birinchi tranzaksiyangizni qo'shdingiz", 50),
            earned = transactions.isNotEmpty()
        ),
        LocalBadge(
            BadgeDto("streak_7_days", "Bir hafta izchil", "7 kun ketma-ket yozuv kiritdingiz", 150),
            earned = longestStreak >= 7
        ),
        LocalBadge(
            BadgeDto("streak_30_days", "Oylik marafon", "30 kun ketma-ket yozuv kiritdingiz", 500),
            earned = longestStreak >= 30
        ),
        LocalBadge(
            BadgeDto("txn_50", "Faol hisobchi", "50 ta tranzaksiya kiritdingiz", 200),
            earned = transactions.size >= 50
        ),
    )

    val xp = transactions.size * 25 + badgeStates.filter { it.earned }.sumOf { it.badge.xp_reward }
    val progress = ProgressDto(
        xp = xp,
        level = xp / 1000 + 1,
        current_streak = currentStreak,
        longest_streak = longestStreak
    )

    return GamificationUiState(
        progress = progress,
        localBadges = badgeStates,
        localChallenges = listOf(
            weeklySavingChallenge(transactions),
            monthlyNoSpendChallenge(transactions)
        )
    )
}

private fun computeStreaks(transactions: List<Transaction>): Pair<Int, Int> {
    if (transactions.isEmpty()) return 0 to 0
    val days = transactions.map { TimeUnit.MILLISECONDS.toDays(it.occurredAt) }.toSortedSet()

    var longest = 1
    var run = 1
    val list = days.toList()
    for (i in 1 until list.size) {
        run = if (list[i] == list[i - 1] + 1) run + 1 else 1
        if (run > longest) longest = run
    }

    val today = TimeUnit.MILLISECONDS.toDays(System.currentTimeMillis())
    var current = 0
    if (days.contains(today) || days.contains(today - 1)) {
        var day = if (days.contains(today)) today else today - 1
        while (days.contains(day)) {
            current++
            day--
        }
    }
    return current to longest
}

private fun weeklySavingChallenge(transactions: List<Transaction>): LocalChallenge {
    val calendar = Calendar.getInstance()
    calendar.set(Calendar.DAY_OF_WEEK, calendar.firstDayOfWeek)
    calendar.set(Calendar.HOUR_OF_DAY, 0)
    calendar.set(Calendar.MINUTE, 0)
    calendar.set(Calendar.SECOND, 0)
    calendar.set(Calendar.MILLISECOND, 0)
    val weekStart = calendar.timeInMillis

    val weekly = transactions.filter { it.occurredAt >= weekStart }
    val saved = weekly.filter { it.type == TransactionType.INCOME }.sumOf { it.amount } -
        weekly.filter { it.type == TransactionType.EXPENSE }.sumOf { it.amount }

    return LocalChallenge(
        title = "Haftalik tejash",
        description = "Bu hafta kamida 100 000 so'm tejang (daromad - xarajat)",
        targetValue = 100_000.0,
        progressValue = saved.coerceAtLeast(0.0),
        xpReward = 200
    )
}

private fun monthlyNoSpendChallenge(transactions: List<Transaction>): LocalChallenge {
    val calendar = Calendar.getInstance()
    val today = calendar.get(Calendar.DAY_OF_MONTH)
    calendar.set(Calendar.DAY_OF_MONTH, 1)
    calendar.set(Calendar.HOUR_OF_DAY, 0)
    calendar.set(Calendar.MINUTE, 0)
    calendar.set(Calendar.SECOND, 0)
    calendar.set(Calendar.MILLISECOND, 0)
    val monthStart = calendar.timeInMillis

    val spendDays = transactions
        .filter { it.type == TransactionType.EXPENSE && it.occurredAt >= monthStart }
        .map { TimeUnit.MILLISECONDS.toDays(it.occurredAt) }
        .toSet()
    val noSpendDays = (today - spendDays.size).coerceAtLeast(0)

    return LocalChallenge(
        title = "Xarajatsiz kunlar",
        description = "Bu oy kamida 5 kun hech narsa sarflamang",
        targetValue = 5.0,
        progressValue = noSpendDays.toDouble(),
        xpReward = 150
    )
}
