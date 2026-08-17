package com.agrovision.mobile.ui.login

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Agriculture
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.agrovision.mobile.ui.nav.Routes

@Composable
fun LoginScreen(navController: NavHostController, viewModel: LoginViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    LaunchedEffect(state.success) {
        if (state.success) {
            navController.navigate(Routes.DASHBOARD) { popUpTo(Routes.LOGIN) { inclusive = true } }
        }
    }

    Box(Modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(28.dp).fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(Icons.Filled.Agriculture, contentDescription = null, modifier = Modifier.size(56.dp), tint = MaterialTheme.colorScheme.primary)
                Text("AgroVision", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.padding(top = 8.dp))
                Text("Qishloq xo'jaligi analitik platformasi", style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(bottom = 20.dp))

                OutlinedTextField(
                    value = state.username, onValueChange = viewModel::onUsernameChange,
                    label = { Text("Login") }, singleLine = true, modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(
                    value = state.password, onValueChange = viewModel::onPasswordChange,
                    label = { Text("Parol") }, singleLine = true, visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                )
                state.error?.let {
                    Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 8.dp), style = MaterialTheme.typography.bodySmall)
                }
                Spacer(Modifier.height(16.dp))
                Button(onClick = viewModel::login, enabled = !state.loading, modifier = Modifier.fillMaxWidth()) {
                    if (state.loading) CircularProgressIndicator(modifier = Modifier.size(18.dp), color = MaterialTheme.colorScheme.onPrimary)
                    else Text("KIRISH")
                }

                Spacer(Modifier.height(16.dp))
                HorizontalDivider()
                Spacer(Modifier.height(8.dp))
                Text("Demo hisoblar:", style = MaterialTheme.typography.labelMedium)
                Text("admin / admin123 — Administrator", style = MaterialTheme.typography.bodySmall)
                Text("menejer / manager123 — Menejer", style = MaterialTheme.typography.bodySmall)
                Text("kuzatuvchi / viewer123 — Kuzatuvchi", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
