package com.uzerp.mobile.ui.sales

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.UzErpException
import com.uzerp.mobile.data.repository.AuthRepository
import com.uzerp.mobile.data.repository.SaleItemInput
import com.uzerp.mobile.data.repository.SalesDocDetail
import com.uzerp.mobile.data.repository.SalesRepository
import com.uzerp.mobile.ui.common.ErrorBanner
import com.uzerp.mobile.ui.common.LoadingState
import com.uzerp.mobile.ui.common.ScreenScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import java.math.BigDecimal
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class SalesReturnUiState(
    val detail: SalesDocDetail? = null,
    val returnQuantities: Map<Long, String> = emptyMap(),
    val isLoading: Boolean = true,
    val isSaving: Boolean = false,
    val error: String? = null,
    val savedReturnId: Long? = null,
)

@HiltViewModel
class SalesReturnViewModel @Inject constructor(
    private val repository: SalesRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SalesReturnUiState())
    val state: StateFlow<SalesReturnUiState> = _state.asStateFlow()
    private var parentId: Long = 0

    fun load(id: Long) {
        parentId = id
        viewModelScope.launch {
            try {
                _state.value = SalesReturnUiState(detail = repository.getDoc(id), isLoading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun setQuantity(productId: Long, value: String) {
        _state.value = _state.value.copy(returnQuantities = _state.value.returnQuantities + (productId to value))
    }

    fun submit() {
        val quantities = _state.value.returnQuantities
        val items = quantities.mapNotNull { (pid, qtyStr) ->
            qtyStr.toBigDecimalOrNull()?.takeIf { it.signum() > 0 }?.let { SaleItemInput(pid, it) }
        }
        if (items.isEmpty()) {
            _state.value = _state.value.copy(error = "Qaytarish miqdorini kiriting.")
            return
        }
        _state.value = _state.value.copy(isSaving = true, error = null)
        viewModelScope.launch {
            try {
                val userId = authRepository.currentUser.value?.id
                val returnId = repository.createReturn(parentId, items, userId)
                _state.value = _state.value.copy(isSaving = false, savedReturnId = returnId)
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(isSaving = false, error = e.message)
            }
        }
    }
}

@Composable
fun SalesReturnScreen(docId: Long, onBack: () -> Unit, onSaved: (Long) -> Unit, viewModel: SalesReturnViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(docId) { viewModel.load(docId) }
    LaunchedEffect(state.savedReturnId) { state.savedReturnId?.let(onSaved) }

    ScreenScaffold(title = "Qaytarish", onBack = onBack) { padding ->
        if (state.isLoading || state.detail == null) {
            LoadingState()
            return@ScreenScaffold
        }
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            state.error?.let { ErrorBanner(it) }
            Text("Sotilgan pozitsiyalar — qaytarish miqdorini kiriting:", color = MaterialTheme.colorScheme.onSurfaceVariant)
            LazyColumn(modifier = Modifier.weight(1f).padding(top = 8.dp)) {
                items(state.detail!!.items, key = { it.id }) { item ->
                    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                        Text("${item.productName} (sotilgan: ${item.quantity} ${item.unit})", modifier = Modifier.weight(1f))
                        OutlinedTextField(
                            value = state.returnQuantities[item.productId] ?: "",
                            onValueChange = { viewModel.setQuantity(item.productId, it) },
                            modifier = Modifier.width(90.dp),
                            singleLine = true,
                            placeholder = { Text("0") },
                        )
                    }
                }
            }
            Button(onClick = viewModel::submit, enabled = !state.isSaving, modifier = Modifier.fillMaxWidth().padding(top = 12.dp)) {
                Text("Qaytarishni rasmiylashtirish")
            }
        }
    }
}
