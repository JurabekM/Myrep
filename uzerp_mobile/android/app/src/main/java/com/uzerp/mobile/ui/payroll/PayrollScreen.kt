package com.uzerp.mobile.ui.payroll

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.RequestQuote
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.uzerp.mobile.core.money
import com.uzerp.mobile.ui.common.EmptyState
import com.uzerp.mobile.ui.common.ErrorBanner
import com.uzerp.mobile.ui.common.ListRowCard
import com.uzerp.mobile.ui.common.LoadingState
import com.uzerp.mobile.ui.common.ScreenScaffold
import com.uzerp.mobile.ui.common.StatusChip
import com.uzerp.mobile.ui.theme.UzAmber
import com.uzerp.mobile.ui.theme.UzGreen

@Composable
fun PayrollListScreen(onBack: () -> Unit, onOpen: (Long) -> Unit, onCreate: () -> Unit, viewModel: PayrollListViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.reload() }

    ScreenScaffold(title = "Ish haqi", onBack = onBack, fabIcon = Icons.Filled.Add, onFabClick = onCreate) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            state.error?.let { ErrorBanner(it) }
            when {
                state.isLoading -> LoadingState()
                state.runs.isEmpty() -> EmptyState("Vedomostlar yo'q.")
                else -> LazyColumn {
                    items(state.runs, key = { it.id }) { run ->
                        ListRowCard(
                            title = run.period,
                            subtitle = "Yalpi: ${money(run.totalGross)} · Sof: ${money(run.totalNet)}",
                            badge = { StatusChip(run.status) },
                            onClick = { onOpen(run.id) },
                            leadingIcon = Icons.Filled.RequestQuote,
                            iconTint = UzAmber,
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun PayrollCreateScreen(onBack: () -> Unit, onCreated: (Long) -> Unit, viewModel: PayrollCreateViewModel = hiltViewModel()) {
    val period by viewModel.period.collectAsState()
    val error by viewModel.error.collectAsState()
    val createdId by viewModel.createdRunId.collectAsState()
    LaunchedEffect(createdId) { createdId?.let(onCreated) }

    ScreenScaffold(title = "Yangi vedomost", onBack = onBack) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            error?.let { ErrorBanner(it) }
            OutlinedTextField(
                value = period, onValueChange = viewModel::setPeriod, label = { Text("Davr (YYYY-MM)") },
                singleLine = true, modifier = Modifier.fillMaxWidth(),
            )
            Button(onClick = viewModel::create, modifier = Modifier.fillMaxWidth().padding(top = 16.dp)) {
                Text("Hisoblash")
            }
        }
    }
}

@Composable
fun PayrollDetailScreen(runId: Long, onBack: () -> Unit, viewModel: PayrollDetailViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(runId) { viewModel.load(runId) }

    val detail = state.detail
    ScreenScaffold(title = detail?.run?.period ?: "Vedomost", onBack = onBack) { padding ->
        if (state.isLoading || detail == null) {
            LoadingState()
            return@ScreenScaffold
        }
        val run = detail.run
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            state.error?.let { ErrorBanner(it) }
            Row(modifier = Modifier.fillMaxWidth()) {
                Text("Holat", modifier = Modifier.weight(1f))
                StatusChip(run.status)
            }
            Text("Yalpi (gross): ${money(run.totalGross)}", modifier = Modifier.padding(top = 8.dp))
            Text("Soliq + INPS: ${money(run.totalTax)}")
            Text("Sof (net): ${money(run.totalNet)}", fontWeight = FontWeight.Bold, color = UzGreen)

            LazyColumn(modifier = Modifier.weight(1f).padding(top = 12.dp)) {
                items(detail.items, key = { it.id }) { item ->
                    ListRowCard(title = item.fullName, subtitle = "${item.code} · ${item.position}", trailing = money(item.net))
                }
            }

            Row(modifier = Modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (run.status == "draft") {
                    Button(onClick = viewModel::approve, colors = ButtonDefaults.buttonColors(containerColor = UzGreen)) { Text("Tasdiqlash") }
                }
                if (run.status == "approved") {
                    Button(onClick = { viewModel.pay("bank") }) { Text("To'lash (bank)") }
                    Button(onClick = { viewModel.pay("cash") }) { Text("To'lash (kassa)") }
                }
            }
        }
    }
}
