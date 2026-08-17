package com.agrovision.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavHostController
import com.agrovision.app.data.repo.AiAnswer
import com.agrovision.app.data.repo.AiRepository
import com.agrovision.app.ui.common.DataTable
import com.agrovision.app.ui.common.SuggestionChips
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ChatMessage(val fromUser: Boolean, val text: String, val answer: AiAnswer? = null)

@HiltViewModel
class AiViewModel @Inject constructor(private val aiRepository: AiRepository) : ViewModel() {
    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages.asStateFlow()

    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading.asStateFlow()

    fun ask(question: String) {
        val trimmed = question.trim()
        if (trimmed.isEmpty() || _loading.value) return
        viewModelScope.launch {
            _messages.value = _messages.value + ChatMessage(true, trimmed)
            _loading.value = true
            val answer = aiRepository.ask(trimmed)
            _messages.value = _messages.value + ChatMessage(false, answer.text, answer)
            _loading.value = false
        }
    }
}

@Composable
fun AiScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: AiViewModel = hiltViewModel(),
) {
    val messages by viewModel.messages.collectAsState()
    val loading by viewModel.loading.collectAsState()
    var input by remember { mutableStateOf("") }
    val listState = rememberLazyListState()

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    AppScaffold(navController, "AI Yordamchi", onLogout) { padding ->
        Column(Modifier.padding(padding).fillMaxSize().padding(horizontal = 16.dp)) {
            Text(
                "Savolni oddiy tilda yozing — yordamchi qurilmadagi barcha ma'lumotlarni tahlil qilib, " +
                    "dalillarga asoslangan javob beradi. Internet talab qilinmaydi.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(vertical = 8.dp),
            )
            SuggestionChips(AiRepository.SAMPLE_QUESTIONS) { viewModel.ask(it) }

            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(10.dp),
                contentPadding = PaddingValues(vertical = 12.dp),
            ) {
                items(messages) { message ->
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = if (message.fromUser) Arrangement.End else Arrangement.Start,
                    ) {
                        Card(
                            colors = CardDefaults.cardColors(
                                containerColor = if (message.fromUser) {
                                    MaterialTheme.colorScheme.primary
                                } else {
                                    MaterialTheme.colorScheme.surfaceVariant
                                },
                            ),
                            modifier = Modifier.widthIn(max = 340.dp),
                        ) {
                            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                if (!message.fromUser) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(
                                            Icons.Filled.SmartToy, contentDescription = null,
                                            modifier = Modifier.size(15.dp),
                                            tint = MaterialTheme.colorScheme.primary,
                                        )
                                        Spacer(Modifier.width(5.dp))
                                        Text(
                                            "AgroAI",
                                            style = MaterialTheme.typography.labelMedium,
                                            fontWeight = FontWeight.Bold,
                                            color = MaterialTheme.colorScheme.primary,
                                        )
                                    }
                                }
                                Text(
                                    message.text,
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = if (message.fromUser) {
                                        MaterialTheme.colorScheme.onPrimary
                                    } else {
                                        MaterialTheme.colorScheme.onSurface
                                    },
                                )
                                message.answer?.takeIf { it.tableRows.isNotEmpty() }?.let { answer ->
                                    HorizontalDivider()
                                    DataTable(
                                        headers = answer.tableHeaders,
                                        rows = answer.tableRows,
                                        maxRows = 8,
                                    )
                                }
                            }
                        }
                    }
                }
                if (loading) {
                    item {
                        Row(Modifier.fillMaxWidth().padding(8.dp)) {
                            CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                        }
                    }
                }
            }

            Row(
                Modifier.fillMaxWidth().padding(bottom = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    value = input,
                    onValueChange = { input = it },
                    placeholder = { Text("Savolingizni yozing…") },
                    maxLines = 3,
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(8.dp))
                FilledIconButton(
                    onClick = { viewModel.ask(input); input = "" },
                    enabled = input.isNotBlank() && !loading,
                ) {
                    Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Yuborish")
                }
            }
        }
    }
}
