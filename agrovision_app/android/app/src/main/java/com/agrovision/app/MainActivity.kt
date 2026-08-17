package com.agrovision.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.app.data.repo.SettingsRepository
import com.agrovision.app.ui.nav.AppNavHost
import com.agrovision.app.ui.screens.BootstrapPhase
import com.agrovision.app.ui.screens.BootstrapScreen
import com.agrovision.app.ui.screens.BootstrapViewModel
import com.agrovision.app.ui.theme.AgroVisionTheme
import dagger.hilt.android.AndroidEntryPoint
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/** Tema rejimini (system/light/dark) saqlab, butun ilovaga uzatadi. */
@HiltViewModel
class ThemeViewModel @Inject constructor(
    private val settingsRepository: SettingsRepository,
) : ViewModel() {
    private val _theme = MutableStateFlow("system")
    val theme: StateFlow<String> = _theme.asStateFlow()

    init {
        viewModelScope.launch { _theme.value = settingsRepository.get("theme", "system") }
    }

    fun setTheme(mode: String) { _theme.value = mode }
}

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    private val bootstrapViewModel: BootstrapViewModel by viewModels()
    private val themeViewModel: ThemeViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val themeMode by themeViewModel.theme.collectAsState()
            val bootstrap by bootstrapViewModel.state.collectAsState()

            AgroVisionTheme(themeMode = themeMode) {
                if (bootstrap.phase == BootstrapPhase.READY) {
                    AppNavHost(onThemeChanged = themeViewModel::setTheme)
                } else {
                    BootstrapScreen(
                        state = bootstrap,
                        onLoadDemo = bootstrapViewModel::loadDemoData,
                        onStartEmpty = bootstrapViewModel::startEmpty,
                    )
                }
            }
        }
    }
}
