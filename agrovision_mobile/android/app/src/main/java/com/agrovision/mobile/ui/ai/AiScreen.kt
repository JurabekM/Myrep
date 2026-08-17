package com.agrovision.mobile.ui.ai

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.agrovision.mobile.ui.common.ChipRow
import com.agrovision.mobile.ui.nav.AppScaffold
import com.agrovision.mobile.ui.nav.logoutAndReturn

@Composable
fun AiScreen(navController: NavHostController, viewModel: AiViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var input by remember { mutableStateOf("") }

    AppScaffold(navController, "AI Yordamchi (offlayn)", onLogout = { navController.logoutAndReturn() }) { padding ->
        Column(Modifier.padding(padding).padding(16.dp).fillMaxSize()) {
            Text(
                "Savolni oddiy tilda yozing — yordamchi qurilmadagi barcha ma'lumotlarni tahlil qilib javob beradi. Internet talab qilinmaydi.",
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(8.dp))
            ChipRow(SAMPLE_QUESTIONS) { viewModel.ask(it) }
            Spacer(Modifier.height(8.dp))

            LazyColumn(Modifier.weight(1f).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(state.messages) { message ->
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = if (message.fromUser) Arrangement.End else Arrangement.Start) {
                        ElevatedCard {
                            Column(Modifier.padding(10.dp).widthIn(max = 320.dp)) {
                                if (!message.fromUser) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Filled.SmartToy, contentDescription = null, modifier = Modifier.size(16.dp))
                                        Spacer(Modifier.width(4.dp))
                                        Text("AgroAI", style = MaterialTheme.typography.labelSmall)
                                    }
                                }
                                Text(message.text, style = MaterialTheme.typography.bodyMedium)
                            }
                        }
                    }
                }
                if (state.loading) {
                    item { CircularProgressIndicator(modifier = Modifier.size(20.dp)) }
                }
            }

            Row(Modifier.fillMaxWidth().padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = input, onValueChange = { input = it },
                    placeholder = { Text("Savolingizni yozing...") },
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(8.dp))
                IconButton(onClick = { viewModel.ask(input); input = "" }) {
                    Icon(Icons.Filled.Send, contentDescription = "Yuborish")
                }
            }
        }
    }
}
