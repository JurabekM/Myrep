package com.agrovision.mobile.ui.nav

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.local.AppDatabase
import com.agrovision.mobile.data.local.SeedData
import com.agrovision.mobile.data.repository.MlRepository
import com.agrovision.mobile.data.repository.SettingsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import javax.inject.Inject

/**
 * Ilova birinchi marta ochilganda: baza urug'lanadi va ML modeli mahalliy
 * ravishda o'qitiladi — bularning barchasi tugagunicha splash ekran
 * ko'rsatiladi, shu bilan Login ekrani hech qachon bo'sh bazaga qarshi
 * ishlamaydi.
 */
@HiltViewModel
class BootstrapViewModel @Inject constructor(
    private val database: AppDatabase,
    private val mlRepository: MlRepository,
    private val settingsRepository: SettingsRepository,
) : ViewModel() {

    private val _ready = MutableStateFlow(false)
    val ready: StateFlow<Boolean> = _ready.asStateFlow()

    init {
        viewModelScope.launch {
            withContext(Dispatchers.IO) {
                val seeded = SeedData.seedIfEmpty(database)
                settingsRepository.ensureDefaults()
                if (seeded) mlRepository.trainYieldModel() else mlRepository.modelStatus()
            }
            _ready.value = true
        }
    }
}
