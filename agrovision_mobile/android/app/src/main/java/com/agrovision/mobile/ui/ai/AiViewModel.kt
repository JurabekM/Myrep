package com.agrovision.mobile.ui.ai

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.repository.AiRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ChatMessage(val fromUser: Boolean, val text: String)

data class AiUiState(val messages: List<ChatMessage> = emptyList(), val loading: Boolean = false)

val SAMPLE_QUESTIONS = listOf(
    "Jizzaxda bug'doy hosili nima uchun pasaydi?",
    "Kelgusi yil paxta hosildorligi prognozi qanday?",
    "Pomidor narxi qancha?",
    "Samarqand uchun qaysi ekin tavsiya etiladi?",
    "2024-yil Jizzax ob-havosi qanday bo'lgan?",
    "Daromad va foyda qanday?",
)

@HiltViewModel
class AiViewModel @Inject constructor(private val aiRepository: AiRepository) : ViewModel() {
    private val _state = MutableStateFlow(AiUiState())
    val state: StateFlow<AiUiState> = _state.asStateFlow()

    fun ask(question: String) {
        if (question.isBlank()) return
        viewModelScope.launch {
            _state.value = _state.value.copy(messages = _state.value.messages + ChatMessage(true, question), loading = true)
            val answer = aiRepository.ask(question)
            _state.value = _state.value.copy(messages = _state.value.messages + ChatMessage(false, answer.text), loading = false)
        }
    }
}
