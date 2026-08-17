package com.agrovision.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.UploadFile
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavHostController
import com.agrovision.app.core.Fmt
import com.agrovision.app.data.local.ImportedFileEntity
import com.agrovision.app.data.repo.ImportRepository
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ImportUiState(
    val busy: Boolean = false,
    val message: String? = null,
    val history: List<ImportedFileEntity> = emptyList(),
)

@HiltViewModel
class ImportViewModel @Inject constructor(private val importRepository: ImportRepository) : ViewModel() {
    private val _state = MutableStateFlow(ImportUiState())
    val state: StateFlow<ImportUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(history = importRepository.recentImports())
        }
    }

    fun import(uri: Uri) {
        viewModelScope.launch {
            _state.value = _state.value.copy(busy = true, message = null)
            val summary = importRepository.import(uri)
            _state.value = _state.value.copy(
                busy = false, message = summary, history = importRepository.recentImports(),
            )
        }
    }
}

@Composable
fun ImportScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: ImportViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let { viewModel.import(it) }
    }

    AppScaffold(navController, "Import", onLogout) { padding ->
        ScreenColumn(padding, scrollToTopKey = state.message) {
            ChartCard(
                "Universal import",
                "Qo'llab-quvvatlanadi: CSV/TSV (bozor narxlari va hosildorlik), GeoJSON va KML " +
                    "(dala poligonlari). Fayl turi ustun nomlari bo'yicha avtomatik aniqlanadi.",
            ) {
                Text(
                    "Kutilgan ustunlar:\n" +
                        "• Narx: ekin, narx, sana (ixtiyoriy), bozor (ixtiyoriy)\n" +
                        "• Hosildorlik: dala, ekin, yil, hosildorlik",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Button(
                    onClick = { picker.launch("*/*") },
                    enabled = !state.busy,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    if (state.busy) {
                        CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                    } else {
                        Icon(Icons.Filled.UploadFile, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("Fayl tanlash")
                    }
                }
                state.message?.let { InfoBanner(it) }
            }

            ChartCard("Import tarixi") {
                DataTable(
                    headers = listOf("Fayl", "Sana", "Natija"),
                    rows = state.history.map {
                        listOf(it.filename, Fmt.dateTime(it.uploadedAt), it.summary)
                    },
                    weights = listOf(1.2f, 1f, 2f),
                    maxRows = 15,
                )
            }
        }
    }
}
