package com.smartmoliya.app.feature.auth.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.smartmoliya.app.core.security.BiometricAuthenticator

enum class PinScreenMode { SETUP, UNLOCK }

private const val PIN_LENGTH = 4

@Composable
fun PinScreen(
    mode: PinScreenMode,
    biometricAuthenticator: BiometricAuthenticator?,
    onUnlocked: () -> Unit,
    viewModel: PinViewModel = hiltViewModel()
) {
    var enteredPin by remember { mutableStateOf("") }
    var firstPinForConfirm by remember { mutableStateOf<String?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    fun onDigit(digit: String) {
        if (enteredPin.length >= PIN_LENGTH) return
        enteredPin += digit
        if (enteredPin.length == PIN_LENGTH) {
            when (mode) {
                PinScreenMode.UNLOCK -> {
                    if (viewModel.verifyPin(enteredPin)) {
                        onUnlocked()
                    } else {
                        errorMessage = "PIN noto'g'ri"
                        enteredPin = ""
                    }
                }
                PinScreenMode.SETUP -> {
                    val first = firstPinForConfirm
                    if (first == null) {
                        firstPinForConfirm = enteredPin
                        enteredPin = ""
                    } else if (first == enteredPin) {
                        viewModel.setPin(enteredPin)
                        onUnlocked()
                    } else {
                        errorMessage = "PIN mos kelmadi, qaytadan urinib ko'ring"
                        firstPinForConfirm = null
                        enteredPin = ""
                    }
                }
            }
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = when (mode) {
                PinScreenMode.UNLOCK -> "PIN kodni kiriting"
                PinScreenMode.SETUP -> if (firstPinForConfirm == null) "Yangi PIN o'rnating" else "PIN'ni tasdiqlang"
            },
            style = MaterialTheme.typography.titleLarge
        )

        Row(modifier = Modifier.padding(vertical = 24.dp)) {
            repeat(PIN_LENGTH) { index ->
                Surface(
                    shape = CircleShape,
                    color = if (index < enteredPin.length) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline,
                    modifier = Modifier.size(16.dp).padding(4.dp)
                ) {}
            }
        }

        if (errorMessage != null) {
            Text(text = errorMessage!!, color = MaterialTheme.colorScheme.error)
        }

        PinKeypad(onDigit = ::onDigit, onBackspace = { enteredPin = enteredPin.dropLast(1) })

        if (mode == PinScreenMode.UNLOCK && biometricAuthenticator?.isAvailable() == true) {
            OutlinedButton(
                onClick = {
                    biometricAuthenticator.authenticate(
                        onSuccess = onUnlocked,
                        onError = { errorMessage = it }
                    )
                },
                modifier = Modifier.padding(top = 16.dp)
            ) {
                Text("Biometrik orqali kirish")
            }
        }
    }
}

@Composable
private fun PinKeypad(onDigit: (String) -> Unit, onBackspace: () -> Unit) {
    val rows = listOf(
        listOf("1", "2", "3"),
        listOf("4", "5", "6"),
        listOf("7", "8", "9"),
        listOf("", "0", "<")
    )
    Column {
        rows.forEach { row ->
            Row {
                row.forEach { key ->
                    when (key) {
                        "" -> androidx.compose.foundation.layout.Box(
                            modifier = Modifier.padding(6.dp).size(72.dp)
                        ) {}
                        "<" -> KeypadButton(label = "⌫", onClick = onBackspace)
                        else -> KeypadButton(label = key, onClick = { onDigit(key) })
                    }
                }
            }
        }
    }
}

@Composable
private fun KeypadButton(label: String, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = CircleShape,
        color = MaterialTheme.colorScheme.surfaceVariant,
        modifier = Modifier.padding(6.dp).size(72.dp)
    ) {
        androidx.compose.foundation.layout.Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier.size(72.dp)
        ) {
            Text(
                text = label,
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}
