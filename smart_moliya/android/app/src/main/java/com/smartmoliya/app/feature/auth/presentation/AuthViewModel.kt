package com.smartmoliya.app.feature.auth.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smartmoliya.app.feature.auth.domain.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuthUiState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val loginSucceeded: Boolean = false,
    /** OTP kodi yuborilganini bildiradi (kod kiritish maydonini ochish uchun). */
    val otpRequested: Boolean = false,
    /** Dev backend SMS o'rniga kodni qaytaradi - foydalanuvchiga ko'rsatamiz. */
    val devOtpCode: String? = null
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    fun login(phone: String, password: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            authRepository.login(phone, password)
                .onSuccess { _uiState.value = AuthUiState(loginSucceeded = true) }
                .onFailure { _uiState.value = AuthUiState(errorMessage = mapError(it)) }
        }
    }

    fun register(phone: String, password: String, fullName: String?) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            authRepository.register(phone, password, fullName)
                .onSuccess { _uiState.value = AuthUiState(loginSucceeded = true) }
                .onFailure { _uiState.value = AuthUiState(errorMessage = mapError(it)) }
        }
    }

    fun requestOtp(phone: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            authRepository.requestOtp(phone)
                .onSuccess { devCode ->
                    _uiState.value = AuthUiState(otpRequested = true, devOtpCode = devCode)
                }
                .onFailure { _uiState.value = AuthUiState(errorMessage = mapError(it)) }
        }
    }

    fun verifyOtp(phone: String, code: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            authRepository.loginWithOtp(phone, code)
                .onSuccess { _uiState.value = AuthUiState(loginSucceeded = true) }
                .onFailure {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = "Kod noto'g'ri yoki muddati tugagan"
                    )
                }
        }
    }

    fun loginWithGoogle(idToken: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            authRepository.loginWithGoogle(idToken)
                .onSuccess { _uiState.value = AuthUiState(loginSucceeded = true) }
                .onFailure { _uiState.value = AuthUiState(errorMessage = mapError(it)) }
        }
    }

    fun reportGoogleSignInError(message: String?) {
        _uiState.value = AuthUiState(errorMessage = message ?: "Google orqali kirish bekor qilindi")
    }

    private fun mapError(throwable: Throwable): String =
        throwable.message ?: "Xatolik yuz berdi, qayta urinib ko'ring"
}
