package uz.dehqonkomakchi.app.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import uz.dehqonkomakchi.app.core.prefs.UserPrefs
import uz.dehqonkomakchi.app.core.prefs.UserSettings
import uz.dehqonkomakchi.app.data.db.DehqonDatabase
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val userPrefs: UserPrefs,
    private val database: DehqonDatabase,
) : ViewModel() {

    val settings: StateFlow<UserSettings> =
        userPrefs.settings.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), UserSettings())

    fun setNotifications(enabled: Boolean) = viewModelScope.launch { userPrefs.setNotificationsEnabled(enabled) }
    fun setTheme(mode: String) = viewModelScope.launch { userPrefs.setDarkModeOverride(mode) }
    fun setTextScale(scale: Float) = viewModelScope.launch { userPrefs.setTextScale(scale) }
    fun setRegion(region: String, district: String) = viewModelScope.launch { userPrefs.setRegion(region, district) }
    fun deleteAllData() = viewModelScope.launch {
        userPrefs.clearAll()
        database.clearAllTables()
    }
}
