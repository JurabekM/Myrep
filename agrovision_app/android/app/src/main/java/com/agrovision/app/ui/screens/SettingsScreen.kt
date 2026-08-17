package com.agrovision.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavHostController
import com.agrovision.app.config.Constants
import com.agrovision.app.core.I18n
import com.agrovision.app.data.repo.SettingsRepository
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(
    val theme: String = "system",
    val language: String = "uz",
    val offlineMode: String = "auto",
    val weatherProvider: String = "open-meteo",
    val backupKeep: String = "20",
    val saved: Boolean = false,
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val settingsRepository: SettingsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SettingsUiState())
    val state: StateFlow<SettingsUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            _state.value = SettingsUiState(
                theme = settingsRepository.get("theme", "system"),
                language = settingsRepository.get("language", "uz"),
                offlineMode = settingsRepository.get("offline_mode", "auto"),
                weatherProvider = settingsRepository.get("weather_provider", "open-meteo"),
                backupKeep = settingsRepository.get("backup_keep", "20"),
            )
        }
    }

    fun update(transform: SettingsUiState.() -> SettingsUiState) {
        _state.value = _state.value.transform().copy(saved = false)
    }

    fun save(onThemeChanged: (String) -> Unit) {
        viewModelScope.launch {
            val current = _state.value
            settingsRepository.set("theme", current.theme)
            settingsRepository.set("language", current.language)
            settingsRepository.set("offline_mode", current.offlineMode)
            settingsRepository.set("weather_provider", current.weatherProvider)
            settingsRepository.set("backup_keep", current.backupKeep)
            I18n.language = current.language
            onThemeChanged(current.theme)
            _state.value = current.copy(saved = true)
        }
    }
}

@Composable
fun SettingsScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    onThemeChanged: (String) -> Unit,
    viewModel: SettingsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Sozlamalar", onLogout) { padding ->
        ScreenColumn(padding, scrollToTopKey = if (state.saved) "saved" else null) {
            ChartCard("Ko'rinish") {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("system" to "Tizim", "light" to "Kunduzgi", "dark" to "Tungi").forEach { (key, label) ->
                        FilterChip(
                            selected = state.theme == key,
                            onClick = { viewModel.update { copy(theme = key) } },
                            label = { Text(label) },
                        )
                    }
                }
            }

            ChartCard("Til") {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    I18n.LANGUAGES.forEach { (key, label) ->
                        FilterChip(
                            selected = state.language == key,
                            onClick = { viewModel.update { copy(language = key) } },
                            label = { Text(label) },
                        )
                    }
                }
                Text(
                    "Til menyu va asosiy sarlavhalarga qo'llanadi.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            ChartCard("Tarmoq rejimi", "Ob-havo modulida internetdan foydalanishni boshqaradi") {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf(
                        "auto" to "Avto",
                        "on" to "Majburiy offlayn",
                        "off" to "Majburiy onlayn",
                    ).forEach { (key, label) ->
                        FilterChip(
                            selected = state.offlineMode == key,
                            onClick = { viewModel.update { copy(offlineMode = key) } },
                            label = { Text(label) },
                        )
                    }
                }
            }

            ChartCard("Ob-havo provayderi") {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf(
                        "open-meteo" to "Open-Meteo",
                        "nasa-power" to "NASA POWER",
                    ).forEach { (key, label) ->
                        FilterChip(
                            selected = state.weatherProvider == key,
                            onClick = { viewModel.update { copy(weatherProvider = key) } },
                            label = { Text(label) },
                        )
                    }
                }
                Text(
                    "Ikkalasi ham bepul va API kalitisiz. Tanlangan provayder javob bermasa " +
                        "ilova avtomatik ikkinchisiga o'tadi.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            ChartCard("Zaxira") {
                NumberField(
                    "Saqlanadigan zaxiralar soni",
                    state.backupKeep,
                    { value -> viewModel.update { copy(backupKeep = value) } },
                )
            }

            Button(
                onClick = { viewModel.save(onThemeChanged) },
                modifier = Modifier.fillMaxWidth().height(48.dp),
            ) { Text("Saqlash") }
            if (state.saved) InfoBanner("Sozlamalar saqlandi.")

            ChartCard("Ilova haqida") {
                Text("AgroVision v${Constants.APP_VERSION}", style = MaterialTheme.typography.bodyMedium)
                Text(
                    "Native Android ilova (Jetpack Compose) — desktop AgroVision platformasining " +
                        "to'liq analogi. Barcha ma'lumot va hisob-kitoblar qurilma ichida bajariladi; " +
                        "internet faqat Ob-havo modulida (Open-Meteo / NASA POWER) ishlatiladi.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
