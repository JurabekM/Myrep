package com.aetherq.messenger.ui.contacts

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aetherq.messenger.crypto.ContactCard
import com.aetherq.messenger.data.MessengerRepository
import com.aetherq.messenger.data.local.entity.ContactEntity
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class ContactsViewModel(private val repository: MessengerRepository) : ViewModel() {

    val contacts: StateFlow<List<ContactEntity>> =
        repository.observeContacts().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    init {
        viewModelScope.launch {
            runCatching { repository.connectMqtt() }
        }
    }

    fun addContact(card: ContactCard, displayName: String) {
        viewModelScope.launch { repository.addContact(card, displayName) }
    }
}
