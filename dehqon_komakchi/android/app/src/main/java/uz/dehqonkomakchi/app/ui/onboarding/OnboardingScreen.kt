package uz.dehqonkomakchi.app.ui.onboarding

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.dehqonkomakchi.app.R
import uz.dehqonkomakchi.app.core.util.Regions
import uz.dehqonkomakchi.app.work.IrrigationReminderWorker
import java.time.LocalDate

@Composable
fun OnboardingScreen(
    onComplete: () -> Unit,
    viewModel: OnboardingViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    LaunchedEffect(state.complete) {
        if (state.complete) {
            if (state.notificationsEnabled) IrrigationReminderWorker.schedule(context)
            onComplete()
        }
    }

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                when (state.step) {
                    0 -> WelcomeStep()
                    1 -> LanguageStep()
                    2 -> RegionStep(
                        selectedRegion = state.region,
                        selectedDistrict = state.district,
                        onSelected = viewModel::setRegion,
                    )
                    3 -> PlantingDateStep(
                        epochDay = state.plantingDateEpochDay,
                        onChange = viewModel::setPlantingDate,
                    )
                    4 -> NotificationsStep(
                        enabled = state.notificationsEnabled,
                        onChange = viewModel::setNotificationsEnabled,
                    )
                }
            }

            Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = viewModel::next,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = state.step != 2 || state.region.isNotBlank(),
                ) {
                    Text(
                        if (state.step == viewModel.totalSteps - 1) stringResource(R.string.onboarding_finish)
                        else stringResource(R.string.action_continue),
                    )
                }
                if (state.step > 0) {
                    OutlinedButton(onClick = viewModel::back, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(R.string.action_back))
                    }
                }
            }
        }
    }
}

@Composable
private fun WelcomeStep() {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text(stringResource(R.string.onboarding_welcome_title), style = MaterialTheme.typography.headlineMedium)
        Text(stringResource(R.string.onboarding_welcome_subtitle), style = MaterialTheme.typography.bodyLarge)
    }
}

@Composable
private fun LanguageStep() {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text(stringResource(R.string.onboarding_language_title), style = MaterialTheme.typography.titleLarge)
        Card(modifier = Modifier.fillMaxWidth()) {
            Text(
                stringResource(R.string.onboarding_language_uz),
                modifier = Modifier.padding(16.dp),
                style = MaterialTheme.typography.bodyLarge,
            )
        }
    }
}

@Composable
private fun RegionStep(
    selectedRegion: String,
    selectedDistrict: String,
    onSelected: (String, String) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(stringResource(R.string.onboarding_region_title), style = MaterialTheme.typography.titleLarge)
        LazyColumn(modifier = Modifier.fillMaxWidth()) {
            items(Regions.ALL) { region ->
                FilterChip(
                    selected = selectedRegion == region,
                    onClick = { onSelected(region, Regions.districtsFor(region).firstOrNull().orEmpty()) },
                    label = { Text(region) },
                    modifier = Modifier.padding(vertical = 4.dp),
                )
            }
        }
        if (selectedRegion.isNotBlank()) {
            Text(stringResource(R.string.onboarding_district_title), style = MaterialTheme.typography.titleMedium)
            LazyColumn {
                items(Regions.districtsFor(selectedRegion)) { district ->
                    FilterChip(
                        selected = selectedDistrict == district,
                        onClick = { onSelected(selectedRegion, district) },
                        label = { Text(district) },
                        modifier = Modifier.padding(vertical = 4.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun PlantingDateStep(epochDay: Long, onChange: (Long) -> Unit) {
    val date = LocalDate.ofEpochDay(epochDay)
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text(stringResource(R.string.onboarding_planting_date_title), style = MaterialTheme.typography.titleLarge)
        Text(stringResource(R.string.onboarding_planting_date_hint), style = MaterialTheme.typography.bodyMedium)
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(-14, -7, 0).forEach { offset ->
                val candidate = LocalDate.now().plusDays(offset.toLong())
                OutlinedButton(
                    onClick = { onChange(candidate.toEpochDay()) },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(candidate.toString() + if (candidate == date) " ✓" else "")
                }
            }
        }
    }
}

@Composable
private fun NotificationsStep(enabled: Boolean, onChange: (Boolean) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text(stringResource(R.string.onboarding_notif_title), style = MaterialTheme.typography.titleLarge)
        Text(stringResource(R.string.onboarding_notif_subtitle), style = MaterialTheme.typography.bodyLarge)
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.Start,
        ) {
            Switch(checked = enabled, onCheckedChange = onChange)
        }
    }
}
