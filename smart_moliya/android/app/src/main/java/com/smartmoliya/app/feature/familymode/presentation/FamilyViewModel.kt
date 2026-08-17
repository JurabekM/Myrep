package com.smartmoliya.app.feature.familymode.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smartmoliya.app.BuildConfig
import com.smartmoliya.app.core.database.dao.LocalTaskDao
import com.smartmoliya.app.core.database.entity.LocalTaskEntity
import com.smartmoliya.app.core.network.ApiService
import com.smartmoliya.app.core.network.dto.AllowanceRequestDto
import com.smartmoliya.app.core.network.dto.FamilyGroupCreateDto
import com.smartmoliya.app.core.network.dto.FamilyGroupWithMembersDto
import com.smartmoliya.app.core.network.dto.TaskRewardApproveDto
import com.smartmoliya.app.core.network.dto.TaskRewardCreateDto
import com.smartmoliya.app.core.network.dto.TaskRewardDto
import com.smartmoliya.app.feature.expense.domain.TransactionRepository
import com.smartmoliya.app.feature.expense.domain.TransactionType
import com.smartmoliya.app.feature.wallets.domain.Wallet
import com.smartmoliya.app.feature.wallets.domain.WalletRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.launch
import java.util.UUID
import javax.inject.Inject

data class FamilyUiState(
    val groupWithMembers: FamilyGroupWithMembersDto? = null,
    val tasks: List<TaskRewardDto> = emptyList(),
    /** Offline rejim: lokal vazifalar va mukofot tushadigan hamyonlar. */
    val localTasks: List<LocalTaskEntity> = emptyList(),
    val wallets: List<Wallet> = emptyList(),
    val isLoading: Boolean = false,
    val message: String? = null
)

@HiltViewModel
class FamilyViewModel @Inject constructor(
    private val api: ApiService,
    private val localTaskDao: LocalTaskDao,
    private val transactionRepository: TransactionRepository,
    walletRepository: WalletRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(FamilyUiState())
    val uiState: StateFlow<FamilyUiState> = _uiState.asStateFlow()

    init {
        if (BuildConfig.OFFLINE_MODE) {
            localTaskDao.observeAll()
                .onEach { tasks -> _uiState.value = _uiState.value.copy(localTasks = tasks) }
                .launchIn(viewModelScope)
            walletRepository.observeWallets()
                .onEach { wallets -> _uiState.value = _uiState.value.copy(wallets = wallets) }
                .launchIn(viewModelScope)
        } else {
            refresh()
        }
    }

    fun refresh() {
        if (BuildConfig.OFFLINE_MODE) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, message = null)
            val group = runCatching { api.getMyFamilyGroup() }.getOrNull()
            val tasks = if (group != null) {
                runCatching { api.listFamilyTasks() }.getOrDefault(emptyList())
            } else {
                emptyList()
            }
            _uiState.value = _uiState.value.copy(
                groupWithMembers = group, tasks = tasks, isLoading = false
            )
        }
    }

    // --- Offline: lokal vazifa/mukofot oqimi ---

    fun createLocalTask(title: String, rewardAmount: Double) {
        viewModelScope.launch {
            localTaskDao.upsert(
                LocalTaskEntity(
                    id = UUID.randomUUID().toString(),
                    title = title,
                    rewardAmount = rewardAmount,
                    status = "PENDING",
                    createdAt = System.currentTimeMillis()
                )
            )
        }
    }

    fun markLocalTaskDone(taskId: String) {
        viewModelScope.launch {
            val task = localTaskDao.getById(taskId) ?: return@launch
            localTaskDao.upsert(task.copy(status = "DONE"))
        }
    }

    fun approveLocalTask(taskId: String, walletId: String) {
        viewModelScope.launch {
            val task = localTaskDao.getById(taskId) ?: return@launch
            if (task.status != "DONE") return@launch
            transactionRepository.addTransaction(
                walletId = walletId,
                categoryId = null,
                type = TransactionType.INCOME,
                amount = task.rewardAmount,
                note = "Vazifa mukofoti: ${task.title}"
            )
            localTaskDao.upsert(task.copy(status = "APPROVED"))
            _uiState.value = _uiState.value.copy(message = "Mukofot hamyonga tushdi ✅")
        }
    }

    fun deleteLocalTask(taskId: String) {
        viewModelScope.launch { localTaskDao.deleteById(taskId) }
    }

    // --- Online: server orqali oila guruhi ---

    fun createGroup(name: String) {
        viewModelScope.launch {
            runCatching { api.createFamilyGroup(FamilyGroupCreateDto(name)) }
                .onSuccess { refresh() }
                .onFailure { _uiState.value = _uiState.value.copy(message = "Guruh yaratib bo'lmadi") }
        }
    }

    fun joinGroup(groupId: String) {
        viewModelScope.launch {
            runCatching { api.joinFamilyGroup(groupId) }
                .onSuccess { refresh() }
                .onFailure { _uiState.value = _uiState.value.copy(message = "Guruhga qo'shilib bo'lmadi (ID'ni tekshiring)") }
        }
    }

    fun sendAllowance(childWalletId: String, amount: Double, note: String?) {
        viewModelScope.launch {
            runCatching { api.sendAllowance(AllowanceRequestDto(childWalletId, amount, note)) }
                .onSuccess { _uiState.value = _uiState.value.copy(message = "Pul yuborildi ✅") }
                .onFailure { _uiState.value = _uiState.value.copy(message = "Yuborib bo'lmadi (hamyon ID va guruhni tekshiring)") }
        }
    }

    fun createTask(assignedToUserId: String, title: String, rewardAmount: Double) {
        viewModelScope.launch {
            runCatching { api.createFamilyTask(TaskRewardCreateDto(assignedToUserId, title, rewardAmount)) }
                .onSuccess { refresh() }
                .onFailure { _uiState.value = _uiState.value.copy(message = "Vazifa yaratib bo'lmadi") }
        }
    }

    fun markTaskDone(taskId: String) {
        viewModelScope.launch {
            runCatching { api.markTaskDone(taskId) }
                .onSuccess { refresh() }
                .onFailure { _uiState.value = _uiState.value.copy(message = "Belgilab bo'lmadi") }
        }
    }

    fun approveTask(taskId: String, walletId: String) {
        viewModelScope.launch {
            runCatching { api.approveTask(taskId, TaskRewardApproveDto(walletId)) }
                .onSuccess {
                    _uiState.value = _uiState.value.copy(message = "Tasdiqlandi, mukofot to'landi ✅")
                    refresh()
                }
                .onFailure { _uiState.value = _uiState.value.copy(message = "Tasdiqlab bo'lmadi") }
        }
    }
}
