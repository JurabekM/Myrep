package uz.dehqonkomakchi.app.ui.diagnose

import android.content.Context
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material.icons.filled.ThumbDown
import androidx.compose.material.icons.filled.ThumbUp
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.hilt.navigation.compose.hiltViewModel
import uz.dehqonkomakchi.app.R
import uz.dehqonkomakchi.app.data.remote.diagnosis.DiagnosisCategory
import java.io.File

private fun categoryLabel(category: DiagnosisCategory): Int = when (category) {
    DiagnosisCategory.PEST -> R.string.category_pest
    DiagnosisCategory.FUNGAL -> R.string.category_fungal
    DiagnosisCategory.NUTRIENT -> R.string.category_nutrient
    DiagnosisCategory.WATERING -> R.string.category_watering
    DiagnosisCategory.HEAT_STRESS -> R.string.category_heat
    DiagnosisCategory.UNCLEAR -> R.string.category_unclear
}

private fun createImageFile(context: Context): File {
    val dir = File(context.cacheDir, "camera").apply { mkdirs() }
    return File(dir, "diag_${System.currentTimeMillis()}.jpg")
}

@Composable
fun DiagnoseScreen(viewModel: DiagnoseViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    val history by viewModel.history.collectAsState()
    val context = androidx.compose.ui.platform.LocalContext.current

    var pendingPhotoFile by remember { mutableStateOf<File?>(null) }

    val galleryLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri ?: return@rememberLauncherForActivityResult
        val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: return@rememberLauncherForActivityResult
        viewModel.analyze(bytes, uri.toString())
    }

    val cameraLauncher = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        val file = pendingPhotoFile ?: return@rememberLauncherForActivityResult
        if (success) {
            val bytes = file.readBytes()
            viewModel.analyze(bytes, file.absolutePath)
        }
    }

    Scaffold { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            when (val state = uiState) {
                is DiagnoseUiState.Idle -> IdleContent(
                    onTakePhoto = {
                        val file = createImageFile(context)
                        pendingPhotoFile = file
                        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
                        cameraLauncher.launch(uri)
                    },
                    onPickGallery = { galleryLauncher.launch("image/*") },
                    history = history,
                )
                is DiagnoseUiState.Analyzing -> AnalyzingContent()
                is DiagnoseUiState.RetakeNeeded -> RetakeContent(onRetry = viewModel::reset)
                is DiagnoseUiState.Done -> ResultContent(
                    record = state.record,
                    onRate = { useful -> viewModel.rate(state.record.id, useful) },
                    onNewCheck = viewModel::reset,
                )
                is DiagnoseUiState.Failed -> Column {
                    Text(stringResource(R.string.status_error_generic))
                    Button(onClick = viewModel::reset) { Text(stringResource(R.string.action_retry)) }
                }
            }
        }
    }
}

@Composable
private fun IdleContent(
    onTakePhoto: () -> Unit,
    onPickGallery: () -> Unit,
    history: List<uz.dehqonkomakchi.app.data.repo.DiagnosisRecord>,
) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text(stringResource(R.string.diagnose_title), style = MaterialTheme.typography.headlineMedium)
        Text(stringResource(R.string.diagnose_intro), style = MaterialTheme.typography.bodyLarge)

        Button(
            onClick = onTakePhoto,
            modifier = Modifier.fillMaxWidth().semantics { contentDescription = "" },
        ) {
            Icon(Icons.Filled.CameraAlt, contentDescription = null)
            Text("  " + stringResource(R.string.diagnose_take_photo))
        }
        OutlinedButton(onClick = onPickGallery, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.Filled.PhotoLibrary, contentDescription = null)
            Text("  " + stringResource(R.string.diagnose_pick_gallery))
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Text(
                stringResource(R.string.diagnose_disclaimer),
                modifier = Modifier.padding(12.dp),
                style = MaterialTheme.typography.bodyMedium,
            )
        }

        Text(stringResource(R.string.diagnose_history_title), style = MaterialTheme.typography.titleMedium)
        if (history.isEmpty()) {
            Text(stringResource(R.string.diagnose_history_empty), style = MaterialTheme.typography.bodyMedium)
        } else {
            LazyColumn(modifier = Modifier.fillMaxWidth()) {
                items(history) { record ->
                    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(stringResource(categoryLabel(record.category)), style = MaterialTheme.typography.titleMedium)
                            Text(record.cause, style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun AnalyzingContent() {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally,
    ) {
        CircularProgressIndicator()
        Column(modifier = Modifier.padding(top = 16.dp)) {
            Text(stringResource(R.string.diagnose_analyzing), style = MaterialTheme.typography.bodyLarge)
        }
    }
}

@Composable
private fun RetakeContent(onRetry: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text(stringResource(R.string.diagnose_retake_title), style = MaterialTheme.typography.titleLarge)
        Text(stringResource(R.string.diagnose_retake_hint), style = MaterialTheme.typography.bodyLarge)
        Button(onClick = onRetry, modifier = Modifier.fillMaxWidth()) {
            Text(stringResource(R.string.action_retry))
        }
    }
}

@Composable
private fun ResultContent(
    record: uz.dehqonkomakchi.app.data.repo.DiagnosisRecord,
    onRate: (Boolean) -> Unit,
    onNewCheck: () -> Unit,
) {
    var rated by remember { mutableStateOf(record.usefulRating != null) }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text(stringResource(R.string.diagnose_result_title), style = MaterialTheme.typography.headlineMedium)
            val confidenceLabel = when {
                record.confidence < 0.45f -> R.string.diagnose_confidence_low
                record.confidence < 0.7f -> R.string.diagnose_confidence_medium
                else -> R.string.diagnose_confidence_high
            }
            Text(stringResource(categoryLabel(record.category)), style = MaterialTheme.typography.titleLarge)
            Text(stringResource(confidenceLabel), style = MaterialTheme.typography.bodyMedium)
            LinearProgressIndicator(progress = { record.confidence }, modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp))
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(stringResource(R.string.diagnose_cause_label), style = MaterialTheme.typography.titleMedium)
                    Text(record.cause, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(stringResource(R.string.diagnose_steps_label), style = MaterialTheme.typography.titleMedium)
                    record.steps.forEach { Text("• $it", style = MaterialTheme.typography.bodyMedium) }
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(stringResource(R.string.diagnose_watch_label), style = MaterialTheme.typography.titleMedium)
                    record.watch.forEach { Text("• $it", style = MaterialTheme.typography.bodyMedium) }
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(stringResource(R.string.diagnose_consult_label), style = MaterialTheme.typography.titleMedium)
                    Text(record.consult, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Text(
                    stringResource(R.string.diagnose_disclaimer),
                    modifier = Modifier.padding(12.dp),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
        item {
            if (rated) {
                Text(stringResource(R.string.diagnose_rate_thanks), style = MaterialTheme.typography.bodyMedium)
            } else {
                Text(stringResource(R.string.diagnose_rate_question), style = MaterialTheme.typography.titleMedium)
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(onClick = { onRate(true); rated = true }) {
                        Icon(Icons.Filled.ThumbUp, contentDescription = null)
                        Text("  " + stringResource(R.string.diagnose_rate_useful))
                    }
                    OutlinedButton(onClick = { onRate(false); rated = true }) {
                        Icon(Icons.Filled.ThumbDown, contentDescription = null)
                        Text("  " + stringResource(R.string.diagnose_rate_not_useful))
                    }
                }
            }
        }
        item {
            Button(onClick = onNewCheck, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.diagnose_take_photo))
            }
        }
    }
}
