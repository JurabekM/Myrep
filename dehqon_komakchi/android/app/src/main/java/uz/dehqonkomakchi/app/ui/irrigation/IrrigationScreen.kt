package uz.dehqonkomakchi.app.ui.irrigation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.dehqonkomakchi.app.R
import uz.dehqonkomakchi.app.data.repo.IrrigationUrgency
import java.time.LocalDate

@Composable
fun IrrigationScreen(viewModel: IrrigationViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            Text(stringResource(R.string.irrigation_title), style = MaterialTheme.typography.headlineMedium)
            Column(modifier = Modifier.padding(top = 12.dp)) {
                when (val state = uiState) {
                    is IrrigationUiState.Loading -> CircularProgressIndicator()
                    is IrrigationUiState.NoRegion -> Text(stringResource(R.string.onboarding_region_title))
                    is IrrigationUiState.Error -> Column {
                        Text(stringResource(R.string.status_error_generic))
                        Button(onClick = viewModel::load) { Text(stringResource(R.string.action_retry)) }
                    }
                    is IrrigationUiState.Loaded -> LoadedContent(state, onLogWatering = viewModel::logWatering)
                }
            }
        }
    }
}

@Composable
private fun LoadedContent(state: IrrigationUiState.Loaded, onLogWatering: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        if (state.weather.isFromCache) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.irrigation_offline_notice), modifier = Modifier.padding(12.dp))
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(stringResource(R.string.irrigation_current_weather), style = MaterialTheme.typography.titleMedium)
                Text("${state.weather.currentTempC}°C — ${state.weather.currentConditionUzbek}", style = MaterialTheme.typography.headlineMedium)
            }
        }

        Text(stringResource(R.string.irrigation_forecast), style = MaterialTheme.typography.titleMedium)
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(state.weather.forecast) { day ->
                Card {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(LocalDate.ofEpochDay(day.epochDay).dayOfMonth.toString(), style = MaterialTheme.typography.titleMedium)
                        Text("${day.tempMinC.toInt()}°–${day.tempMaxC.toInt()}°")
                        Text("${stringResource(R.string.irrigation_rain_label)}: ${day.rainProbabilityPercent}%", style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }

        val (icon, tint) = when (state.suggestion.urgency) {
            IrrigationUrgency.HOLD_OFF -> Icons.Filled.CheckCircle to MaterialTheme.colorScheme.primary
            IrrigationUrgency.WATER_SOON -> Icons.Filled.Warning to MaterialTheme.colorScheme.error
            IrrigationUrgency.NORMAL -> Icons.Filled.WaterDrop to MaterialTheme.colorScheme.tertiary
        }
        Card(modifier = Modifier.fillMaxWidth()) {
            Row(modifier = Modifier.padding(16.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Icon(icon, contentDescription = null, tint = tint)
                Column(modifier = Modifier.padding(start = 12.dp)) {
                    Text(stringResource(R.string.irrigation_suggestion_title), style = MaterialTheme.typography.titleMedium)
                    Text(state.suggestion.messageUzbek, style = MaterialTheme.typography.bodyLarge)
                }
            }
        }

        Text(
            stringResource(R.string.irrigation_last_watered) + ": " +
                (state.lastWateredEpochDay?.let { LocalDate.ofEpochDay(it).toString() }
                    ?: stringResource(R.string.irrigation_last_watered_never)),
            style = MaterialTheme.typography.bodyMedium,
        )

        Button(onClick = onLogWatering, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.Filled.WaterDrop, contentDescription = null)
            Text("  " + stringResource(R.string.irrigation_log_watering))
        }
    }
}
