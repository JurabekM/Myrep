package uz.buildcontrol.mobile.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import uz.buildcontrol.mobile.BuildControlApp
import uz.buildcontrol.mobile.core.I18n
import uz.buildcontrol.mobile.core.tr
import uz.buildcontrol.mobile.data.repo.AuthException
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.ui.components.PrimaryButton
import uz.buildcontrol.mobile.ui.theme.BcColors
import uz.buildcontrol.mobile.ui.theme.BcRadius

@Composable
fun LoginScreen(onSignedIn: (CurrentUser) -> Unit, onOpenSettings: () -> Unit) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()

    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var showPassword by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var hasUsers by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        username = container.prefs.rememberedUser.first()
        hasUsers = container.auth.hasUsers()
    }

    fun submit() {
        if (busy) return
        error = ""
        busy = true
        scope.launch {
            try {
                val user = container.auth.login(username, password)
                container.prefs.setRememberedUser(user.username)
                onSignedIn(user)
            } catch (exc: AuthException) {
                error = tr(exc.key)
            } catch (exc: Exception) {
                error = exc.message ?: "error"
            } finally {
                busy = false
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BcColors.Background)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(72.dp))
        Box(
            Modifier
                .size(64.dp)
                .background(BcColors.AccentSoft, RoundedCornerShape(BcRadius.lg)),
            contentAlignment = Alignment.Center,
        ) {
            Text("◆", color = BcColors.Accent, style = MaterialTheme.typography.headlineMedium)
        }
        Spacer(Modifier.height(16.dp))
        Text(
            "BuildControl",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            color = BcColors.Text,
        )
        Text(
            if (I18n.language == "uz") "Qurilish nazorati" else "Construction control",
            style = MaterialTheme.typography.bodyMedium,
            color = BcColors.TextMuted,
        )
        Spacer(Modifier.height(36.dp))

        OutlinedTextField(
            value = username,
            onValueChange = { username = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text(tr("username")) },
            shape = RoundedCornerShape(BcRadius.sm),
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Text,
                imeAction = ImeAction.Next,
            ),
        )
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text(tr("password")) },
            shape = RoundedCornerShape(BcRadius.sm),
            visualTransformation = if (showPassword) VisualTransformation.None
            else PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Password,
                imeAction = ImeAction.Done,
            ),
            trailingIcon = {
                IconButton(onClick = { showPassword = !showPassword }) {
                    Icon(
                        if (showPassword) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                        contentDescription = null,
                        tint = BcColors.TextMuted,
                    )
                }
            },
        )

        if (error.isNotBlank()) {
            Spacer(Modifier.height(10.dp))
            Text(error, color = BcColors.Danger, style = MaterialTheme.typography.bodySmall)
        }
        if (!hasUsers) {
            Spacer(Modifier.height(10.dp))
            Text(
                tr("no_users_hint"),
                color = BcColors.Warning,
                style = MaterialTheme.typography.bodySmall,
            )
        }

        Spacer(Modifier.height(20.dp))
        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            if (busy) {
                CircularProgressIndicator(Modifier.size(28.dp), color = BcColors.Accent)
            } else {
                PrimaryButton(tr("login"), onClick = ::submit, modifier = Modifier.fillMaxWidth())
            }
        }

        Spacer(Modifier.height(16.dp))
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            TextButton(onClick = onOpenSettings) {
                Text(tr("sync"), color = BcColors.Accent)
            }
            TextButton(onClick = {
                val next = if (I18n.language == "uz") "en" else "uz"
                I18n.apply(next)
                scope.launch { container.prefs.setLanguage(next) }
            }) {
                Text(if (I18n.language == "uz") "English" else "O'zbekcha", color = BcColors.TextMuted)
            }
        }
        Spacer(Modifier.height(40.dp))
    }
}
