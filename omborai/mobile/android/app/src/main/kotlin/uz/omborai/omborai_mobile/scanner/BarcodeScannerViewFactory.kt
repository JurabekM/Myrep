package uz.omborai.omborai_mobile.scanner

import android.content.Context
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MessageCodec
import io.flutter.plugin.platform.PlatformView
import io.flutter.plugin.platform.PlatformViewFactory

class BarcodeScannerViewFactory(
    private val messenger: BinaryMessenger,
    codec: MessageCodec<Any?>,
) : PlatformViewFactory(codec) {
    override fun create(context: Context, viewId: Int, args: Any?): PlatformView =
        BarcodeScannerView(context, messenger, viewId)
}
