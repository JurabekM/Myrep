package com.agrovision.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Agriculture
import androidx.compose.material.icons.filled.DatasetLinked
import androidx.compose.material.icons.filled.EditNote
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.app.data.repo.BootstrapRepository
import com.agrovision.app.ui.common.InfoBanner
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

enum class BootstrapPhase { LOADING, CHOOSE_DATA, SEEDING, READY }

data class BootstrapUiState(
    val phase: BootstrapPhase = BootstrapPhase.LOADING,
    val step: String = "",
    val percent: Int = 0,
)

@HiltViewModel
class BootstrapViewModel @Inject constructor(
    private val bootstrapRepository: BootstrapRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(BootstrapUiState())
    val state: StateFlow<BootstrapUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            val fresh = bootstrapRepository.prepare()
            val hasDemo = bootstrapRepository.hasDemoData()
            _state.value = if (fresh && !hasDemo) {
                BootstrapUiState(BootstrapPhase.CHOOSE_DATA)
            } else {
                bootstrapRepository.ensureModels()
                BootstrapUiState(BootstrapPhase.READY)
            }
        }
    }

    fun loadDemoData() {
        viewModelScope.launch {
            _state.value = BootstrapUiState(BootstrapPhase.SEEDING, "Boshlanmoqda", 0)
            bootstrapRepository.loadDemoData { step, percent ->
                _state.value = BootstrapUiState(BootstrapPhase.SEEDING, step, percent)
            }
            _state.value = BootstrapUiState(BootstrapPhase.READY)
        }
    }

    fun startEmpty() {
        _state.value = BootstrapUiState(BootstrapPhase.READY)
    }
}

/** Birinchi ishga tushirish ekrani: yuklanish → ma'lumot tanlovi → tayyor. */
@Composable
fun BootstrapScreen(state: BootstrapUiState, onLoadDemo: () -> Unit, onStartEmpty: () -> Unit) {
    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            Modifier.fillMaxSize().padding(28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Box(
                Modifier.size(76.dp).background(MaterialTheme.colorScheme.primary, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Filled.Agriculture, contentDescription = null,
                    tint = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(42.dp),
                )
            }
            Spacer(Modifier.height(14.dp))
            Text("AgroVision", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(
                "Qishloq xo'jaligi analitik platformasi",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(28.dp))

            when (state.phase) {
                BootstrapPhase.LOADING -> {
                    CircularProgressIndicator()
                    Spacer(Modifier.height(10.dp))
                    Text("Baza tayyorlanmoqda…", style = MaterialTheme.typography.bodySmall)
                }

                BootstrapPhase.SEEDING -> {
                    LinearProgressIndicator(
                        progress = { state.percent / 100f },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Spacer(Modifier.height(10.dp))
                    Text("${state.step}… ${state.percent}%", style = MaterialTheme.typography.bodySmall)
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "Namuna to'plami ~70 ming yozuvdan iborat — bir necha soniya oladi.",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }

                BootstrapPhase.CHOOSE_DATA -> {
                    Text(
                        "Ishni qanday boshlaymiz?",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Spacer(Modifier.height(16.dp))
                    ElevatedCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Filled.DatasetLinked, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                Spacer(Modifier.width(8.dp))
                                Text("Namuna ma'lumotlar bilan", fontWeight = FontWeight.SemiBold)
                            }
                            Text(
                                "Desktop versiyasidagi kabi to'liq test to'plami: 13 viloyat, 60 fermer, " +
                                    "140 dala, 23 ekin, 5 yillik hosildorlik, ob-havo, narx, moliya va NDVI. " +
                                    "Barcha modullarni darhol sinab ko'rish uchun.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            Button(onClick = onLoadDemo, modifier = Modifier.fillMaxWidth()) {
                                Text("Namuna ma'lumotlarni yuklash")
                            }
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                    ElevatedCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Filled.EditNote, contentDescription = null, tint = MaterialTheme.colorScheme.secondary)
                                Spacer(Modifier.width(8.dp))
                                Text("Bo'sh boshlash", fontWeight = FontWeight.SemiBold)
                            }
                            Text(
                                "Faqat ma'lumotnoma (viloyat/tuman va ekin turlari) qoladi. Fermer, " +
                                    "xo'jalik, dala va boshqa yozuvlarni \"Ma'lumotlar\" bo'limidan o'zingiz kiritasiz.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            OutlinedButton(onClick = onStartEmpty, modifier = Modifier.fillMaxWidth()) {
                                Text("Bo'sh boshlash")
                            }
                        }
                    }
                    Spacer(Modifier.height(14.dp))
                    InfoBanner("Bu tanlovni keyinroq Administrator bo'limidan ham o'zgartirish mumkin.")
                }

                BootstrapPhase.READY -> Unit
            }
        }
    }
}
