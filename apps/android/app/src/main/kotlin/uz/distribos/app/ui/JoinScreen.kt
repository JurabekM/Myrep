package uz.distribos.app.ui

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import java.util.concurrent.Executors

/**
 * Qurilmani ulash ekrani.
 *
 * Ikkita yo'l: **QR skanerlash** (odatiy) va **qo'lda kiritish**
 * (kamera ishlamasa yoki ruxsat berilmasa). Qo'lda kiritish shunchaki
 * zaxira emas — omborda telefon kamerasi ko'pincha iflos yoki qorong'i
 * joyda ishlamaydi.
 *
 * QR kod ichida epoch kaliti YO'Q — faqat bir martalik taklif tegi
 * (`specs/distribos-event-seal/BOOT-1.md`).
 */

sealed interface JoinUiState {
    data object Idle : JoinUiState
    data object Scanning : JoinUiState
    data object Waiting : JoinUiState
    data class Joined(val role: String) : JoinUiState
    data class Failed(val reason: String) : JoinUiState
}

@Composable
fun JoinScreen(
    state: JoinUiState,
    onQrScanned: (ByteArray) -> Unit,
    onManualCode: (String) -> Unit,
    onStartScan: () -> Unit,
    onCancel: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("Qurilmani ulash", style = MaterialTheme.typography.headlineMedium)
        Text(
            "Kompyuterdagi DistribOS dasturida «Xavfsizlik» bo'limini oching " +
                "va «Yangi qurilma qo'shish» tugmasini bosing. Chiqqan QR kodni " +
                "shu yerda skanerlang.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        when (state) {
            is JoinUiState.Idle -> IdleContent(onStartScan, onManualCode)
            is JoinUiState.Scanning -> ScannerContent(onQrScanned, onCancel)
            is JoinUiState.Waiting -> WaitingContent(onCancel)
            is JoinUiState.Joined -> JoinedContent(state.role)
            is JoinUiState.Failed -> FailedContent(state.reason, onStartScan)
        }
    }
}

@Composable
private fun IdleContent(onStartScan: () -> Unit, onManualCode: (String) -> Unit) {
    val context = LocalContext.current
    var code by remember { mutableStateOf("") }
    var cameraDenied by remember { mutableStateOf(false) }

    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) onStartScan() else cameraDenied = true
    }

    Button(
        onClick = {
            val granted = ContextCompat.checkSelfPermission(
                context, Manifest.permission.CAMERA
            ) == PackageManager.PERMISSION_GRANTED
            if (granted) onStartScan() else permission.launch(Manifest.permission.CAMERA)
        },
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text("QR kodni skanerlash")
    }

    if (cameraDenied) {
        Text(
            "Kameraga ruxsat berilmadi. Quyida kodni qo'lda kiritishingiz mumkin.",
            style = MaterialTheme.typography.bodyMedium,
            color = StatusColors.warning,
        )
    }

    Text(
        "Yoki kodni qo'lda kiriting",
        style = MaterialTheme.typography.titleMedium,
    )
    OutlinedTextField(
        value = code,
        onValueChange = { code = it.trim() },
        label = { Text("Ulash kodi") },
        placeholder = { Text("a1b2c3…") },
        singleLine = false,
        minLines = 3,
        modifier = Modifier.fillMaxWidth(),
    )
    OutlinedButton(
        onClick = { onManualCode(code) },
        enabled = code.length >= 32,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text("Kod bilan ulash")
    }
}

@Composable
private fun ScannerContent(onQrScanned: (ByteArray) -> Unit, onCancel: () -> Unit) {
    QrScanner(
        onDetected = onQrScanned,
        modifier = Modifier.fillMaxWidth().aspectRatio(3f / 4f),
    )
    Text(
        "QR kodni ramka ichiga joylashtiring",
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    OutlinedButton(onClick = onCancel, modifier = Modifier.fillMaxWidth()) {
        Text("Bekor qilish")
    }
}

@Composable
private fun WaitingContent(onCancel: () -> Unit) {
    Card {
        Column(
            Modifier.fillMaxWidth().padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            CircularProgressIndicator()
            Text("Kompyuter javobi kutilmoqda…", style = MaterialTheme.typography.titleMedium)
            Text(
                "Bu bir necha soniya olishi mumkin. Internet ulanishini tekshiring.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
    OutlinedButton(onClick = onCancel, modifier = Modifier.fillMaxWidth()) {
        Text("Bekor qilish")
    }
}

@Composable
private fun JoinedContent(role: String) {
    Card(
        colors = CardDefaults.cardColors(
            containerColor = StatusColors.ok.copy(alpha = 0.14f)
        )
    ) {
        Column(
            Modifier.fillMaxWidth().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            StatusChip("Ulandi", StatusTone.OK)
            Text(
                "Qurilma qo'shildi. Rol: ${roleLabel(role)}",
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                "Endi kompyuterda egasi qurilmani TASDIQLASHI kerak. Tasdiqlanmaguncha " +
                    "yozuvlaringiz telefonda saqlanadi, lekin kompyuterga o'tmaydi.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun FailedContent(reason: String, onRetry: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(
            containerColor = StatusColors.error.copy(alpha = 0.14f)
        )
    ) {
        Column(
            Modifier.fillMaxWidth().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            StatusChip("Ulanmadi", StatusTone.ERROR)
            Text(reason, style = MaterialTheme.typography.bodyMedium)
        }
    }
    Button(onClick = onRetry, modifier = Modifier.fillMaxWidth()) {
        Text("Qaytadan urinish")
    }
}

/**
 * CameraX + ML Kit orqali QR o'qish.
 *
 * QR ichida BINAR CBOR bor, matn emas — shuning uchun `rawBytes` olinadi.
 * `displayValue` ni ishlatish baytlarni buzardi.
 */
@Composable
private fun QrScanner(onDetected: (ByteArray) -> Unit, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val executor = remember { Executors.newSingleThreadExecutor() }
    var handled by remember { mutableStateOf(false) }

    DisposableEffect(Unit) {
        onDispose { executor.shutdown() }
    }

    Box(modifier) {
        AndroidView(
            factory = { viewContext ->
                val previewView = PreviewView(viewContext)
                val providerFuture = ProcessCameraProvider.getInstance(viewContext)

                providerFuture.addListener({
                    val provider = providerFuture.get()
                    val preview = androidx.camera.core.Preview.Builder().build().also {
                        it.surfaceProvider = previewView.surfaceProvider
                    }

                    val scanner = BarcodeScanning.getClient()
                    val analysis = ImageAnalysis.Builder()
                        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                        .build()

                    analysis.setAnalyzer(executor) { proxy: ImageProxy ->
                        val media = proxy.image
                        if (media == null || handled) {
                            proxy.close()
                            return@setAnalyzer
                        }
                        val image = InputImage.fromMediaImage(
                            media, proxy.imageInfo.rotationDegrees
                        )
                        scanner.process(image)
                            .addOnSuccessListener { barcodes ->
                                val payload = barcodes
                                    .firstOrNull { it.format == Barcode.FORMAT_QR_CODE }
                                    ?.rawBytes
                                if (payload != null && !handled) {
                                    handled = true
                                    onDetected(payload)
                                }
                            }
                            .addOnCompleteListener { proxy.close() }
                    }

                    provider.unbindAll()
                    provider.bindToLifecycle(
                        lifecycleOwner, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis
                    )
                }, ContextCompat.getMainExecutor(viewContext))

                previewView
            },
            modifier = Modifier.fillMaxSize(),
        )
    }
}

private fun roleLabel(role: String): String = when (role) {
    "owner" -> "Egasi"
    "manager" -> "Rahbar"
    "agent" -> "Savdo agenti"
    "warehouse" -> "Omborchi"
    "cashier" -> "Kassir"
    "viewer" -> "Kuzatuvchi"
    else -> role
}
