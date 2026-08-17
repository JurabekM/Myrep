package com.agrovision.mobile.ui.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.repository.AuthRepository
import com.agrovision.mobile.data.repository.LoginResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LoginUiState(
    val username: String = "",
    val password: String = "",
    val loading: Boolean = false,
    val error: String? = null,
    val success: Boolean = false,
)

@HiltViewModel
class LoginViewModel @Inject constructor(private val authRepository: AuthRepository) : ViewModel() {
    private val _state = MutableStateFlow(LoginUiState())
    val state: StateFlow<LoginUiState> = _state.asStateFlow()

    fun onUsernameChange(value: String) { _state.value = _state.value.copy(username = value, error = null) }
    fun onPasswordChange(value: String) { _state.value = _state.value.copy(password = value, error = null) }

    fun login() {
        val current = _state.value
        if (current.username.isBlank() || current.password.isBlank()) {
            _state.value = current.copy(error = "Login va parolni kiriting.")
            return
        }
        viewModelScope.launch {
            _state.value = current.copy(loading = true, error = null)
            when (val result = authRepository.login(current.username, current.password)) {
                is LoginResult.Success -> _state.value = _state.value.copy(loading = false, success = true)
                LoginResult.InvalidCredentials -> _state.value = _state.value.copy(loading = false, error = "Login yoki parol noto'g'ri.")
                LoginResult.AccountDisabled -> _state.value = _state.value.copy(loading = false, error = "Hisob bloklangan.")
            }
        }
    }
}
