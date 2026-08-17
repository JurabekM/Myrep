package com.uzerp.mobile.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.hilt.navigation.compose.hiltViewModel
import com.uzerp.mobile.ui.theme.UzAccent
import com.uzerp.mobile.ui.theme.UzBg
import com.uzerp.mobile.ui.theme.UzGradEnd
import com.uzerp.mobile.ui.theme.UzGradMid
import com.uzerp.mobile.ui.theme.UzGradStart
import com.uzerp.mobile.ui.theme.UzGreen
import com.uzerp.mobile.ui.theme.UzMuted

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LoginScreen(viewModel: AuthViewModel = hiltViewModel()) {
    val bootstrapState by viewModel.bootstrapState.collectAsState()
    val uiState by viewModel.uiState.collectAsState()
    var passwordVisible by remember { mutableStateOf(false) }
    var showAdminPasswordDialog by remember { mutableStateOf(false) }
    var adminPassword by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(bootstrapState) {
        val state = bootstrapState
        if (state is BootstrapState.Ready && state.generatedAdminPassword != null) {
            adminPassword = state.generatedAdminPassword
            showAdminPasswordDialog = true
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    0f to UzGradStart.copy(alpha = 0.35f),
                    0.45f to UzBg,
                    1f to UzGradEnd.copy(alpha = 0.25f),
                ),
            ),
        contentAlignment = Alignment.Center,
    ) {
        if (bootstrapState is BootstrapState.Loading) {
            CircularProgressIndicator(color = UzAccent)
            return@Box
        }

        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            // Logo — gradientli dumaloq belgi
            Box(
                modifier = Modifier
                    .size(84.dp)
                    .background(
                        Brush.linearGradient(listOf(UzGradStart, UzGradMid, UzGradEnd)),
                        RoundedCornerShape(26.dp),
                    ),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Filled.AccountBalance,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(42.dp),
                )
            }
            Spacer(Modifier.height(18.dp))
            Text(
                "UzERP",
                style = MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Text(
                "Enterprise Resource Planning",
                style = MaterialTheme.typography.bodyMedium,
                color = UzMuted,
            )
            Spacer(Modifier.height(24.dp))

        Card(
            modifier = Modifier.widthIn(max = 380.dp).padding(horizontal = 24.dp),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        ) {
            Column(modifier = Modifier.padding(28.dp)) {

                OutlinedTextField(
                    value = uiState.username,
                    onValueChange = viewModel::onUsernameChange,
                    label = { Text("Login") },
                    leadingIcon = { Icon(Icons.Filled.Person, null) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = uzTextFieldColors(),
                )
                Spacer(Modifier.height(12.dp))

                OutlinedTextField(
                    value = uiState.password,
                    onValueChange = viewModel::onPasswordChange,
                    label = { Text("Parol") },
                    leadingIcon = { Icon(Icons.Filled.Lock, null) },
                    trailingIcon = {
                        IconButton(onClick = { passwordVisible = !passwordVisible }) {
                            Icon(
                                if (passwordVisible) Icons.Filled.VisibilityOff
                                else Icons.Filled.Visibility,
                                null,
                            )
                        }
                    },
                    visualTransformation = if (passwordVisible) VisualTransformation.None
                    else PasswordVisualTransformation(),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = uzTextFieldColors(),
                )

                uiState.error?.let { error ->
                    Spacer(Modifier.height(10.dp))
                    Text(error, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
                }

                Spacer(Modifier.height(20.dp))
                Button(
                    onClick = viewModel::login,
                    enabled = !uiState.isLoading,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    if (uiState.isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.height(18.dp).widthIn(max = 18.dp),
                            color = Color.White,
                            strokeWidth = 2.dp,
                        )
                    } else {
                        Text("Kirish")
                    }
                }

                Spacer(Modifier.height(14.dp))
                Text(
                    "To'liq avtonom — tarmoqqa ulanmaydi. Barcha ma'lumotlar " +
                        "shu qurilmada saqlanadi.",
                    style = MaterialTheme.typography.labelSmall,
                    color = UzMuted,
                )
            }
        }
        }
    }

    if (showAdminPasswordDialog && adminPassword != null) {
        AdminPasswordDialog(
            password = adminPassword!!,
            onDismiss = { showAdminPasswordDialog = false },
        )
    }
}

@Composable
private fun AdminPasswordDialog(password: String, onDismiss: () -> Unit) {
    val clipboard = LocalClipboardManager.current
    AlertDialog(
        onDismissRequest = {},
        title = { Text("Administrator hisobi yaratildi", fontWeight = FontWeight.Bold) },
        text = {
            Column {
                Text(
                    "Birinchi ishga tushirish — quyidagi ma'lumotlar bilan kiring va " +
                        "parolni albatta saqlab qo'ying (qayta ko'rsatilmaydi):",
                    color = UzMuted,
                )
                Spacer(Modifier.height(12.dp))
                Text("Login:  admin", fontWeight = FontWeight.SemiBold)
                SelectionContainer {
                    Text(
                        "Parol:  $password",
                        fontWeight = FontWeight.SemiBold,
                        color = UzGreen,
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                clipboard.setText(AnnotatedString(password))
            }) {
                Icon(Icons.Filled.ContentCopy, null, modifier = Modifier.height(16.dp))
                Text(" Nusxalash")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Tushunarli, saqladim") }
        },
    )
}

@Composable
private fun uzTextFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = UzAccent,
    unfocusedBorderColor = MaterialTheme.colorScheme.outline,
    focusedLabelColor = UzAccent,
)
