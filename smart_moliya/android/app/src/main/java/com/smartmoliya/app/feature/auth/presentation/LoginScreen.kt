package com.smartmoliya.app.feature.auth.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.smartmoliya.app.core.security.GoogleSignInHelper
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(
    onLoginSuccess: () -> Unit,
    onNavigateToRegister: () -> Unit,
    onNavigateToOtp: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel()
) {
    val state by viewModel.uiState.collectAsState()
    var phone by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }

    val context = LocalContext.current
    val googleSignInHelper = remember { GoogleSignInHelper(context) }
    val coroutineScope = rememberCoroutineScope()

    LaunchedEffect(state.loginSucceeded) {
        if (state.loginSucceeded) onLoginSuccess()
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(text = "Smart Moliya", style = MaterialTheme.typography.titleLarge)
        Text(text = "Hisobingizga kiring")

        OutlinedTextField(
            value = phone,
            onValueChange = { phone = it },
            label = { Text("Telefon raqami") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
            modifier = Modifier.fillMaxWidth().padding(top = 16.dp)
        )
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Parol") },
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
        )

        if (state.errorMessage != null) {
            Text(text = state.errorMessage!!, color = MaterialTheme.colorScheme.error)
        }

        Button(
            onClick = { viewModel.login(phone, password) },
            enabled = !state.isLoading && phone.isNotBlank() && password.isNotBlank(),
            modifier = Modifier.fillMaxWidth().padding(top = 16.dp)
        ) {
            if (state.isLoading) {
                CircularProgressIndicator(modifier = Modifier.padding(4.dp))
            } else {
                Text("Kirish")
            }
        }

        OutlinedButton(
            onClick = onNavigateToOtp,
            enabled = !state.isLoading,
            modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
        ) {
            Text("SMS kod bilan kirish")
        }

        if (googleSignInHelper.isConfigured()) {
            OutlinedButton(
                onClick = {
                    coroutineScope.launch {
                        runCatching { googleSignInHelper.getIdToken() }
                            .onSuccess { idToken -> viewModel.loginWithGoogle(idToken) }
                            .onFailure { viewModel.reportGoogleSignInError(it.message) }
                    }
                },
                enabled = !state.isLoading,
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
            ) {
                Text("Google bilan kirish")
            }
        }

        TextButton(onClick = onNavigateToRegister) {
            Text("Hisobingiz yo'qmi? Ro'yxatdan o'ting")
        }
    }
}
