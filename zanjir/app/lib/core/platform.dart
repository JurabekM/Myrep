import 'package:flutter/services.dart';
import 'package:printing/printing.dart';

/// Ekranshot va ekran yozuvidan himoya (Android `FLAG_SECURE`) — faqat imzolash ekranida (prompt, MASVS).
abstract interface class SecureScreen {
  Future<void> enable();
  Future<void> disable();
}

class MethodChannelSecureScreen implements SecureScreen {
  const MethodChannelSecureScreen();
  static const _channel = MethodChannel('zanjir/secure_screen');

  @override
  Future<void> enable() => _call('enable');

  @override
  Future<void> disable() => _call('disable');

  Future<void> _call(String method) async {
    try {
      await _channel.invokeMethod<void>(method);
    } on MissingPluginException {
      // Android bo'lmagan platformalar (desktop, test) — himoya yo'q.
    }
  }
}

/// Imzolangan PDF ni ulashish va chop etish (`printing`). Testlarda soxtasi bilan almashtiriladi.
abstract interface class PdfActions {
  Future<void> share(Uint8List pdf, String filename);
  Future<void> print(Uint8List pdf, String name);
}

class PrintingPdfActions implements PdfActions {
  const PrintingPdfActions();

  @override
  Future<void> share(Uint8List pdf, String filename) => Printing.sharePdf(bytes: pdf, filename: filename);

  @override
  Future<void> print(Uint8List pdf, String name) => Printing.layoutPdf(onLayout: (_) async => pdf, name: name);
}
