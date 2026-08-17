package com.smartmoliya.app.feature.dashboard.presentation

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDownward
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.smartmoliya.app.feature.expense.domain.TransactionType
import com.smartmoliya.app.ui.components.EmptyState
import com.smartmoliya.app.ui.components.GradientCard
import com.smartmoliya.app.ui.components.SectionHeader
import com.smartmoliya.app.ui.components.TransactionRow
import com.smartmoliya.app.ui.components.formatAmount
import com.smartmoliya.app.ui.components.formatShortDate

@Composable
fun DashboardScreen(viewModel: DashboardViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            GradientCard {
                Text(
                    text = "Umumiy balans",
                    style = MaterialTheme.typography.labelLarge,
                    color = Color.White.copy(alpha = 0.85f)
                )
                Text(
                    text = formatAmount(state.totalBalance),
                    style = MaterialTheme.typography.displayMedium,
                    color = Color.White
                )
                Text(
                    text = state.currency,
                    style = MaterialTheme.typography.labelLarge,
                    color = Color.White.copy(alpha = 0.85f)
                )

                Spacer(modifier = Modifier.height(16.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    MonthStatPill(
                        icon = Icons.Default.ArrowDownward,
                        label = "Daromad",
                        value = formatAmount(state.monthIncome),
                        modifier = Modifier.weight(1f)
                    )
                    MonthStatPill(
                        icon = Icons.Default.ArrowUpward,
                        label = "Xarajat",
                        value = formatAmount(state.monthExpense),
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }

        item { SectionHeader(title = "So'nggi tranzaksiyalar") }

        if (state.recentTransactions.isEmpty()) {
            item {
                EmptyState(
                    emoji = "🌱",
                    text = "Hozircha tranzaksiya yo'q.\n\"Tranzaksiyalar\" bo'limida + tugmasini bosing"
                )
            }
        } else {
            items(state.recentTransactions, key = { it.id }) { transaction ->
                val category = transaction.categoryId?.let { state.categories[it] }
                TransactionRow(
                    title = transaction.note ?: category?.name
                        ?: if (transaction.type == TransactionType.INCOME) "Daromad" else "Xarajat",
                    subtitle = listOfNotNull(category?.name, formatShortDate(transaction.occurredAt))
                        .joinToString(" • "),
                    amount = transaction.amount,
                    currency = transaction.currency,
                    isIncome = transaction.type == TransactionType.INCOME,
                    icon = category?.icon
                )
            }
        }
    }
}

@Composable
private fun MonthStatPill(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    value: String,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .background(Color.White.copy(alpha = 0.16f), RoundedCornerShape(16.dp))
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = Color.White,
            modifier = Modifier
                .size(28.dp)
                .background(Color.White.copy(alpha = 0.2f), CircleShape)
                .padding(5.dp)
        )
        Column(modifier = Modifier.padding(start = 8.dp)) {
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                color = Color.White.copy(alpha = 0.85f)
            )
            Text(
                text = value,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                color = Color.White,
                maxLines = 1
            )
        }
    }
}
