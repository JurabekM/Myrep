package com.aetherq.messenger.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider

/** Hilt'siz, oddiy lambda orqali ViewModel yaratuvchi factory (manual DI). */
class SimpleViewModelFactory(private val creator: () -> ViewModel) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T = creator() as T
}
