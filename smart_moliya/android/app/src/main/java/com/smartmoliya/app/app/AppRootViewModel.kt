package com.smartmoliya.app.app

import androidx.lifecycle.ViewModel
import com.smartmoliya.app.core.datastore.ThemeManager
import com.smartmoliya.app.core.security.PinManager
import com.smartmoliya.app.feature.auth.domain.AuthRepository
import com.smartmoliya.app.ui.theme.AppThemeId
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject

@HiltViewModel
class AppRootViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val pinManager: PinManager,
    private val themeManager: ThemeManager
) : ViewModel() {

    val theme: StateFlow<AppThemeId> = themeManager.theme

    fun isLoggedIn(): Boolean = authRepository.isLoggedIn()

    fun isPinConfigured(): Boolean = pinManager.isPinSet()
}
