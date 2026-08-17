package com.smartmoliya.app.feature.familymode.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.smartmoliya.app.core.network.dto.TaskRewardDto

@Composable
fun FamilyScreen(viewModel: FamilyViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    when {
        com.smartmoliya.app.BuildConfig.OFFLINE_MODE -> LocalTasksContent(state = state, viewModel = viewModel)
        state.groupWithMembers == null -> NoGroupContent(
            message = state.message,
            onCreate = { name -> viewModel.createGroup(name) },
            onJoin = { groupId -> viewModel.joinGroup(groupId) }
        )
        else -> GroupContent(state = state, viewModel = viewModel)
    }
}

/** Offline rejim: bir qurilmalik vazifa/mukofot tizimi (Family Mode'ning lokal varianti). */
@Composable
private fun LocalTasksContent(state: FamilyUiState, viewModel: FamilyViewModel) {
    var taskTitle by remember { mutableStateOf("") }
    var taskReward by remember { mutableStateOf("") }
    var selectedWalletId by remember { mutableStateOf<String?>(null) }
    var walletMenuExpanded by remember { mutableStateOf(false) }

    val selectedWallet = state.wallets.find { it.id == selectedWalletId } ?: state.wallets.firstOrNull()

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(text = "Vazifalar va mukofotlar", style = MaterialTheme.typography.titleLarge)
            Text(
                text = "Vazifa bajarilib tasdiqlanganda mukofot tanlangan hamyonga daromad sifatida tushadi",
                style = MaterialTheme.typography.labelSmall
            )
            state.message?.let { Text(text = it, style = MaterialTheme.typography.labelSmall) }
        }

        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(text = "Yangi vazifa", fontWeight = FontWeight.SemiBold)
                    OutlinedTextField(
                        value = taskTitle,
                        onValueChange = { taskTitle = it },
                        label = { Text("Vazifa nomi") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = taskReward,
                        onValueChange = { taskReward = it.filter { c -> c.isDigit() } },
                        label = { Text("Mukofot (so'm)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    Button(
                        onClick = {
                            val reward = taskReward.toDoubleOrNull()
                            if (reward != null && reward > 0 && taskTitle.isNotBlank()) {
                                viewModel.createLocalTask(taskTitle, reward)
                                taskTitle = ""
                                taskReward = ""
                            }
                        },
                        enabled = taskTitle.isNotBlank() && taskReward.isNotBlank(),
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
                    ) { Text("Vazifa yaratish") }
                }
            }
        }

        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(text = "Mukofot tushadigan hamyon", fontWeight = FontWeight.SemiBold)
                    TextButton(onClick = { walletMenuExpanded = true }) {
                        Text(selectedWallet?.name ?: "Hamyon mavjud emas")
                    }
                    DropdownMenu(
                        expanded = walletMenuExpanded,
                        onDismissRequest = { walletMenuExpanded = false }
                    ) {
                        state.wallets.forEach { wallet ->
                            DropdownMenuItem(
                                text = { Text(wallet.name) },
                                onClick = { selectedWalletId = wallet.id; walletMenuExpanded = false }
                            )
                        }
                    }
                }
            }
        }

        item { Text(text = "Vazifalar", fontWeight = FontWeight.SemiBold) }
        if (state.localTasks.isEmpty()) {
            item { Text(text = "Hozircha vazifalar yo'q") }
        } else {
            items(state.localTasks, key = { it.id }) { task ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(text = task.title, fontWeight = FontWeight.Medium)
                            Text(text = "${task.rewardAmount.toLong()} so'm")
                        }
                        Text(text = taskStatusLabel(task.status), style = MaterialTheme.typography.labelSmall)
                        Row {
                            when (task.status) {
                                "PENDING" -> TextButton(onClick = { viewModel.markLocalTaskDone(task.id) }) {
                                    Text("Bajarildi deb belgilash")
                                }
                                "DONE" -> TextButton(
                                    onClick = {
                                        selectedWallet?.let { viewModel.approveLocalTask(task.id, it.id) }
                                    }
                                ) { Text("Tasdiqlash va to'lash") }
                            }
                            TextButton(onClick = { viewModel.deleteLocalTask(task.id) }) { Text("O'chirish") }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun NoGroupContent(message: String?, onCreate: (String) -> Unit, onJoin: (String) -> Unit) {
    var groupName by remember { mutableStateOf("") }
    var joinId by remember { mutableStateOf("") }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center
    ) {
        Text(text = "Oila rejimi", style = MaterialTheme.typography.titleLarge)
        Text(text = "Guruh yarating yoki mavjud guruhga qo'shiling")

        OutlinedTextField(
            value = groupName,
            onValueChange = { groupName = it },
            label = { Text("Yangi guruh nomi") },
            modifier = Modifier.fillMaxWidth().padding(top = 16.dp)
        )
        Button(
            onClick = { if (groupName.isNotBlank()) onCreate(groupName) },
            enabled = groupName.isNotBlank(),
            modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
        ) { Text("Guruh yaratish") }

        OutlinedTextField(
            value = joinId,
            onValueChange = { joinId = it },
            label = { Text("Guruh ID (taklif orqali)") },
            modifier = Modifier.fillMaxWidth().padding(top = 24.dp)
        )
        Button(
            onClick = { if (joinId.isNotBlank()) onJoin(joinId.trim()) },
            enabled = joinId.isNotBlank(),
            modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
        ) { Text("Guruhga qo'shilish") }

        message?.let { Text(text = it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 8.dp)) }
    }
}

@Composable
private fun GroupContent(state: FamilyUiState, viewModel: FamilyViewModel) {
    val group = state.groupWithMembers ?: return

    var allowanceWalletId by remember { mutableStateOf("") }
    var allowanceAmount by remember { mutableStateOf("") }
    var taskUserId by remember { mutableStateOf("") }
    var taskTitle by remember { mutableStateOf("") }
    var taskReward by remember { mutableStateOf("") }
    var approveWalletId by remember { mutableStateOf("") }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(text = "Oila: ${group.group.name}", style = MaterialTheme.typography.titleLarge)
            Text(text = "Guruh ID (taklif uchun): ${group.group.id}", style = MaterialTheme.typography.labelSmall)
            state.message?.let { Text(text = it, style = MaterialTheme.typography.labelSmall) }
        }

        item { Text(text = "A'zolar", fontWeight = FontWeight.SemiBold) }
        items(group.members, key = { it.id }) { member ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(text = member.full_name ?: member.phone ?: "Foydalanuvchi")
                    Text(text = "ID: ${member.id}", style = MaterialTheme.typography.labelSmall)
                }
            }
        }

        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(text = "Pocket money yuborish", fontWeight = FontWeight.SemiBold)
                    OutlinedTextField(
                        value = allowanceWalletId,
                        onValueChange = { allowanceWalletId = it },
                        label = { Text("Bola hamyoni ID") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = allowanceAmount,
                        onValueChange = { allowanceAmount = it.filter { c -> c.isDigit() } },
                        label = { Text("Summa (so'm)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    Button(
                        onClick = {
                            val amount = allowanceAmount.toDoubleOrNull()
                            if (amount != null && amount > 0 && allowanceWalletId.isNotBlank()) {
                                viewModel.sendAllowance(allowanceWalletId.trim(), amount, null)
                                allowanceAmount = ""
                            }
                        },
                        enabled = allowanceWalletId.isNotBlank() && allowanceAmount.isNotBlank(),
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
                    ) { Text("Yuborish") }
                }
            }
        }

        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(text = "Vazifa yaratish (mukofot bilan)", fontWeight = FontWeight.SemiBold)
                    OutlinedTextField(
                        value = taskUserId,
                        onValueChange = { taskUserId = it },
                        label = { Text("Kimga (a'zo ID)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = taskTitle,
                        onValueChange = { taskTitle = it },
                        label = { Text("Vazifa nomi") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = taskReward,
                        onValueChange = { taskReward = it.filter { c -> c.isDigit() } },
                        label = { Text("Mukofot (so'm)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    Button(
                        onClick = {
                            val reward = taskReward.toDoubleOrNull()
                            if (reward != null && reward > 0 && taskUserId.isNotBlank() && taskTitle.isNotBlank()) {
                                viewModel.createTask(taskUserId.trim(), taskTitle, reward)
                                taskTitle = ""
                                taskReward = ""
                            }
                        },
                        enabled = taskUserId.isNotBlank() && taskTitle.isNotBlank() && taskReward.isNotBlank(),
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
                    ) { Text("Vazifa yaratish") }
                }
            }
        }

        item { Text(text = "Vazifalar", fontWeight = FontWeight.SemiBold) }
        if (state.tasks.isEmpty()) {
            item { Text(text = "Hozircha vazifalar yo'q") }
        } else {
            items(state.tasks, key = { it.id }) { task ->
                TaskCard(
                    task = task,
                    approveWalletId = approveWalletId,
                    onApproveWalletIdChange = { approveWalletId = it },
                    onDone = { viewModel.markTaskDone(task.id) },
                    onApprove = { walletId -> viewModel.approveTask(task.id, walletId) }
                )
            }
        }
    }
}

@Composable
private fun TaskCard(
    task: TaskRewardDto,
    approveWalletId: String,
    onApproveWalletIdChange: (String) -> Unit,
    onDone: () -> Unit,
    onApprove: (String) -> Unit
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(text = task.title, fontWeight = FontWeight.Medium)
                Text(text = "${task.reward_amount.toLong()} so'm")
            }
            Text(text = taskStatusLabel(task.status), style = MaterialTheme.typography.labelSmall)

            when (task.status.lowercase()) {
                "pending" -> TextButton(onClick = onDone) { Text("Bajarildi deb belgilash") }
                "done" -> {
                    OutlinedTextField(
                        value = approveWalletId,
                        onValueChange = onApproveWalletIdChange,
                        label = { Text("Mukofot tushadigan hamyon ID") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    TextButton(
                        onClick = { if (approveWalletId.isNotBlank()) onApprove(approveWalletId.trim()) }
                    ) { Text("Tasdiqlash va to'lash") }
                }
            }
        }
    }
}

private fun taskStatusLabel(status: String): String = when (status.lowercase()) {
    "pending" -> "Kutilmoqda"
    "done" -> "Bajarildi (tasdiq kutmoqda)"
    "approved" -> "Tasdiqlandi, to'landi ✅"
    else -> status
}
