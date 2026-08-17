package com.agrovision.mobile.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.repository.SettingsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(val theme: String = "light", val language: String = "uz", val saved: Boolean = false)

@HiltViewModel
class SettingsViewModel @Inject constructor(private val settingsRepository: SettingsRepository) : ViewModel() {
    private val _state = MutableStateFlow(SettingsUiState())
    val state: StateFlow<SettingsUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            _state.value = SettingsUiState(
                theme = settingsRepository.get("theme", "light"),
                language = settingsRepository.get("language", "uz"),
            )
        }
    }

    fun setTheme(theme: String) { _state.value = _state.value.copy(theme = theme, saved = false) }
    fun setLanguage(language: String) { _state.value = _state.value.copy(language = language, saved = false) }

    fun save() {
        viewModelScope.launch {
            settingsRepository.set("theme", _state.value.theme)
            settingsRepository.set("language", _state.value.language)
            _state.value = _state.value.copy(saved = true)
        }
    }
}
