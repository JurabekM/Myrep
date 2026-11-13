package uz.omborai.omborai_mobile.scanner

import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.StandardMessageCodec

/**
 * Shtrix-kod skaneri: Flutter'da "uz.omborai/scanner" platform view sifatida ochiladi.
 * Topilgan kodlar EventChannel ("uz.omborai/scanner/events/<viewId>") orqali Dart tomoniga yuboriladi.
 */
class BarcodeScannerPlugin : FlutterPlugin {
    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        binding.platformViewRegistry.registerViewFactory(
            VIEW_TYPE,
            BarcodeScannerViewFactory(binding.binaryMessenger, StandardMessageCodec.INSTANCE),
        )
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        // Ro'yxatdan chiqarish shart emas: platform view'lar o'zi dispose qilinadi
    }

    companion object {
        const val VIEW_TYPE = "uz.omborai/scanner"
    }
}
