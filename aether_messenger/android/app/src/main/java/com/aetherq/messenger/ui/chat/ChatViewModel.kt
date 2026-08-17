package com.aetherq.messenger.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aetherq.messenger.data.MessengerRepository
import com.aetherq.messenger.data.local.entity.ContactEntity
import com.aetherq.messenger.data.local.entity.MessageEntity
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class ChatViewModel(
    private val repository: MessengerRepository,
    private val contact: ContactEntity,
) : ViewModel() {

    val messages: StateFlow<List<MessageEntity>> =
        repository.observeMessages(contact.userId)
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun send(text: String) {
        if (text.isBlank()) return
        viewModelScope.launch {
            runCatching { repository.sendMessage(contact, text) }
        }
    }
}
