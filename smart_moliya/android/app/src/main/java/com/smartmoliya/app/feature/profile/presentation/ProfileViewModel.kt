package com.smartmoliya.app.feature.profile.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smartmoliya.app.BuildConfig
import com.smartmoliya.app.core.datastore.ThemeManager
import com.smartmoliya.app.core.network.ApiService
import com.smartmoliya.app.core.network.dto.UserDto
import com.smartmoliya.app.feature.auth.domain.AuthRepository
import com.smartmoliya.app.ui.theme.AppThemeId
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileUiState(val user: UserDto? = null, val loggedOut: Boolean = false)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val api: ApiService,
    private val authRepository: AuthRepository,
    private val themeManager: ThemeManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    val currentTheme: StateFlow<AppThemeId> = themeManager.theme

    init {
        if (!BuildConfig.OFFLINE_MODE) {
            viewModelScope.launch {
                runCatching { api.me() }.onSuccess { _uiState.value = _uiState.value.copy(user = it) }
            }
        }
    }

    fun setTheme(id: AppThemeId) = themeManager.setTheme(id)

    fun logout() {
        authRepository.logout()
        _uiState.value = _uiState.value.copy(loggedOut = true)
    }
}
