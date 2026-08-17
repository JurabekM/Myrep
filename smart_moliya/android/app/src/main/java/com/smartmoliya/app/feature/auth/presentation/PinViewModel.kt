package com.smartmoliya.app.feature.auth.presentation

import androidx.lifecycle.ViewModel
import com.smartmoliya.app.core.security.PinManager
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class PinViewModel @Inject constructor(
    private val pinManager: PinManager
) : ViewModel() {

    fun isPinConfigured(): Boolean = pinManager.isPinSet()

    fun setPin(pin: String) = pinManager.setPin(pin)

    fun verifyPin(pin: String): Boolean = pinManager.verifyPin(pin)
}
