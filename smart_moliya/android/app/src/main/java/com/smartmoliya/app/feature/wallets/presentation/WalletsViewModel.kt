package com.smartmoliya.app.feature.wallets.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smartmoliya.app.feature.wallets.domain.Wallet
import com.smartmoliya.app.feature.wallets.domain.WalletRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

data class WalletsUiState(
    val wallets: List<Wallet> = emptyList(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

@HiltViewModel
class WalletsViewModel @Inject constructor(
    private val repository: WalletRepository
) : ViewModel() {

    private val _isLoading = MutableStateFlow(false)
    private val _errorMessage = MutableStateFlow<String?>(null)

    val uiState: StateFlow<WalletsUiState> = repository.observeWallets()
        .let { walletsFlow ->
            kotlinx.coroutines.flow.combine(walletsFlow, _isLoading, _errorMessage) { wallets, loading, error ->
                WalletsUiState(wallets = wallets, isLoading = loading, errorMessage = error)
            }
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), WalletsUiState())

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _isLoading.value = true
            runCatching { repository.refresh() }
                .onFailure { _errorMessage.value = "Serverga ulanib bo'lmadi, offline ma'lumot ko'rsatilmoqda" }
            _isLoading.value = false
        }
    }

    fun createWallet(name: String, currency: String) {
        viewModelScope.launch {
            repository.createWallet(name, currency)
        }
    }

    fun deleteWallet(walletId: String) {
        viewModelScope.launch {
            repository.deleteWallet(walletId)
        }
    }
}
