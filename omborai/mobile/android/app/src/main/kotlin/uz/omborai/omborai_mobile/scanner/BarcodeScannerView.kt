package uz.omborai.omborai_mobile.scanner

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.View
import androidx.camera.core.CameraSelector
import androidx.camera.core.ExperimentalGetImage
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.LifecycleRegistry
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.platform.PlatformView
import java.util.concurrent.Executors

/**
 * CameraX orqali orqa kamera tasviri; ML Kit har bir kadrda shtrix-kodni qidiradi.
 * Bir xil kod 2 soniya ichida qayta yuborilmaydi (kassada ikki marta qo'shilmasligi uchun).
 */
class BarcodeScannerView(
    private val context: Context,
    messenger: BinaryMessenger,
    viewId: Int,
) : PlatformView, LifecycleOwner {

    private val previewView = PreviewView(context).apply {
        scaleType = PreviewView.ScaleType.FILL_CENTER
        implementationMode = PreviewView.ImplementationMode.COMPATIBLE
    }
    private val lifecycleRegistry = LifecycleRegistry(this)
    private val analysisExecutor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())
    private val scanner = BarcodeScanning.getClient(
        BarcodeScannerOptions.Builder()
            .setBarcodeFormats(
                Barcode.FORMAT_EAN_13,
                Barcode.FORMAT_EAN_8,
                Barcode.FORMAT_UPC_A,
                Barcode.FORMAT_UPC_E,
                Barcode.FORMAT_CODE_128,
                Barcode.FORMAT_CODE_39,
                Barcode.FORMAT_QR_CODE,
            )
            .build(),
    )
    private val events = EventChannel(messenger, "uz.omborai/scanner/events/$viewId")
    private var sink: EventChannel.EventSink? = null
    private var lastCode: String? = null
    private var lastEmittedAt = 0L
    private var cameraProvider: ProcessCameraProvider? = null
    private var disposed = false

    init {
        events.setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, eventSink: EventChannel.EventSink?) {
                sink = eventSink
            }

            override fun onCancel(arguments: Any?) {
                sink = null
            }
        })
        lifecycleRegistry.currentState = Lifecycle.State.CREATED
        lifecycleRegistry.currentState = Lifecycle.State.RESUMED
        startCamera()
    }

    override fun getView(): View = previewView

    override val lifecycle: Lifecycle
        get() = lifecycleRegistry

    override fun dispose() {
        disposed = true
        cameraProvider?.unbindAll()
        lifecycleRegistry.currentState = Lifecycle.State.DESTROYED
        analysisExecutor.shutdown()
        scanner.close()
        events.setStreamHandler(null)
        sink = null
    }

    private fun startCamera() {
        val providerFuture = ProcessCameraProvider.getInstance(context)
        providerFuture.addListener({
            if (disposed) return@addListener
            val provider = providerFuture.get()
            cameraProvider = provider

            val preview = Preview.Builder().build().also {
                it.surfaceProvider = previewView.surfaceProvider
            }
            val analysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also { it.setAnalyzer(analysisExecutor) { frame -> analyze(frame) } }

            provider.unbindAll()
            provider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
        }, ContextCompat.getMainExecutor(context))
    }

    @ExperimentalGetImage
    private fun analyze(frame: ImageProxy) {
        val media = frame.image
        if (media == null) {
            frame.close()
            return
        }
        val input = InputImage.fromMediaImage(media, frame.imageInfo.rotationDegrees)
        scanner.process(input)
            .addOnSuccessListener { codes ->
                codes.firstNotNullOfOrNull { it.rawValue }?.let { emit(it) }
            }
            .addOnCompleteListener { frame.close() }
    }

    private fun emit(code: String) {
        val now = SystemClock.elapsedRealtime()
        if (code == lastCode && now - lastEmittedAt < DUPLICATE_WINDOW_MS) return
        lastCode = code
        lastEmittedAt = now
        mainHandler.post { sink?.success(code) }
    }

    private companion object {
        const val DUPLICATE_WINDOW_MS = 2_000L
    }
}
