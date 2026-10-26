package uz.sectorverify.feature.survey.debug

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import uz.sectorverify.feature.survey.R

@Composable
fun DebugScreen(vm: DebugViewModel = hiltViewModel()) {
    val s by vm.survey.collectAsStateWithLifecycle()
    val ui by vm.ui.collectAsStateWithLifecycle()
    val sites by vm.sites.collectAsStateWithLifecycle()
    val permissions = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(stringResource(R.string.debug_title), style = MaterialTheme.typography.headlineSmall)
        Text(stringResource(R.string.debug_rate, s.rateHz))
        Text(stringResource(R.string.debug_counts, s.samples, s.fixes))
        Text(stringResource(R.string.debug_visible, s.visibleCells.joinToString { it.toString() }))
        s.live?.let { Text(stringResource(R.string.debug_coverage, (it.overallCoverage * 100).toInt())) }
        ui.capabilities?.let {
            Text(
                stringResource(
                    R.string.debug_caps,
                    it.measuredRateHz,
                    it.neighborRsrpReported.toString(),
                    it.timingAdvanceReported.toString(),
                ),
            )
        }
        ui.messageRes?.let { Text(stringResource(it, ui.messageArg), color = MaterialTheme.colorScheme.error) }
        val big = Modifier.fillMaxWidth().heightIn(min = 56.dp)
        OutlinedButton(
            onClick = {
                permissions.launch(
                    arrayOf(
                        Manifest.permission.ACCESS_FINE_LOCATION,
                        Manifest.permission.READ_PHONE_STATE,
                        Manifest.permission.POST_NOTIFICATIONS,
                    ),
                )
            },
            modifier = big,
        ) { Text(stringResource(R.string.debug_permissions)) }
        OutlinedButton(onClick = vm::probe, enabled = !ui.probing, modifier = big) { Text(stringResource(R.string.debug_probe)) }
        for (site in sites) {
            Button(onClick = {
                vm.start(site)
            }, enabled = !s.running, modifier = big) { Text(stringResource(R.string.debug_start, site.code)) }
        }
        Button(onClick = vm::stop, enabled = s.running, modifier = big) { Text(stringResource(R.string.debug_stop)) }
        OutlinedButton(onClick = vm::exportZip, modifier = big) { Text(stringResource(R.string.debug_export)) }
        ui.lastZip?.let { Text(it.name, style = MaterialTheme.typography.bodySmall) }
    }
}
